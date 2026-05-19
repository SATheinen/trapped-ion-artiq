from artiq.experiment import kernel, delay
from artiq.language import TFloat, TNone, TInt32

class Laser729Module():

    def build(self, experiment):
        self.core = experiment.core
        self._dds_729 = experiment.get_device("dds_729")

    def set_frequency(self, frequency):
        self._dds_729.set_frequency(frequency)
    
    @kernel
    def pulse(self, ion_index: TInt32, duration: TFloat, phi: TFloat) -> TNone:
        
        # sim-only
        self._dds_729.apply_pulse(ion_index, duration, phi)

        # Hardware
        self._dds_729.sw.on() # Switch AOM on
        delay(duration) # Wait
        self._dds_729.sw.off() # Switch AOM off

    @kernel
    def bloch_pulse(self, ion_index: TInt32, theta: TFloat, phi: TFloat) -> TNone:

        # sim-only
        from ion_chain import ion
        duration = theta / ion.omega_rabi # which unit?
        self._dds_729.bloch_pulse(ion_index, duration, phi)

        # Hardware
        self._dds_729.sw.on() # Switch AOM on
        delay(duration) # Wait
        self._dds_729.sw.off() # Switch AOM off