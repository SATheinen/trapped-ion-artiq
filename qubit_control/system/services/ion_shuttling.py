from artiq.experiment import kernel, delay, ms, us
from artiq.language.types import TInt32, TFloat, TNone
from config import ADJACENCY
import numpy as np

class ShuttlingService:

    def build(self, trap_dc, cooling):
        self._trap_dc = trap_dc
        self._cooling = cooling
        self.core = trap_dc.core
        
    def transport(self, ion_index: TInt32, to_z: TInt32) -> TNone:
        current = self._trap_dc.get_zone(ion_index)
        if current == to_z: return

        step = +1 if to_z > current else -1
        path = range(current + step, to_z + step, step)

        # Validate path first
        prev = current
        for z in path:
            assert z in ADJACENCY[prev]
            blocker = self._trap_dc.occupant(z)
            if blocker >= 0:
                raise ValueError(f"transport blocked: zone {z} held by ion {blocker}")
            prev = z

        # Execute
        for z in path:
            self._trap_dc.shuttle(ion_index, z)

    def shuttle(self, ion_index: TInt32, to_z: TInt32) -> TNone:
        self._trap_dc.shuttle(ion_index, to_z)

    def shuttle_and_recool(self, ion_index: TInt32, to_z: TInt32) -> TNone:
        self._trap_dc.shuttle(ion_index, to_z)
        self._cooling.doppler_cool()
        self._cooling.full_automatic_sideband_cool()

    def merge(self, a, b):
      gate = self._trap_dc.interaction_zone
      za, zb = self._trap_dc.get_zone(a), self._trap_dc.get_zone(b)
      if zb not in ADJACENCY[za]:
          raise ValueError(f"merge: ions {a},{b} not adjacent ({za},{zb})")
      if (za == gate) == (zb == gate):     # XOR: exactly one already at the gate
          raise ValueError(f"merge: exactly one of {a},{b} must be at the gate")
      self._trap_dc.merge(a, b)

    def split(self, ion, to_zone):
        gate = self._trap_dc.interaction_zone
        if self._trap_dc.get_zone(ion) != gate:
            raise ValueError(f"split: ion {ion} not at the gate")
        if len(self._trap_dc.ions_in_zone(gate)) != 2:
            raise ValueError("split: need exactly two ions at the gate")
        if self._trap_dc.occupant(to_zone) >= 0:
            raise ValueError(f"split: target zone {to_zone} occupied")
        if to_zone not in ADJACENCY[gate]:
            raise ValueError(f"split: zone {to_zone} not adjacent to gate")
        self._trap_dc.split(ion, to_zone)

    def swap(self, x, y):
        zx, zy = self._trap_dc.get_zone(x), self._trap_dc.get_zone(y)
        if zy not in ADJACENCY[zx]:
            raise ValueError(f"swap: ions {x},{y} not adjacent ({zx},{zy})")
        self._trap_dc.swap(x, y)