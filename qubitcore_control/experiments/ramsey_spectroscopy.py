from artiq.experiment import EnvExperiment, kernel, delay, NumberValue
from artiq.language.types import TFloat, TInt32, TNone
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.detection import DetectionModule
from system.services.cooling import CoolingService
from config import RESONANCE_HZ, OMEGA_RABI, N_BRIGHT, N_DARK, T2_STAR
from scipy.optimize import curve_fit
import numpy as np
import matplotlib.pyplot as plt

class RamseySpectroscopy(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_argument("T_min", NumberValue(default=0.0, unit='s'))
        self.setattr_argument("T_max", NumberValue(default=5e-3, unit='s'))
        self.setattr_argument("n_points", NumberValue(default=500))
        self.setattr_argument("n_shots", NumberValue(default=100))
        self.setattr_argument("detuning_hz", NumberValue(default=1e3))
        self.setattr_argument("measure_duration", NumberValue(default=1e-3))

        self.detection = DetectionModule()
        self.detection.build(self)
        self.laser_729 = Laser729Module()
        self.laser_729.build(self)
        self.laser_397_cool = Laser397CoolModule()
        self.laser_397_cool.build(self)
        self.laser_397_pump = Laser397PumpModule()
        self.laser_397_pump.build(self)

        self.cooling = CoolingService()
        self.cooling.build(self.laser_729, self.laser_397_cool, self.laser_397_pump, self.detection)

    def prepare(self):
        self.T_min = float(self.T_min)
        self.T_max = float(self.T_max)
        self.n_points = int(self.n_points)
        self.n_shots = int(self.n_shots)
        self.detuning_hz = float(self.detuning_hz)
        self.measure_duration = float(self.measure_duration)

        self.wait_times = np.linspace(self.T_min, self.T_max, self.n_points)
        self.set_dataset("wait_times", self.wait_times, broadcast=True)
        self.set_dataset("p_excited", np.zeros(self.n_points), broadcast=True)
        self.set_dataset("counts", np.zeros((self.n_points, self.n_shots)), broadcast=True)

        self._counts = np.zeros((self.n_points, self.n_shots))

    def init_device(self):
        self.laser_729.set_frequency(RESONANCE_HZ + self.detuning_hz)
        self.laser_729.set_phase(0)

    def run(self):

        self.init_device()
        self.cooling.doppler_cool()

        for i in range(self.n_points):
            for shot in range(self.n_shots):
                self.cooling.optical_pump()
                T = self.wait_times[i]
                self._counts[i, shot] = self.pulses_and_count(T)

        self.set_dataset("counts", self._counts, broadcast=True)

    @kernel
    def pulses_and_count(self, T: TFloat) -> TInt32:
        self.laser_729.pulse((np.pi / 2) / OMEGA_RABI)
        delay(T)
        self.laser_729.pulse((np.pi / 2) / OMEGA_RABI)
        counts = self.detection.count(ion_index=0, duration=self.measure_duration)
        return counts

    def analyze(self):
        counts_2d = self.get_dataset("counts")
        threshold = (N_BRIGHT + N_DARK) / 2 * self.measure_duration * 1e3
        excited = counts_2d < threshold
        p_excited = excited.mean(axis=1)
        p_err = np.sqrt(p_excited * (1 - p_excited) / self.n_shots)
        self.set_dataset("p_excited", p_excited, broadcast=True)

        def ramsey_model(T, f, phi, T2_star):
            r = np.exp(-T / T2_star)
            return (1 + 2 * r * np.cos(2 * np.pi * f * T + phi) + r**2) / 4

        p0 = [self.detuning_hz, 0.0, T2_STAR]
        bounds = ([0, -np.pi, 1e-6], [1e5, np.pi, 1.0])
        popt, pcov = curve_fit(
            ramsey_model, self.wait_times, p_excited,
            sigma=np.clip(p_err, 1e-3, None),
            p0=p0, bounds=bounds, maxfev=10000,
        )
        f_fit, phi_fit, T2_fit = popt
        f_err, phi_err, T2_err = np.sqrt(np.diag(pcov))

        self.set_dataset("calibration.T2_star", T2_fit, persist=True)
        self.set_dataset("calibration.laser_detuning_hz", f_fit, persist=True)

        print(f"  detuning = {f_fit:7.2f} ± {f_err:.2f} Hz   (set: {self.detuning_hz:.1f} Hz)")
        print(f"  T2*      = {T2_fit*1e3:7.3f} ± {T2_err*1e3:.3f} ms")

        T_fine = np.linspace(self.wait_times.min(), self.wait_times.max(), 1000)
        fit_curve = ramsey_model(T_fine, *popt)
        r_fine = np.exp(-T_fine / T2_fit)
        env_upper = (1 + 2 * r_fine + r_fine**2) / 4
        env_lower = (1 - 2 * r_fine + r_fine**2) / 4

        plt.rcParams.update({
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelsize": 12,
            "xtick.direction": "in",
            "ytick.direction": "in",
        })

        DATA_COLOR = "#2b6cb0"
        FIT_COLOR  = "#c53030"

        fig, ax = plt.subplots(figsize=(8.5, 4.8))

        ax.fill_between(
            T_fine * 1e3, env_lower, env_upper,
            color=FIT_COLOR, alpha=0.08, lw=0,
            label=r"$T_2^*$ envelope",
        )
        ax.errorbar(
            self.wait_times * 1e3, p_excited, yerr=p_err,
            fmt="o", ms=3.2, mfc=DATA_COLOR, mec="none",
            ecolor=DATA_COLOR, elinewidth=0.5, alpha=0.65, capsize=0,
            label=f"data ({self.n_shots} shots/point)",
        )
        ax.plot(
            T_fine * 1e3, fit_curve,
            color=FIT_COLOR, lw=1.7, label="fit",
        )

        ax.set_xlabel(r"Free evolution time  $T$  (ms)")
        ax.set_ylabel(r"$P(|1\rangle)$")
        ax.set_ylim(-0.03, 1.03)
        ax.set_xlim(self.wait_times.min() * 1e3, self.wait_times.max() * 1e3)
        ax.grid(True, alpha=0.25, linestyle=":")

        info = (
            f"$\\delta_\\mathrm{{fit}} = {f_fit:.1f} \\pm {f_err:.1f}$ Hz\n"
            f"$T_2^* = {T2_fit*1e3:.2f} \\pm {T2_err*1e3:.2f}$ ms"
        )
        ax.text(
            0.985, 0.96, info, transform=ax.transAxes,
            ha="right", va="top", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor="white", edgecolor="#bbb", alpha=0.92),
        )
        ax.legend(loc="lower right", framealpha=0.9, fontsize=9, ncol=1)
        ax.set_title("Ramsey spectroscopy", loc="left", fontsize=13, pad=10)

        fig.tight_layout()
        fig.savefig("ramsey_spectroscopy.pdf", bbox_inches="tight")
        plt.close(fig)