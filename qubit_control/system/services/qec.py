import numpy as np
from config import ADJACENCY, RESONANCE_HZ, OMEGA_RABI, SECULAR_FREQ, MS_GATE_TIME, MS_AMPLITUDE, MS_SUM_PHASE

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
        self._729.set_frequency(RESONANCE_HZ) # detuning 0 = carrier
        self._729.set_phase(phi)
        self._729.pulse(theta / OMEGA_RABI) # angle = OMEGA_RABI * duration

    def _ms_gate(self):
        rsb = RESONANCE_HZ - SECULAR_FREQ / (2*np.pi)
        bsb = RESONANCE_HZ + SECULAR_FREQ / (2*np.pi)
        self._729.set_dual_mode(rsb, bsb, MS_AMPLITUDE, MS_SUM_PHASE)
        self._729.pulse(MS_GATE_TIME)

    def cnot(self, c, t):
        self._rotate_isolated(c, -np.pi/2, np.pi/2) # Ry_c(−π/2)
        self._rotate_isolated(c, -np.pi/2, 0.0) # Rx_c(−π/2)
        self._rotate_isolated(t,  np.pi/2, 0.0) # Rx_t(+π/2) 
        # ENTANGLE
        self._shuttling.merge(c, t)
        self._cooling.doppler_cool() # recool
        self._ms_gate() # XX(π/4)
        for z in ADJACENCY[self.gate]: # split t out to an empty neighbour
            if self._trap_dc.occupant(z) < 0:
                self._shuttling.split(t, z)
                break
        else:
            raise RuntimeError("cnot: no empty neighbour to split into")

        self._rotate_isolated(c, np.pi/2, np.pi/2) # Ry_c(+π/2)