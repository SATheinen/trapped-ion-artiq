from artiq.experiment import kernel, TFloat, TInt32, TNone, delay
from config import (
    RESONANCE_HZ, SECULAR_FREQ,
    MS_DETUNING_OFFSET, MS_AMPLITUDE, MS_GATE_TIME, MS_SUM_PHASE,
)

class GateService:

    def build(self, experiment):
        self.laser_729 = experiment.laser_729

        self.carrier_freq = RESONANCE_HZ                      
        self.ms_detuning  = SECULAR_FREQ + MS_DETUNING_OFFSET 
        self.ms_amplitude = MS_AMPLITUDE                         
        self.ms_sum_phase = MS_SUM_PHASE                      
        self.ms_gate_time = MS_GATE_TIME      

    @kernel
    def apply_ms_gate(self) -> TNone:
        f_red = self.carrier_freq - self.ms_detuning
        f_blue = self.carrier_freq + self.ms_detuning

        self.laser_729.set_dual_tone(f_red, f_blue,
                                     self.ms_amplitude,
                                     self.ms_sum_phase)
        self.laser_729.pulse(self.ms_gate_time)