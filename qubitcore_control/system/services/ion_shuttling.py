from artiq.experiment import kernel, delay, ms, us
from artiq.language.types import TInt32, TFloat, TNone
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.laser_729 import Laser729Module
from system.services.cooling import CoolingService
import numpy as np

class ShuttlingService:

    def build(self, trap_dc):
        self._trap_dc = trap_dc
        self.laser_729 = Laser729Module()
        self.laser_729.build(self)
        self.laser_397_cool = Laser397CoolModule()
        self.laser_397_cool.build(self)
        self.laser_397_pump = Laser397PumpModule()
        self.laser_397_pump.build(self)
        self.core = self._trap_dc.core

        self.cooling = CoolingService()
        self.cooling.build(self.laser_729, self.laser_397_cool, self.laser_397_pump)

    def shuttle(self, ion_index, to_z):
        self._trap_dc.shuttle(ion_index, to_z)
    
    def shuttle_and_recool(self, ion_index, to_z):
        self._trap_dc.shuttle(ion_index, to_z)
        self.cooling.doppler_cool()
        self.cooling.full_automatic_sideband_cool()