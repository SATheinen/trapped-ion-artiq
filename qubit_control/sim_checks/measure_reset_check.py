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

        spec = ion.psi.ptrace(0)
        spec = spec / spec.tr()                  # free evolution shrank the global norm; renormalize
        # A whole-register reset would give |0><0| (no coherence, p1=0). The spectator DOES dephase
        # over the 500us pump delay (expected T2) — but its state survives the ancilla reset.
        assert abs(spec[0, 1]) > 0.2,            f"spectator coherence destroyed: {spec}"
        assert float(spec[1, 1].real) > 0.1,     f"spectator excited population gone: {spec}"
        print("OK: ancilla reset; spectator coherence intact:", round(abs(spec[0,1]), 3))

        try:                                              # guard fires off-readout
            self.readout.measure_and_reset(0, duration=1e-3)
            print("FAIL")
        except ValueError as e:
            print("OK guard:", e)