from config import READOUT_ZONE

class ReadoutService:
    def build(self, detection, laser_397_pump, trap_dc):
        self._detection = detection
        self._pump = laser_397_pump
        self._trap_dc = trap_dc
        self.core = trap_dc.core

    def measure_and_reset(self, ion_index, duration):
        z = self._trap_dc.get_zone(ion_index)
        if z != READOUT_ZONE:
            raise ValueError(f"measure_and_reset: ion {ion_index} at zone {z}, not READOUT_ZONE")
        count = self._detection.count(ion_index, duration)   # MEASURE first (collapses ion)
        self._pump.set_target_zone(READOUT_ZONE)             # THEN reset
        self._pump.pulse(500e-6)
        return count