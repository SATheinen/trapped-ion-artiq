from artiq.experiment import kernel, delay
from artiq.language import TFloat, TNone, TInt32

class Laser729Module():

    def build(self, experiment):
        self.core = experiment.core
        self._dds_729 = experiment.get_device("dds_729")

    def set_frequency(self, frequency):
        self._dds_729.set_frequency(frequency)

    def set_dual_mode(self, f_red, f_blue, amplitude, sum_phase):
        self._dds_729.set_dual_tone(f_red, f_blue, amplitude, sum_phase)

    def set_phase(self, phi):
        self._dds_729.set_phase(phi)
    
    @kernel
    def pulse(self, duration: TFloat) -> TNone:        
        self._dds_729.sw.on() # Switch AOM on
        delay(duration) # Wait
        self._dds_729.sw.off() # Switch AOM off