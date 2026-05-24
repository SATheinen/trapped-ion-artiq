import numpy as np
import qutip as qt

from config import (
    N_IONS, N_BAR_INITIAL, N_BAR_DOPPLER,
    N_BRIGHT, N_DARK,
    OMEGA_RABI, RESONANCE_HZ, SECULAR_FREQ, ETA, T2_STAR, MS_GATE_TIME,
    INITIAL_POSITIONS, INTERACTION_ZONE,
)

class IonChain:

    def __init__(self):
        self.N_IONS = N_IONS
        self.psi = qt.tensor([qt.basis(2, 0)] * self.N_IONS) # initialize psi for N_IONS in groundstate
        self.n_bar = N_BAR_INITIAL # Phonon motional mode, assuming all zones share one mode (Simplification of reality)
        self.n_eq = N_BAR_DOPPLER # laser 397 driven equilibrium motional modes
        self.positions = np.array(INITIAL_POSITIONS) # Zone each ion is residing in

        self.N_BRIGHT = N_BRIGHT # count / ms
        self.N_DARK = N_DARK # count / ms
        self.omega_rabi = OMEGA_RABI # rad/s
        self.RESONANCE_HZ = RESONANCE_HZ # 1/s
        self.secular_freq = SECULAR_FREQ
        self.eta = ETA
        self.T2_star = T2_STAR # 1ms coherence

        self.laser_state = "off" # Check if any laser is currently on, required for free_evolution
        self.laser_freq = self.RESONANCE_HZ # get laser frequency to calculate detuning

    def _single_ion_op(self, op, ion_index):
        ops = [qt.qeye(2)] * self.N_IONS
        ops[ion_index] = op
        return qt.tensor(ops)

    def current_detuning_rad(self):
        return 2 * np.pi * (self.laser_freq - self.RESONANCE_HZ)

    def reset_to_ground(self) -> None:
        self.psi = qt.tensor([qt.basis(2, 0)] * self.N_IONS)

    def apply_rotation(self, ion_index: int, theta: float, phi: float) -> None:
        c, s = np.cos(theta/2), np.sin(theta/2)

        R = qt.Qobj([
            [c,                       -1j*np.exp(-1j*phi)*s],
            [-1j*np.exp(1j*phi)*s,    c                    ],
        ])
        U = self._single_ion_op(R, ion_index)
        # apply rotation
        self.psi = U * self.psi

    def free_evolve(self, ion_index, detuning_rad, duration):
        damp = np.exp(-duration / self.T2_star)              # ✓ real, dimensionless damping
        D = qt.Qobj([
            [1, 0],
            [0, damp * np.exp(1j * detuning_rad * duration)] # phase applied once
        ])

        U = self._single_ion_op(D, ion_index)
        self.psi = U * self.psi

    def sample_fluorescence(self, ion_index: int, duration: float) -> int:
        rho_i = self.psi.ptrace(ion_index)
        p_excited = float(rho_i[1, 1].real)

        outcome = 1 if np.random.rand() < p_excited else 0

        ket_b = qt.basis(2, outcome)
        proj = ket_b * ket_b.dag()
        P_full = self._single_ion_op(proj, ion_index)
        self.psi = (P_full * self.psi).unit()

        rate = self.N_DARK if outcome == 1 else self.N_BRIGHT
        return int(np.random.poisson(rate * duration * 1e3))

    def apply_pulse(self, duration: float, detuning_rad: float, phi: float) -> None:
        delta = detuning_rad

        # distance from resonance
        d_carrier = abs(delta)
        d_rsb = abs(delta + self.secular_freq)
        d_bsb = abs(delta - self.secular_freq)

        # pick nearest
        if d_carrier <= d_rsb and d_carrier <= d_bsb:
            eff_rabi = self.omega_rabi
            residual = delta
            kind = "carrier"
        elif d_rsb <= d_bsb:
            eff_rabi = self.omega_rabi * self.eta * np.sqrt(max(self.n_bar, 1e-6))
            residual = delta + self.secular_freq
            kind = "rsb"
        else:
            eff_rabi = self.omega_rabi * self.eta * np.sqrt(self.n_bar + 1)
            residual = delta - self.secular_freq
            kind = "bsb"

        # generalised Rabi
        Omega_eff = np.sqrt(eff_rabi**2 + residual**2)
        p_excited = (eff_rabi/Omega_eff)**2 * np.sin(Omega_eff*duration/2)**2

        half = Omega_eff * duration / 2
        c, s = np.cos(half), np.sin(half)

        nx_xy = eff_rabi/Omega_eff
        nz = residual/Omega_eff

        U = np.array([
            [c - 1j*nz*s,                        -1j*nx_xy*np.exp(-1j*phi)*s],
            [-1j*nx_xy*np.exp(1j*phi)*s,          c + 1j*nz*s               ],
        ])

        U_qobj = qt.Qobj(U)
        ops = [U_qobj if self.positions[i] == INTERACTION_ZONE else qt.qeye(2) for i in range(self.N_IONS)]
        U_full = qt.tensor(ops)
        self.psi = U_full * self.psi

        # phonon bookkeeping (approximate)
        if kind == "rsb":
            self.n_bar = max(0.0, self.n_bar - p_excited)
        elif kind == "bsb":
            self.n_bar = self.n_bar + p_excited

    def apply_ms_gate(self, duration):
        if np.sum(self.positions == INTERACTION_ZONE) != 2:
            raise ValueError(f"MS gate requires exactly two ions in zone {INTERACTION_ZONE}")
        if self.n_bar > 0.1:
          print(f"WARNING: MS gate with n_bar={self.n_bar:.2f}, fidelity will degrade.")

        chi = np.pi / 4 * (duration / MS_GATE_TIME)

        zone_ions = np.where(self.positions == INTERACTION_ZONE)[0]
        ion_a, ion_b = int(zone_ions[0]), int(zone_ions[1])

        ops = [qt.qeye(2)] * self.N_IONS
        ops[ion_a] = qt.sigmax()
        ops[ion_b] = qt.sigmax()
        Sxx_full = qt.tensor(ops)

        U_ms = (-1j * chi * Sxx_full).expm()
        self.psi = U_ms * self.psi

    def shuttle(self, ion_index, from_z, to_z, heating):
        if self.positions[ion_index] != from_z: # check if ion is in the correct zone
            raise ValueError(f"Ion {ion_index} is in zone {self.positions[ion_index]}, not {from_z}")
        self.positions[ion_index] = to_z # Move ion
        # Heating goes to the shared phonon mode regardless of destination —
        # the gate-zone ion sees it because the mode is shared across all zones.
        self.n_bar += heating
        
ion = IonChain()