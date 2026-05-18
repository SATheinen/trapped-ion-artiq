from artiq.experiment import kernel, delay, ms, us
from artiq.language.types import TInt32, TNone

class CoolingService:

    def build(self, laser_397, detection, ion_chain):
        self._laser_397 = laser_397
        self._detection = detection
        self._ion = ion_chain

    @kernel
    def doppler_cool(self) -> TNone:
        self._laser_397.pulse(3*ms)

        # sim-only
        self._sim_set_n_bar(20.0)

    @kernel
    def optical_pump(self, ion_index: TInt32) -> TNone:
        self._laser_397.pump_pulse(500*us)

        # sim-only
        self._sim_reset_ion(ion_index)


    # sim-only RPCs
    def _sim_set_n_bar(self, n_bar: float) -> None:
        self._ion.n_bar = n_bar

    def _sim_reset_ion(self, ion_index: int) -> None:
        self._ion.reset_to_ground(ion_index)