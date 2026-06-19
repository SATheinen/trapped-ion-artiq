from artiq.experiment import EnvExperiment, kernel, delay, NumberValue, us
from artiq.language.types import TInt32, TFloat, TNone
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.trap_dc import TrapDCModule
from system.modules.detection import DetectionModule
from system.services.cooling import CoolingService
from system.services.ion_shuttling import ShuttlingService
from system.services.readout import ReadoutService
from config import N_IONS, INITIAL_POSITIONS
import numpy as np

class MeasureResetCheck(EnvExperiment):
      
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
        
    def run(self):
        from sim.ion_chain import ion

        ion.apply_rotation(0, np.pi/2, -np.pi/2)         # spectator D0 (zone 2) -> |+>
        spec_before = ion.psi.ptrace(0)
        ion.apply_rotation(4, np.pi, 0)                  # ancilla D2 (zone 6 = readout) -> |1>

        count = self.readout.measure_and_reset(4, duration=1e-3)
        print("ancilla count:", count)

        assert float(ion.psi.ptrace(4)[1,1].real) < 1e-6                 # ancilla reset to |0>
        assert (ion.psi.ptrace(0) - spec_before).norm() < 1e-9          # spectator |+> UNTOUCHED
        print("OK: ancilla reset, spectator intact")

        try:                                              # guard fires off-readout
            self.readout.measure_and_reset(0, duration=1e-3)
            print("FAIL")
        except ValueError as e:
            print("OK guard:", e)