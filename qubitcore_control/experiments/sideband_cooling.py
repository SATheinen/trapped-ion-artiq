from artiq.experiment import EnvExperiment, kernel, delay, NumberValue
from artiq.language.types import TFloat, TInt32, TNone
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.detection import DetectionModule
from system.services.cooling import CoolingService
from config.config import RESONANCE_HZ, SECULAR_FREQ, N_DARK, N_BRIGHT, ETA, OMEGA_RABI
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
        self.cooling.build(self.laser_729, self.laser_397_cool, self.laser_397_pump)

    def prepare(self):
        self.n_shots = int(self.n_shots)
        self.n_cooling_steps = int(self.n_cooling_steps)
        self.measure_duration = float(self.measure_duration)

        self.bsb_pi_time = np.pi / (ETA * OMEGA_RABI)

        self._rsb_counts = []
        self._bsb_counts = []

    def init_device(self):
        self.laser_729.set_frequency(RESONANCE_HZ - SECULAR_FREQ / (2 * np.pi))
        self.laser_729.set_phase(0)

    def run(self):

        def pi_pulse_duration(n):
            return np.pi / (ETA * OMEGA_RABI * np.sqrt(n))

        self.init_device()

        for shot in range(self.n_shots):
            self.cooling.doppler_cool()

            for i in range(10):
                self.cooling.sideband_cool(n_cycles=int(self.n_cooling_steps / 10),
                                            duration=pi_pulse_duration(n=(20 -2*i)))

            if shot % 2 == 0:
                self._rsb_counts.append(self.measure(RESONANCE_HZ - SECULAR_FREQ / (2 * np.pi)))
            else:
                self._bsb_counts.append(self.measure(RESONANCE_HZ + SECULAR_FREQ / (2 * np.pi)))

        self.set_dataset("rsb_counts", np.array(self._rsb_counts), broadcast=True)
        self.set_dataset("bsb_counts", np.array(self._bsb_counts), broadcast=True)

    @kernel
    def measure(self, frequency):
        self.laser_729.set_frequency(frequency)
        self.laser_729.pulse(self.bsb_pi_time)
        return self.detection.count(ion_index=0, duration=self.measure_duration)

    def analyze(self):
        rsb_counts = self.get_dataset("rsb_counts")
        bsb_counts = self.get_dataset("bsb_counts")
        n_rsb = len(rsb_counts)
        n_bsb = len(bsb_counts)

        threshold = (N_BRIGHT + N_DARK) / 2 * self.measure_duration * 1e3
        p_rsb = float((rsb_counts < threshold).mean())
        p_bsb = float((bsb_counts < threshold).mean())
        p_rsb_err = np.sqrt(p_rsb * (1 - p_rsb) / max(n_rsb, 1))
        p_bsb_err = np.sqrt(p_bsb * (1 - p_bsb) / max(n_bsb, 1))

        if p_bsb > p_rsb and p_bsb > 0:
            R = p_rsb / p_bsb
            n_bar = R / (1 - R)
            dR_dprsb = 1 / p_bsb
            dR_dpbsb = -p_rsb / p_bsb**2
            R_err = np.sqrt((dR_dprsb * p_rsb_err)**2 + (dR_dpbsb * p_bsb_err)**2)
            n_bar_err = R_err / (1 - R)**2
            n_bar_label = f"$\\bar n = {n_bar:.2f} \\pm {n_bar_err:.2f}$"
        else:
            n_bar = float("nan")
            n_bar_label = r"$\bar n$ undefined ($P_\mathrm{RSB} \geq P_\mathrm{BSB}$)"

        print(f"P_RSB = {p_rsb:.3f} ± {p_rsb_err:.3f}")
        print(f"P_BSB = {p_bsb:.3f} ± {p_bsb_err:.3f}")
        print(f"n_bar = {n_bar:.3f}")
        self.set_dataset("calibration.n_bar", n_bar, persist=True)

        plt.rcParams.update({
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelsize": 12,
            "xtick.direction": "in",
            "ytick.direction": "in",
        })

        RSB_COLOR = "#2b6cb0"
        BSB_COLOR = "#2f855a"
        REF_COLOR = "#c53030"

        all_counts = np.concatenate([rsb_counts, bsb_counts])
        max_count = int(all_counts.max()) + 2
        bins = np.arange(0, max_count + 2) - 0.5

        fig, (ax_rsb, ax_bsb) = plt.subplots(1, 2, figsize=(11.0, 4.6), sharey=True)

        for ax, counts, p, p_err, color, label in [
            (ax_rsb, rsb_counts, p_rsb, p_rsb_err, RSB_COLOR, "RSB"),
            (ax_bsb, bsb_counts, p_bsb, p_bsb_err, BSB_COLOR, "BSB"),
        ]:
            ax.hist(counts, bins=bins, color=color, alpha=0.7, edgecolor="none")
            ax.axvline(threshold, color=REF_COLOR, lw=0.8, ls="--", alpha=0.6)
            ax.text(threshold, 1.02, "threshold", color=REF_COLOR,
                    ha="center", va="bottom", fontsize=9,
                    transform=ax.get_xaxis_transform())
            ax.set_xlabel("Photon counts")
            ax.set_xlim(-0.5, max_count + 0.5)
            ax.grid(True, alpha=0.25, linestyle=":")
            info = (
                f"$P_\\mathrm{{{label}}} = {p:.3f} \\pm {p_err:.3f}$\n"
                f"$N = {len(counts)}$ shots"
            )
            ax.text(
                0.985, 0.96, info, transform=ax.transAxes,
                ha="right", va="top", fontsize=10,
                bbox=dict(boxstyle="round,pad=0.4",
                          facecolor="white", edgecolor="#bbb", alpha=0.92),
            )
            ax.set_title(label, loc="left", fontsize=12, pad=8, color=color)

        ax_rsb.set_ylabel("Occurrences")

        fig.suptitle(
            f"Sideband thermometry after {self.n_cooling_steps} cooling cycles    "
            + n_bar_label,
            x=0.02, ha="left", fontsize=13,
        )

        fig.tight_layout(rect=[0, 0, 1, 0.94])
        fig.savefig("sideband_cooling.pdf", bbox_inches="tight")
        plt.close(fig)