from artiq.experiment import EnvExperiment, kernel, delay, NumberValue, us
from artiq.language.types import TFloat, TInt32, TNone
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.detection import DetectionModule
from system.modules.trap_dc import TrapDCModule
from system.services.cooling import CoolingService
from system.services.ion_shuttling import ShuttlingService
from config import RESONANCE_HZ, SECULAR_FREQ, N_DARK, N_BRIGHT, ETA, OMEGA_RABI
import numpy as np
import matplotlib.pyplot as plt

class ShuttlingCheck(EnvExperiment):

    def build(self):
        self.setattr_argument("n_shots", NumberValue(default=100))
        self.setattr_argument("measure_duration", NumberValue(default=1e-3))

        self.setattr_device("core")
        self.laser_729 = Laser729Module()    
        self.laser_729.build(self)
        self.laser_397_cool = Laser397CoolModule()  
        self.laser_397_cool.build(self)
        self.laser_397_pump = Laser397PumpModule()   
        self.laser_397_pump.build(self)
        self.detection = DetectionModule()      
        self.detection.build(self)
        self.trap_dc = TrapDCModule()        
        self.trap_dc.build(self)

        self.cooling = CoolingService()
        self.cooling.build(self.laser_729, self.laser_397_cool,
                            self.laser_397_pump, self.detection)

        self.shuttling = ShuttlingService()
        self.shuttling.build(self.trap_dc, self.laser_729, self.cooling)

    def prepare(self):
        self.n_shots = int(self.n_shots)
        self.measure_duration = float(self.measure_duration)

        self.bsb_pi_time = np.pi / (ETA * OMEGA_RABI)
        self.rbs_msr_freq = RESONANCE_HZ - SECULAR_FREQ / (2 * np.pi)
        self.bbs_msr_freq = RESONANCE_HZ + SECULAR_FREQ / (2 * np.pi)

        self.set_dataset(
          "counts",
          np.zeros((3, 2, self.n_shots // 2), dtype=np.int32),
          broadcast=True,
      )

    @kernel
    def run(self):
        for shot in range(self.n_shots):
            sideband = shot % 2
            pair_idx = shot // 2
            freq     = self.rbs_msr_freq if sideband == 0 else self.bbs_msr_freq

            # Stage 0 — cooled
            self.cooling.doppler_cool()
            self.cooling.full_automatic_sideband_cool()
            self.mutate_dataset("counts", (0, sideband, pair_idx), self.measure(freq))

            # Stage 1 — after shuttle, no recool
            self.shuttling.shuttle(ion_index=2, to_z=0)
            self.mutate_dataset("counts", (1, sideband, pair_idx), self.measure(freq))

            # Stage 2 — after shuttle-and-recool (return to zone 1)
            self.shuttling.shuttle_and_recool(ion_index=2, to_z=1)
            self.mutate_dataset("counts", (2, sideband, pair_idx), self.measure(freq))

    @kernel
    def measure(self, frequency):
        self.laser_729.set_frequency(frequency)
        self.laser_729.pulse(self.bsb_pi_time)
        return self.detection.count(ion_index=0, duration=self.measure_duration)
    
    def analyze(self):
        counts = self.get_dataset("counts")    # (3, 2, n_pairs)
        n_pairs = counts.shape[2]

        threshold = (N_BRIGHT + N_DARK) / 2 * self.measure_duration * 1e3

        STAGES = ["Cooled", "After shuttle", "After recool"]
        n_bar     = np.full(3, np.nan)
        n_bar_err = np.full(3, np.nan)
        p_rsb     = np.zeros(3)
        p_bsb     = np.zeros(3)
        p_rsb_err = np.zeros(3)
        p_bsb_err = np.zeros(3)

        for s in range(3):
            rsb = counts[s, 0, :]
            bsb = counts[s, 1, :]
            p_rsb[s] = float((rsb < threshold).mean())
            p_bsb[s] = float((bsb < threshold).mean())
            p_rsb_err[s] = np.sqrt(p_rsb[s] * (1 - p_rsb[s]) / max(n_pairs, 1))
            p_bsb_err[s] = np.sqrt(p_bsb[s] * (1 - p_bsb[s]) / max(n_pairs, 1))

            if p_bsb[s] > p_rsb[s] and p_bsb[s] > 0:
                R = p_rsb[s] / p_bsb[s]
                n_bar[s] = R / (1 - R)
                dR_drsb = 1 / p_bsb[s]
                dR_dbsb = -p_rsb[s] / p_bsb[s]**2
                R_err = np.sqrt((dR_drsb * p_rsb_err[s])**2 + (dR_dbsb * p_bsb_err[s])**2)
                n_bar_err[s] = R_err / (1 - R)**2

            print(f"[{STAGES[s]:<14}]  "
                    f"P_RSB = {p_rsb[s]:.3f} ± {p_rsb_err[s]:.3f}  "
                    f"P_BSB = {p_bsb[s]:.3f} ± {p_bsb_err[s]:.3f}  "
                    f"n_bar = {n_bar[s]:.3f} ± {n_bar_err[s]:.3f}")

        self.set_dataset("calibration.n_bar_shuttling", n_bar, persist=True)

        plt.rcParams.update({
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelsize": 12,
            "xtick.direction": "in",
            "ytick.direction": "in",
        })

        COOLED_COLOR    = "#2b6cb0"   # blue  — same as RSB in sideband_cooling
        SHUTTLED_COLOR  = "#c05621"   # orange — heating stage
        RECOOLED_COLOR  = "#2f855a"   # green — same as BSB in sideband_cooling
        REF_COLOR       = "#c53030"
        stage_colors    = [COOLED_COLOR, SHUTTLED_COLOR, RECOOLED_COLOR]

        fig, ax = plt.subplots(figsize=(8.2, 4.8))

        xs = np.arange(3)
        bars = ax.bar(xs, n_bar, yerr=n_bar_err, color=stage_colors,
                        alpha=0.78, capsize=5, edgecolor="none")

        # Reference line for the cooled n̄ — visualises how far above we land
        if not np.isnan(n_bar[0]):
            ax.axhline(n_bar[0], color=REF_COLOR, lw=0.8, ls="--", alpha=0.6)
            ax.text(2.45, n_bar[0], "cooled baseline",
                    color=REF_COLOR, ha="right", va="bottom", fontsize=9)

        # Per-bar value annotation
        for x, n, err in zip(xs, n_bar, n_bar_err):
            if not np.isnan(n):
                ax.text(x, n + err + 0.08,
                        f"$\\bar n = {n:.2f} \\pm {err:.2f}$",
                        ha="center", va="bottom", fontsize=10)

        ax.set_xticks(xs)
        ax.set_xticklabels(STAGES)
        ax.set_ylabel(r"$\bar n$  (motional quanta)")
        ax.grid(True, alpha=0.25, linestyle=":", axis="y")
        ax.set_ylim(bottom=0)

        fig.suptitle(
            f"Shuttling heating verification    "
            f"$N = {n_pairs}$ shots per sideband",
            x=0.02, ha="left", fontsize=13,
        )

        fig.tight_layout(rect=[0, 0, 1, 0.94])
        fig.savefig("shuttling.pdf", bbox_inches="tight")
        plt.close(fig)