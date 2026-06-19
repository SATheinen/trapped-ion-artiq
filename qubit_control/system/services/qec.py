import numpy as np
from config import ADJACENCY, RESONANCE_HZ, OMEGA_RABI

class QECService:
    def build(self, shuttling, cooling, laser_729, readout, trap_dc):
        self._shuttling = shuttling; self._cooling = cooling
        self._729 = laser_729; self._readout = readout; self._trap_dc = trap_dc
        self.core = trap_dc.core
        self.gate = trap_dc.interaction_zone

    def _rotate_isolated(self, ion, theta, phi):
        # 1. clear the gate of any OTHER ion
        occ = self._trap_dc.occupant(self.gate)
        if occ >= 0 and occ != ion:
            for z in ADJACENCY[self.gate]:
                if self._trap_dc.occupant(z) < 0:
                    self._shuttling.transport(occ, z); break
            else:
                raise RuntimeError("_rotate_isolated: no empty neighbour to clear the gate")
        # 2. bring ion to the gate
        self._shuttling.transport(ion, self.gate)
        # 3. carrier 729 pulse
        if theta < 0:
            phi += np.pi; theta = -theta
        self._729.set_frequency(RESONANCE_HZ)     # detuning 0 = carrier
        self._729.set_phase(phi)
        self._729.pulse(theta / OMEGA_RABI)       # angle = OMEGA_RABI · duration