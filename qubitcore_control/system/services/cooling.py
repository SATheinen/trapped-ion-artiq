from artiq.experiment import kernel, delay, ms, us
from artiq.language.types import TInt32, TNone

class CoolingService:

    def build(self, laser_397_cool, laser_397_pump, detection):
        self._laser_397_cool = laser_397_cool
        self._laser_397_pump = laser_397_pump
        self._detection = detection

    @kernel
    def doppler_cool(self) -> TNone:
        self._laser_397_cool.pulse(3*ms)

    @kernel
    def optical_pump(self) -> TNone:
        self._laser_397_pump.pulse(500*us)