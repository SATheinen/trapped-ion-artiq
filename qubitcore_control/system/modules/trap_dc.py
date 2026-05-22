from artiq.experiment import kernel, delay, us
from artiq.language import TFloat, TNone, TInt32
from config.loader import load_trap_config
from config import INITIAL_POSITIONS
import numpy as np

class TrapDCModule:

    def build(self, experiment):
          self.core = experiment.core
          self._dc = experiment.get_device("dc_electrodes")
          cfg = load_trap_config()

          n = max(cfg.zones) + 1
          # 2D lookup tables
          self._route_duration = [[0.0 for _ in range(n)] for _ in range(n)]
          self._route_heating  = [[0.0 for _ in range(n)] for _ in range(n)]
          self._route_valid    = [[False for _ in range(n)] for _ in range(n)]
          for (a, b), r in cfg.routes.items():
              self._route_duration[a][b] = r.duration_us
              self._route_heating[a][b]  = r.heating.mean
              self._route_valid[a][b]    = True

          self._positions = np.array(INITIAL_POSITIONS)
          self.interaction_zone = cfg.interaction_zone

    @kernel
    def shuttle(self, ion_index: TInt32, target_zone: TInt32) -> TNone:
        current = self._positions[ion_index]
        if current == target_zone:
            return                          # already there — no waveform, no heating
        if not self._route_valid[current][target_zone]:
            raise ValueError("no route defined for this (from, to)")
        duration = self._route_duration[current][target_zone]
        heating  = self._route_heating[current][target_zone]
        self._dc.execute_route(ion_index, current, target_zone, duration, heating)
        delay(duration * us)
        self._positions[ion_index] = target_zone

    def get_zone(self, ion_index: int) -> int:
        return self._positions[ion_index]