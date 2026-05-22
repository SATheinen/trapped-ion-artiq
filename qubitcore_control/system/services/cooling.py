from artiq.experiment import kernel, delay, ms, us
from artiq.language.types import TInt32, TFloat, TNone
import numpy as np

from config import RESONANCE_HZ, SECULAR_FREQ, OMEGA_RABI, ETA

class CoolingService:

    def build(self, laser_729, laser_397_cool, laser_397_pump):
        self._laser_729 = laser_729
        self._laser_397_cool = laser_397_cool
        self._laser_397_pump = laser_397_pump
        self.core = laser_397_cool.core

        self.RESONANCE_HZ = RESONANCE_HZ
        self.secular_freq = SECULAR_FREQ
        self.omega_rabi = OMEGA_RABI
        self.eta = ETA

    @kernel
    def doppler_cool(self) -> TNone:
        self._laser_397_cool.pulse(3*ms)

    @kernel
    def optical_pump(self) -> TNone:
        self._laser_397_pump.pulse(500*us)

    def sideband_cool(self, n_cycles: TInt32, duration: TFloat) -> TNone:
        self._laser_729.set_frequency(self.RESONANCE_HZ - self.secular_freq / (2 * np.pi))
        self.optical_pump()
        for _ in range(n_cycles):
            self._cool_cycle(duration)

    def full_automatic_sideband_cool(self):

        def pi_pulse_duration(n):
            return np.pi / (ETA * OMEGA_RABI * np.sqrt(n))

        for i in range(20):
            self.sideband_cool(n_cycles=int(5),
                               duration=pi_pulse_duration(n=(20 - i)))

    @kernel
    def _cool_cycle(self, duration) -> TNone:
        self._laser_729.pulse(duration)
        self.optical_pump()
