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