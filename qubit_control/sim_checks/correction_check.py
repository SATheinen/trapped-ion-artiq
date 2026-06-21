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
from config import N_IONS, INTERACTION_ZONE, INITIAL_POSITIONS, DATA_IONS
import numpy as np

class RouteCheck(EnvExperiment):
      
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
        np.random.seed(59)
        ion.dephasing_on = False
        zero, one = qt.basis(2,0), qt.basis(2,1)
        readout_duration = 1e-3
        p1 = lambda i: float(ion.psi.ptrace(i)[1,1].real)

        cases = [(None, (0,0)), (0, (1,0)), (2, (1,1)), (4, (0,1))]
        for err, expect in cases:
            kets = [zero]*5
            if err is not None:
                kets[err] = one
            ion.psi = qt.tensor(kets)
            ion.positions = np.array(INITIAL_POSITIONS)
            self.trap_dc._positions = np.array(INITIAL_POSITIONS)

            s0, s1 = self.qec.extract_syndrome(readout_duration)
            corrected = self.qec.correct(s0, s1)

            restored = all(round(p1(d)) == 0 for d in DATA_IONS)
            print(f"err={err}  syn=({s0},{s1}) want={expect}  flagged={corrected}  restored={restored}")
            assert (s0, s1) == expect and corrected == err and restored
        print("OK decode+correct (Checkpoint 4)")