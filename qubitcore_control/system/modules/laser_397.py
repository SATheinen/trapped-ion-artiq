from artiq.experiment import kernel, delay
from artiq.language.types import TFloat, TInt32, TNone

class Laser397Module():

    def build(self, experiment):
        self.core = experiment.core
        self._dds_397 = experiment.get_device("dds_397")

    def set_frequency(self, frequency: float) -> None:
        self._dds_397.set_frequency(frequency)

    @kernel
    def pulse(self, duration: TFloat) -> TNone:
        self._dds_397.sw.on()
        self.delay(duration)
        self._dds_397.sw.off()

    @kernel
    def pump_pulse(self, duration: TFloat) -> TNone:
        self._dds_397.sw.on()
        self.delay(duration)
        self._dds_397.sw.off()