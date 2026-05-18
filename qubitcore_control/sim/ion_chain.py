import numpy as np
import qutip as qt

class IonChain:

    def __init__(self):
        self.N_IONS = 3 # Number of Ions in the chain
        self.states = np.array([np.array([1+0j, 0+0j]) for _ in range(self.N_IONS)]) # alpha and beta coefficients of every qbit
        self.n_bar = 10e4 # Phonon motional mode, assuming all zones share one mode (Simplification of reality)
        self.positions = np.array([0, 0, 1]) # Zone each ion is residing in

        self.N_BRIGHT = 40.0 # count / ms
        self.N_DARK = 0.5 # count / ms
        self.omega_rabi = 2 * np.pi * 50e3 # rad/s
        self.RESONANCE_HZ = 200e6 # 1/s
        self.secular_freq = 2*np.pi*50e3
        self.eta = 0.1
        self.T2_star = 1e-3 # 1ms coherence

    def reset_to_ground(self, ion_index: int) -> None:
        self.states[ion_index, :] = np.array([1+0j, 0+0j])

    def apply_rotation(self, ion_index: int, theta: float, phi: float) -> None:
        c, s = np.cos(theta/2), np.sin(theta/2)

        rotation_matrix = np.array([
            [c,                       -1j*np.exp(-1j*phi)*s],
            [-1j*np.exp(1j*phi)*s,    c                    ],
        ])
        # apply rotation
        self.states[ion_index, :] = rotation_matrix @ self.states[ion_index, :]

    def evolve_free(self, ion_index, detuning_rad, duration):
        alpha, beta = self.states[ion_index, :]
        beta = beta * np.exp(1j * detuning_rad * duration)

        # T2* dephasing on the coherence:
        damp = np.exp(-duration / (2*self.T2_star))
        beta = beta * damp

        # Normalize |alpha|² + |beta|² = 1
        norm = np.sqrt(abs(alpha)**2 + abs(beta)**2)
        alpha, beta = alpha/norm, beta/norm
        self.states[ion_index] = np.array([alpha, beta])

    def sample_fluorescence(self, ion_index: int, duration: float) -> int:
        p_excited = np.abs(self.states[ion_index, 1])**2

        # No excitation due to too many phonons
        if self.n_bar > 20.0:
            return int(self.N_BRIGHT * duration * 1e3)

        random_num = np.random.rand()
        if random_num < p_excited:
            # collapse to |1>
            self.states[ion_index, :] = np.array[0+0j, 1+0j]
            return int(np.random.poisson(self.N_DARK * duration * 1e3))
        else:
            # collapse to |0>
            self.states[ion_index, :] = np.array[1+0j, 0+0j]
            return int(np.random.poisson(self.N_BRIGHT * duration * 1e3))

    def apply_pulse(self, ion_index: int, duration: float, delta: float) -> None:
        
        if self.positions[ion_index] != 0:
            raise ValueError(f"Ion {ion_index} not in interaction zone")
        
        # Only applicable on pure |0> states
        alpha, beta = self.states[ion_index, :]
        if np.abs(alpha)**2 != 0:
            raise ValueError(f"Ion {ion_index} must be in pure |0> state for this operation")
        
        omega_eff = np.sqrt(self.omega_rabi**2 + delta**2)

        p_excited = (self.omega_rabi/omega_eff)**2 * np.sin(omega_eff*duration/2)**2

        # treat as effective carrier rotation with that excitation probability
        theta = 2*np.arcsin(np.sqrt(min(p_excited, 1.0)))
        self.apply_rotation(ion_index, theta, 0.0)
        
ion = IonChain()