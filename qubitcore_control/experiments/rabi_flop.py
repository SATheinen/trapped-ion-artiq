from artiq.experiment import EnvExperiment, kernel, NumberValue
from artiq.language.types import TFloat, TInt32
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.detection import DetectionModule
from system.services.cooling import CoolingService
from config import RESONANCE_HZ, OMEGA_RABI
import numpy as np

class RabiFlop(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_argument("measure_duration", NumberValue(default=1e-3))
        self.setattr_argument("pulse_min_duration", NumberValue(default=0e-6))
        self.setattr_argument("pulse_max_duration", NumberValue(default=50e-6))
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

        self.pulse_durations = np.linspace(self.pulse_min_duration, self.pulse_max_duration, self.pulse_n_durations)
        shot_results = np.zeros(self.n_shots)
        duration_results = np.zeros(self.pulse_n_durations)

        self.set_dataset("shot_photon_count", shot_results)
        self.set_dataset("duration_photon_count", duration_results)

    def run(self):
        
        # Set Laser frequency and phase
        self.init_device()

        # Motional mode cooling
        self.cooling.doppler_cool()

        for i, pulse_duration in enumerate(self.pulse_durations):
            for shot in range(self.n_shots):
                
                # Reset state
                self.cooling.optical_pump()                

                # Real Hardware
                self.pulse(pulse_duration) # Send laser pulse
                self.measure(shot)

            average_photons = np.mean(self.get_dataset("shot_photon_count")) # Average counts over shots
            self.mutate_dataset("duration_photon_count", i, average_photons) # write to dataset

    def init_device(self):
        self.laser_729.set_frequency(self.laser_frequency)
        self.laser_729.set_phase(self.laser_phase)

    @kernel
    def pulse(self, duration: TFloat):
        self.laser_729.pulse(duration)            

    @kernel
    def measure(self, shot: TInt32):
        count = self.detection.count(ion_index=0, duration=self.measure_duration)
        self.mutate_dataset("shot_photon_count", shot, count)

    def analyze(self):
        import matplotlib.pyplot as plt
        from scipy.optimize import curve_fit

        t = self.pulse_durations
        data = self.get_dataset("duration_photon_count")

        def rabi_model(t, omega, phi, A, offset):
            return A * np.cos(omega * t + phi) + offset

        p0 = [OMEGA_RABI, 0, 20, 20]
        bounds = ([0, -np.pi, 0, 0],
                  [2 * np.pi * 200e3, np.pi, 40, 40])
        popt, pcov = curve_fit(rabi_model, t, data, p0=p0,
                            bounds=bounds, maxfev=10000)

        omega_fit, phi_fit, A_fit, offset_fit = popt
        omega_err, phi_err, A_err, offset_err = np.sqrt(np.diag(pcov))
        t_pi = (np.pi - phi_fit) / omega_fit
        f_rabi = omega_fit / (2 * np.pi)
        f_rabi_err = omega_err / (2 * np.pi)
        t_fine = np.linspace(t.min(), t.max(), 2000)

        print(f"π-time: {t_pi*1e6:.2f} µs  |  Rabi freq: {f_rabi/1e3:.2f} kHz")

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
        REF_COLOR  = "#2f855a"

        fig, ax = plt.subplots(figsize=(8.5, 4.8))

        ax.axvline(t_pi * 1e6, color=REF_COLOR, lw=0.8, ls="--", alpha=0.6)
        ax.text(t_pi * 1e6, 1.02, r"$t_\pi$", color=REF_COLOR,
                ha="center", va="bottom", fontsize=9,
                transform=ax.get_xaxis_transform())

        ax.plot(
            t * 1e6, data,
            marker="o", ms=3.2, mfc=DATA_COLOR, mec="none", lw=0,
            alpha=0.65, label=f"data ({self.n_shots} shots/point)",
        )
        ax.plot(
            t_fine * 1e6, rabi_model(t_fine, *popt),
            color=FIT_COLOR, lw=1.7, label="fit",
        )

        ax.set_xlabel(r"Pulse duration  $t$  (µs)")
        ax.set_ylabel("Photon counts")
        ax.set_xlim(t.min() * 1e6, t.max() * 1e6)
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