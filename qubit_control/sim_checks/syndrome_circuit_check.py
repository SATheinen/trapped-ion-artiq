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
from config import N_IONS, INTERACTION_ZONE
import numpy as np

class SyndromeCircuitCheck(EnvExperiment):
      
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
        zero, one = qt.basis(2,0), qt.basis(2,1)

        def stage(c, t): # test scaffold ONLY (no transport)
            others = [i for i in range(N_IONS) if i not in (c, t)]
            pos = {c: 3, t: 2} # control@gate, target(ancilla)@neighbour 2, zone 4 free
            for i, z in zip(others, [0, 1, N_IONS]):
                pos[i] = z # spectators parked outside the gate region {2,3,4}
            arr = np.array([pos[i] for i in range(N_IONS)])
            ion.positions = arr.copy(); self.trap_dc._positions = arr.copy()

        def p1(i):
            return float(ion.psi.ptrace(i)[1, 1].real)

        CNOTS = [(0,1), (2,1), (2,3), (4,3)] # (D0→A0),(D1→A0),(D1→A1),(D2→A1)
        for d0, d1, d2 in [(0,0,0),(1,0,0),(0,1,0),(0,0,1),(1,1,1)]:
            kets = [zero]*5
            kets[0] = one if d0 else zero
            kets[2] = one if d1 else zero
            kets[4] = one if d2 else zero
            ion.psi = qt.tensor(kets) # data classical, ancillas |0>
            for c, t in CNOTS:
                stage(c, t); self.qec.cnot(c, t)
            s0, s1 = round(p1(1)), round(p1(3)) # A0=ion1, A1=ion3
            ok = (s0 == d0 ^ d1) and (s1 == d1 ^ d2)
            print(f"|{d0}{d1}{d2}>  s=({s0},{s1})  want=({d0^d1},{d1^d2})  {'OK' if ok else 'FAIL'}")
            assert ok
        print("OK syndrome circuit (manual staging)")