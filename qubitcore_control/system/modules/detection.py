from artiq.experiment import kernel
from artiq.language.types import TFloat, TInt32

class DetectionModule():

    def build(self, experiment):
        self._pmt = experiment.get_device("ttl_pmt")

    @kernel
    def count(self, duration: TFloat) -> TInt32: 
        return self._pmt.count(duration)