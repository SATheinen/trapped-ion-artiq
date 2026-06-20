from sim.ion_chain import ion

ion.dephasing_on = False

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

class RouteCheck(EnvExperiment):

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

    def run(self):
        self.shuttling.route_for_cnot(0, 1)