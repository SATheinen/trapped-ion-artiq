from artiq.experiment import kernel, delay, us
from artiq.language import TFloat, TNone, TInt32
from config.loader import load_trap_config
from config import INITIAL_POSITIONS, MERGE_HEATING, SPLIT_HEATING, SWAP_HEATING
from pathlib import Path
import numpy as np

class TrapDCModule:

    def build(self, experiment):
        self.core = experiment.core
        self._dc = experiment.get_device("dc_electrodes")
        cfg = load_trap_config()
        config_dir = Path(__file__).parent.parent.parent / "config"

        n = max(cfg.zones) + 1
        self._route_duration = [[0.0 for _ in range(n)] for _ in range(n)]
        self._route_heating = [[0.0 for _ in range(n)] for _ in range(n)]
        self._route_valid = [[False for _ in range(n)] for _ in range(n)]
        self._waveforms = {}    # (from, to) -> (n_frames, 7)

        for (a, b), r in cfg.routes.items():
            self._route_duration[a][b] = r.duration_us
            self._route_heating[a][b] = r.heating.mean
            self._route_valid[a][b] = True
            self._waveforms[(a, b)] = np.load(config_dir / r.waveform_ref)

        self._positions = np.array(INITIAL_POSITIONS)
        self.interaction_zone = cfg.interaction_zone

    def ions_in_zone(self, zone: int) -> list:
        return [int(i) for i in np.where(self._positions == zone)[0]]

    def occupant(self, zone: int) -> int:
        found = np.where(self._positions == zone)[0]
        if found.size > 0:
            return int(found[0])
        else:
            return -1
        
    def merge(self, a, b):
      self._positions[a] = self.interaction_zone
      self._positions[b] = self.interaction_zone
      self._dc.apply_merge(a, b, MERGE_HEATING)

    def split(self, ion, to_zone):
        self._positions[ion] = to_zone
        self._dc.apply_split(ion, to_zone, SPLIT_HEATING)

    def swap(self, x, y):
        self._positions[x], self._positions[y] = self._positions[y], self._positions[x]
        self._dc.apply_swap(x, y, SWAP_HEATING)

    @kernel
    def shuttle(self, ion_index: TInt32, target_zone: TInt32) -> TNone:
        current = self._positions[ion_index]
        if current == target_zone:
            return                          # already there — no waveform, no heating
        if not self._route_valid[current][target_zone]:
            raise ValueError("no route defined for this (from, to)")
        
        waveform = self._waveforms[(current, target_zone)]
        duration_us = self._route_duration[current][target_zone]
        heating_mean = self._route_heating[current][target_zone]

        n_frames = waveform.shape[0]
        dt_us = duration_us / (n_frames - 1)

        for frame in range(n_frames):
            self._dc.set_voltages(waveform[frame])
            delay(dt_us * us)

        self._dc.apply_route_heating(ion_index, current, target_zone, heating_mean)
        self._positions[ion_index] = target_zone

    def get_zone(self, ion_index: int) -> int:
        return self._positions[ion_index]