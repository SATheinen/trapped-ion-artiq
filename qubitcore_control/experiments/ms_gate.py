from artiq.experiment import EnvExperiment, kernel, delay, NumberValue, us
from artiq.language.types import TFloat, TInt32, TNone
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.detection import DetectionModule
from system.modules.trap_dc import TrapDCModule
from system.services.cooling import CoolingService
from system.services.ion_shuttling import ShuttlingService
from system.services.gate_service import GateService
from config import RESONANCE_HZ, SECULAR_FREQ, N_DARK, N_BRIGHT, ETA, OMEGA_RABI
import numpy as np
import matplotlib.pyplot as plt

class MSGate(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_argument("n_shots", NumberValue(default=300))
        self.setattr_argument("measure_duration", NumberValue(default=1e-3))

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
                            self.laser_397_pump)

        self.shuttling = ShuttlingService()
        self.shuttling.build(self.trap_dc, self.cooling)

        self.gate = GateService()
        self.gate.build(self)
    
    def prepare(self):
        self.n_shots = int(self.n_shots)
        self.measure_duration = float(self.measure_duration)

        self.set_dataset("o0_counts", np.zeros(self.n_shots), broadcast=True)
        self.set_dataset("o1_counts", np.zeros(self.n_shots), broadcast=True)

    def run(self):

        for shot in range(self.n_shots):
            self.run_shot(shot)

    @kernel
    def run_shot(self, shot):
        self.cooling.doppler_cool()
        self.cooling.full_automatic_sideband_cool()
        self.cooling.optical_pump()

        # Shuttle
        self.shuttling.shuttle_and_recool(ion_index=0, to_z=0)
        self.shuttling.shuttle_and_recool(ion_index=1, to_z=0)

        # ms gate
        self.gate.apply_ms_gate()

        # detection
        o0 = self.detection.count(0, self.measure_duration)
        o1 = self.detection.count(1, self.measure_duration)

        self.mutate_dataset("o0_counts", shot, o0)
        self.mutate_dataset("o1_counts", shot, o1)

    def analyze(self):
        o0 = np.array(self.get_dataset("o0_counts"))
        o1 = np.array(self.get_dataset("o1_counts"))

        # Threshold each shot — bright (above) → |0⟩, dark (below) → |1⟩
        threshold = 0.5 * (N_BRIGHT + N_DARK) * self.measure_duration * 1e3
        q0 = (o0 < threshold).astype(int)
        q1 = (o1 < threshold).astype(int)

        p00 = np.mean((q0 == 0) & (q1 == 0))
        p01 = np.mean((q0 == 0) & (q1 == 1))
        p10 = np.mean((q0 == 1) & (q1 == 0))
        p11 = np.mean((q0 == 1) & (q1 == 1))

        p_pop   = p00 + p11
        leakage = p01 + p10

        print(f"P(00) = {p00:.3f}")
        print(f"P(01) = {p01:.3f}")
        print(f"P(10) = {p10:.3f}")
        print(f"P(11) = {p11:.3f}")
        print(f"Bell-subspace population (P_00 + P_11) = {p_pop:.3f}")
        print(f"Leakage (P_01 + P_10)                  = {leakage:.3f}")

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
        LEAK_COLOR   = "#a0aec0"
        FIT_COLOR    = "#c53030"

        values = np.array([p00, p01, p10, p11])
        errs   = np.sqrt(values * (1 - values) / max(self.n_shots, 1))
        labels = [r"$|00\rangle$", r"$|01\rangle$", r"$|10\rangle$", r"$|11\rangle$"]
        colors = [DATA_COLOR, LEAK_COLOR, LEAK_COLOR, DATA_COLOR]

        fig, ax = plt.subplots(figsize=(8.5, 4.8))

        ax.bar(labels, values, yerr=errs, color=colors, alpha=0.78,
               capsize=5, edgecolor="none")
        ax.axhline(0.5, color=FIT_COLOR, lw=0.8, ls="--", alpha=0.6,
                   label="ideal (0.5)")

        for x, v, e in zip(range(4), values, errs):
            ax.text(x, v + e + 0.02, f"{v:.3f}",
                    ha="center", va="bottom", fontsize=10)

        ax.set_ylabel(r"$P$")
        ax.set_ylim(0, 1.10)
        ax.grid(True, alpha=0.25, linestyle=":", axis="y")

        info = (
            f"$P_{{00}} + P_{{11}} = {p_pop:.3f}$\n"
            f"leakage $= {leakage:.3f}$\n"
            f"$N = {self.n_shots}$ shots"
        )
        ax.text(
            0.985, 0.96, info, transform=ax.transAxes,
            ha="right", va="top", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor="white", edgecolor="#bbb", alpha=0.92),
        )
        ax.legend(loc="upper left", framealpha=0.9, fontsize=9)
        ax.set_title("MS gate output populations", loc="left", fontsize=13, pad=10)

        fig.tight_layout()
        fig.savefig("ms_gate.pdf", bbox_inches="tight")
        plt.close(fig)