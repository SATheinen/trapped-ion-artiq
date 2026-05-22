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
        self.setattr_argument("n_shots", NumberValue(default=100))
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
        self.trap_dc.shuttle_and_recool(ion_index=0, to_z=0)
        self.trap_dc.shuttle_and_recool(ion_index=1, to_z=0)

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

        fig, ax = plt.subplots(figsize=(6, 4))
        labels = ["|00⟩", "|01⟩", "|10⟩", "|11⟩"]
        values = [p00, p01, p10, p11]
        colors = ["#2b6cb0", "#aaa", "#aaa", "#2b6cb0"]
        ax.bar(labels, values, color=colors, edgecolor="black", lw=0.5)
        ax.axhline(0.5, color="#c53030", lw=0.8, ls="--", alpha=0.7, label="ideal (0.5)")
        ax.set_ylabel("Probability")
        ax.set_ylim(0, 1)
        ax.set_title("MS gate output populations", loc="left")
        ax.legend(loc="upper right", framealpha=0.9, fontsize=9)
        fig.tight_layout()
        fig.savefig("ms_gate.pdf", bbox_inches="tight")
        plt.close(fig)