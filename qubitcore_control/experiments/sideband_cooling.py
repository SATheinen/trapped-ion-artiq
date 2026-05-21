from artiq.experiment import EnvExperiment, kernel, delay, NumberValue
from artiq.language.types import TFloat, TInt32, TNone
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.detection import DetectionModule
from system.services.cooling import CoolingService
from config import RESONANCE_HZ, SECULAR_FREQ
import numpy as np
import matplotlib.pyplot as plt

class SidebandCooling(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_argument("n_shots", NumberValue(default=100))
        self.setattr_argument("n_cooling_steps", NumberValue(default=100))
        self.setattr_argument("measure_duration", NumberValue(default=1e-3, unit='s'))

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
        self.n_shots = int(self.n_shots)
        self.n_cooling_steps = int(self.n_cooling_steps)
        self.measure_duration = float(self.measure_duration)

        self._counts = np.zeros(self.n_shots)

    def init_device(self):
        self.laser_729.set_frequency(RESONANCE_HZ - SECULAR_FREQ / (2 * np.pi))
        self.laser_729.set_phase(0)

    def run(self):

        self.init_device()

        for shot in range(self.n_shots):
            self.cooling.doppler_cool()
            self.cooling.sideband_cool(n_cycles=self.n_cooling_steps)
            self._counts[shot] = self.measure()

        self.set_dataset("counts", self._counts, broadcast=True)

    @kernel
    def measure(self):
        self.laser_729.set_frequency(RESONANCE_HZ + SECULAR_FREQ / (2 * np.pi))
        return self.detection.count(ion_index=0, duration=self.measure_duration)

    def analyze(self):
        counts = self.get_dataset("counts")
        shots = np.arange(self.n_shots)
        mean_counts = float(np.mean(counts))
        std_counts = float(np.std(counts))

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
        REF_COLOR  = "#c53030"

        fig, ax = plt.subplots(figsize=(8.5, 4.8))

        ax.axhline(mean_counts, color=REF_COLOR, lw=0.8, ls="--", alpha=0.6)
        ax.text(1.0, mean_counts, r"$\langle N \rangle$", color=REF_COLOR,
                ha="left", va="center", fontsize=9,
                transform=ax.get_yaxis_transform())

        ax.plot(
            shots, counts,
            marker="o", ms=3.2, mfc=DATA_COLOR, mec="none", lw=0,
            alpha=0.65, label=f"counts (after {self.n_cooling_steps} cycles)",
        )

        ax.set_xlabel("Shot")
        ax.set_ylabel("Photon counts")
        ax.set_xlim(shots.min(), shots.max())
        ax.grid(True, alpha=0.25, linestyle=":")

        info = (
            f"$\\langle N \\rangle = {mean_counts:.2f}$\n"
            f"$\\sigma_N = {std_counts:.2f}$"
        )
        ax.text(
            0.985, 0.96, info, transform=ax.transAxes,
            ha="right", va="top", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor="white", edgecolor="#bbb", alpha=0.92),
        )
        ax.legend(loc="lower right", framealpha=0.9, fontsize=9)
        ax.set_title("Sideband cooling", loc="left", fontsize=13, pad=10)

        fig.tight_layout()
        fig.savefig("sideband_cooling.pdf", bbox_inches="tight")
        plt.close(fig)