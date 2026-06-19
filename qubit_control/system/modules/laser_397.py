from artiq.experiment import kernel, delay
from artiq.language.types import TFloat, TInt32, TNone

class Laser397CoolModule():

    def build(self, experiment):
        self.core = experiment.core
        self._dds_397 = experiment.get_device("dds_397_cool")

    def set_frequency(self, frequency: float) -> None:
        self._dds_397.set_frequency(frequency)

    def set_phase(self, phi: float) -> None:
        self._dds_397.set_phase(phi)

    @kernel
    def pulse(self, duration: TFloat) -> TNone:
        self._dds_397.sw.on()
        delay(duration)
        self._dds_397.sw.off()

class Laser397PumpModule():

    def build(self, experiment):
        self.core = experiment.core
        self._dds_397 = experiment.get_device("dds_397_pump")

    def set_frequency(self, frequency: float) -> None:
        self._dds_397.set_frequency(frequency)

    def set_target_zone(self, zone):
        self._dds_397.set_target_zone(zone)

    def set_phase(self, phi: float) -> None:
        self._dds_397.set_phase(phi)

    @kernel
    def pulse(self, duration: TFloat) -> TNone:
        self._dds_397.sw.on()
        delay(duration)
        self._dds_397.sw.off()