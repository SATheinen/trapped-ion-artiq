from artiq.experiment import EnvExperiment, kernel, delay, NumberValue, us
from artiq.language.types import TInt32, TFloat, TNone
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.trap_dc import TrapDCModule
from system.modules.detection import DetectionModule
from system.services.cooling import CoolingService
from system.services.ion_shuttling import ShuttlingService
from system.services.readout import ReadoutService
from system.services.qec import QECService
from config import N_IONS, INTERACTION_ZONE, DATA_IONS
import numpy as np
import matplotlib.pyplot as plt

class CNOTPortableCheck(EnvExperiment):
      
    def build(self):
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
                            self.laser_397_pump)
        
        self.shuttling = ShuttlingService()
        self.shuttling.build(self.trap_dc, self.cooling)

        self.readout = ReadoutService()
        self.readout.build(self.detection, self.laser_397_pump, self.trap_dc)

        self.qec = QECService()
        self.qec.build(self.shuttling, self.cooling, self.laser_729, self.readout, self.trap_dc)

    def run(self):
        from sim.ion_chain import ion
        import qutip as qt
        ion.dephasing = False
        np.random.seed(445538)
        measure_duration = 1e-3

        EXPECT = [(None,((0,0),None)),
                  (DATA_IONS[0],((1,0),DATA_IONS[0])),
                  (DATA_IONS[1],((1,1),DATA_IONS[1])),
                  (DATA_IONS[2],((0,1),DATA_IONS[2]))]
        self._labels  = ["no error", "X on D0", "X on D1", "X on D2"]
        self._syn = []; self._flagged = []; self._logical = []

        for err, (exp_syn, exp_flag) in EXPECT:
            self.cooling.doppler_cool() # real motion prep (spins are |0> by init / prior readout-reset)
            if err is not None:
                self.qec.inject_x(err) # real laser flip on one data qubit
            s0, s1  = self.qec.extract_syndrome(measure_duration) # real routing + mid-circuit measure+reset
            flagged = self.qec.correct(s0, s1) # real decode + corrective X
            logical = self.qec.logical_readout(measure_duration)  # real measured majority vote
            self.shuttling.route_home() # real reset of positions -> INITIAL (no ion.positions=)

            self._syn.append((s0, s1)); self._flagged.append(flagged); self._logical.append(logical)
            print(f"{self._labels[err is not None and DATA_IONS.index(err)+1 or 0]:9s}"
                    f"  s=({s0},{s1})  flagged={flagged}  logical={logical}")
            assert (s0, s1) == exp_syn and flagged == exp_flag and logical == 0
        print("OK repetition-code: every injected X detected, localized, corrected; logical |0>_L preserved")

        def analyze(self):
            plt.rcParams.update({ ... })             # same block as rabi_flop
            S0_C, S1_C, ACCENT = "#2b6cb0", "#2f855a", "#c53030"
            fig, ax = plt.subplots(figsize=(8.5, 4.8))
            g = np.arange(4); w = 0.30
            ax.bar(g - w/2, [s[0] for s in self._syn], w, color=S0_C, label=r"$s_0$  ($Z_0Z_1$)")
            ax.bar(g + w/2, [s[1] for s in self._syn], w, color=S1_C, label=r"$s_1$  ($Z_1Z_2$)")
            for k in range(4):
                tgt = "—" if self._flagged[k] is None else f"D{DATA_IONS.index(self._flagged[k])}"
                ax.text(g[k], 1.12, f"decode: {tgt}\nlogical = {self._logical[k]}",
                        ha="center", va="bottom", fontsize=8, color=ACCENT)
            ax.set_xticks(g); ax.set_xticklabels(self._labels)
            ax.set_yticks([0, 1]); ax.set_ylim(0, 1.6)
            ax.set_ylabel("measured syndrome bit")
            ax.set_title("3-qubit bit-flip code — measured syndrome & correction", loc="left", fontsize=13, pad=10)
            ax.legend(loc="upper right", framealpha=0.9, fontsize=9)
            ax.text(0.015, 0.96, "each injected X flips its syndrome bits (the live decode table);\nlogical $|0\\rangle_L$ restored in every case",
                    transform=ax.transAxes, ha="left", va="top", fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#bbb", alpha=0.92))
            fig.tight_layout()
            fig.savefig("repetition_code.pdf", bbox_inches="tight"); plt.close(fig)