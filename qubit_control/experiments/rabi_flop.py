from artiq.experiment import EnvExperiment, kernel, NumberValue
from artiq.language.types import TFloat, TInt32
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.detection import DetectionModule
from system.services.cooling import CoolingService
from config import RESONANCE_HZ, OMEGA_RABI, N_BRIGHT, N_DARK
from scipy.optimize import curve_fit
import numpy as np
import matplotlib.pyplot as plt

class RabiFlop(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_argument("measure_duration", NumberValue(default=1e-3, unit='s'))
        self.setattr_argument("pulse_min_duration", NumberValue(default=0e-6, unit='s'))
        self.setattr_argument("pulse_max_duration", NumberValue(default=50e-6, unit='s'))
        self.setattr_argument("n_shots", NumberValue(default=100))
        self.setattr_argument("pulse_n_durations", NumberValue(default=100))
        self.setattr_argument("laser_frequency", NumberValue(default=RESONANCE_HZ))
        self.setattr_argument("laser_phase", NumberValue(default=0))

        self.detection = DetectionModule()
        self.detection.build(self)
        self.laser_729 = Laser729Module()
        self.laser_729.build(self)
        self.laser_397_cool = Laser397CoolModule()
        self.laser_397_cool.build(self)
        self.laser_397_pump = Laser397PumpModule()
        self.laser_397_pump.build(self)

        self.cooling = CoolingService()
        self.cooling.build(self.laser_729, self.laser_397_cool, self.laser_397_pump)

    def prepare(self):
        self.measure_duration = float(self.measure_duration)
        self.pulse_min_duration = float(self.pulse_min_duration)
        self.pulse_max_duration = float(self.pulse_max_duration)
        self.n_shots = int(self.n_shots)
        self.pulse_n_durations = int(self.pulse_n_durations)
        self.laser_frequency = float(self.laser_frequency)
        self.laser_phase = float(self.laser_phase)

        self.pulse_durations = np.linspace(
            self.pulse_min_duration, self.pulse_max_duration, self.pulse_n_durations
        )
        self.set_dataset("pulse_durations", self.pulse_durations, broadcast=True)
        self.set_dataset("p_excited", np.zeros(self.pulse_n_durations), broadcast=True)
        self.set_dataset("counts", np.zeros((self.pulse_n_durations, self.n_shots)), broadcast=True)

        self._counts = np.zeros((self.pulse_n_durations, self.n_shots))

    def init_device(self):
        self.laser_729.set_frequency(self.laser_frequency)
        self.laser_729.set_phase(self.laser_phase)

    def run(self):
        self.init_device()
        self.cooling.doppler_cool()

        for i in range(self.pulse_n_durations):
            for shot in range(self.n_shots):
                self.cooling.optical_pump()
                self._counts[i, shot] = self.pulse_and_count(self.pulse_durations[i])

        self.set_dataset("counts", self._counts, broadcast=True)

    @kernel
    def pulse_and_count(self, duration: TFloat) -> TInt32:
        self.laser_729.pulse(duration)
        return self.detection.count(ion_index=1, duration=self.measure_duration)

    def analyze(self):
        t = self.pulse_durations
        counts_2d = self.get_dataset("counts")

        threshold = (N_BRIGHT + N_DARK) / 2 * self.measure_duration * 1e3
        excited = counts_2d < threshold
        p_excited = excited.mean(axis=1)
        p_err = np.sqrt(p_excited * (1 - p_excited) / self.n_shots)
        self.set_dataset("p_excited", p_excited, broadcast=True)

        def rabi_model(t, omega, phi, A, offset):
            return A * (1 - np.cos(omega * t + phi)) / 2 + offset

        p0 = [OMEGA_RABI, 0.0, 1.0, 0.0]
        bounds = ([0, -np.pi, 0, -0.1],
                  [2 * np.pi * 200e3, np.pi, 1.2, 0.5])
        popt, pcov = curve_fit(
            rabi_model, t, p_excited,
            sigma=np.clip(p_err, 1e-3, None),
            p0=p0, bounds=bounds, maxfev=10000,
        )

        omega_fit, phi_fit, A_fit, offset_fit = popt
        omega_err, phi_err, A_err, offset_err = np.sqrt(np.diag(pcov))
        t_pi = (np.pi - phi_fit) / omega_fit
        f_rabi = omega_fit / (2 * np.pi)
        f_rabi_err = omega_err / (2 * np.pi)
        t_fine = np.linspace(t.min(), t.max(), 2000)

        self.set_dataset("calibration.t_pi", t_pi, persist=True)
        self.set_dataset("calibration.omega_rabi", omega_fit, persist=True)

        print(f"  Ω/2π    = {f_rabi/1e3:7.2f} ± {f_rabi_err/1e3:.2f} kHz")
        print(f"  t_π     = {t_pi*1e6:7.2f} µs")

        plt.rcParams.update({
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelsize": 12,
            "xtick.direction": "in",
            "ytick.direction": "in",
        })

        DATA_COLOR   = "#2b6cb0"
        FIT_COLOR    = "#c53030"
        ACCENT_COLOR = "#2f855a"

        fig, ax = plt.subplots(figsize=(8.5, 4.8))

        ax.axvline(t_pi * 1e6, color=ACCENT_COLOR, lw=0.8, ls="--", alpha=0.6)
        ax.text(t_pi * 1e6, 1.02, r"$t_\pi$", color=ACCENT_COLOR,
                ha="center", va="bottom", fontsize=9,
                transform=ax.get_xaxis_transform())

        ax.errorbar(
            t * 1e6, p_excited, yerr=p_err,
            fmt="o", ms=3.2, mfc=DATA_COLOR, mec="none",
            ecolor=DATA_COLOR, elinewidth=0.5, alpha=0.65, capsize=0,
            label=f"data ({self.n_shots} shots/point)",
        )
        ax.plot(
            t_fine * 1e6, rabi_model(t_fine, *popt),
            color=FIT_COLOR, lw=1.7, label="fit",
        )

        ax.set_xlabel(r"Pulse duration  $t$  ($\mu$s)")
        ax.set_ylabel(r"$P(|1\rangle)$")
        ax.set_xlim(t.min() * 1e6, t.max() * 1e6)
        ax.set_ylim(-0.03, 1.10)
        ax.grid(True, alpha=0.25, linestyle=":")

        info = (
            f"$\\Omega/2\\pi = {f_rabi/1e3:.2f} \\pm {f_rabi_err/1e3:.2f}$ kHz\n"
            f"$t_\\pi = {t_pi*1e6:.2f}$ µs"
        )
        ax.text(
            0.985, 0.96, info, transform=ax.transAxes,
            ha="right", va="top", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor="white", edgecolor="#bbb", alpha=0.92),
        )
        ax.legend(loc="lower right", framealpha=0.9, fontsize=9)
        ax.set_title("Rabi flop", loc="left", fontsize=13, pad=10)

        fig.tight_layout()
        fig.savefig("rabi_flop.pdf", bbox_inches="tight")
        plt.close(fig)
