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
from config import N_IONS, INTERACTION_ZONE, DATA_IONS, N_BRIGHT, N_DARK
import numpy as np
import matplotlib.pyplot as plt

class QecZCheck(EnvExperiment):
      
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
        ion.dephasing_on = False
        np.random.seed(445538)
        measure_duration = 3e-3
        n_shots = 40
        self._c0 = [[] for _ in range(4)]       # A0 read counts (s0), per scenario
        self._c1 = [[] for _ in range(4)]       # A1 read counts (s1), per scenario

        EXPECT = [(None,((0,0),None)),
                  (DATA_IONS[0],((1,0),DATA_IONS[0])),
                  (DATA_IONS[1],((1,1),DATA_IONS[1])),
                  (DATA_IONS[2],((0,1),DATA_IONS[2]))]
        self._labels  = ["no error", "X on D0", "X on D1", "X on D2"]
        self._syn = []; self._flagged = []; self._logical = []

        for k, (err, (exp_syn, exp_flag)) in enumerate(EXPECT):
            for _ in range(n_shots):
                if err is not None:
                    self.qec.inject_x(err)
                s0, s1  = self.qec.extract_syndrome(measure_duration)
                c0, c1  = self.qec.last_syndrome_counts
                flagged = self.qec.correct(s0, s1)
                logical = self.qec.logical_readout(measure_duration)
                self.shuttling.route_home()
                self._c0[k].append(c0); self._c1[k].append(c1)
                assert (s0, s1) == exp_syn and flagged == exp_flag and logical == 0
            print(f"{self._labels[k]:9s}  syndrome={exp_syn}  ({n_shots} shots)  OK")
        print("OK repetition-code: syndrome stable over shots; logical |0>_L preserved")

    def analyze(self):
        plt.rcParams.update({ ... })            # the real rcParams block from rabi_flop
        S0_C, S1_C, THR_C = "#2b6cb0", "#2f855a", "#888888"
        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        g = np.arange(4); off = 0.17
        rng = np.random.default_rng(0)
        for k in range(4):
            for counts, color, dx, lbl in [(self._c0[k], S0_C, -off, r"$s_0$  (A0, $Z_0Z_1$)"),
                                            (self._c1[k], S1_C, +off, r"$s_1$  (A1, $Z_1Z_2$)")]:
                x = g[k] + dx + (rng.random(len(counts)) - 0.5) * 0.13      # horizontal jitter
                ax.scatter(x, counts, s=14, color=color, alpha=0.45, edgecolors="none",
                            label=(lbl if k == 0 else None))
        thr = (N_BRIGHT + N_DARK) / 2 * self._dur * 1e3
        ax.axhline(thr, color=THR_C, ls="--", lw=1.0)
        ax.text(3.46, thr, " discrimination threshold", color=THR_C, va="bottom", ha="right", fontsize=8)

        ax.set_xticks(g); ax.set_xticklabels(self._labels)
        ax.set_xlim(-0.5, 3.5); ax.set_ylim(-5, None)
        ax.set_ylabel("PMT counts per ancilla readout")
        ax.set_title("3-qubit bit-flip code — single-shot ancilla readout", loc="left", fontsize=13, pad=10)
        ax.legend(loc="center right", framealpha=0.9, fontsize=9)
        ax.text(0.015, 0.96,
                "each point = one shot's ancilla readout\n"
                "below threshold = dark = $|1\\rangle$ = syndrome bit 1",
                transform=ax.transAxes, ha="left", va="top", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#bbb", alpha=0.92))
        fig.tight_layout(); fig.savefig("qec_x.pdf", bbox_inches="tight"); plt.close(fig)