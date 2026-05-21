import numpy as np
from config import (
    N_IONS, N_BAR_INITIAL, N_BAR_DOPPLER,
    N_BRIGHT, N_DARK,
    OMEGA_RABI, RESONANCE_HZ, SECULAR_FREQ, ETA, T2_STAR,
)

class IonChain:

    def __init__(self):
        self.N_IONS = N_IONS
        self.states = np.array([np.array([1+0j, 0+0j]) for _ in range(self.N_IONS)]) # alpha and beta coefficients of every qbit
        self.n_bar = N_BAR_INITIAL # Phonon motional mode, assuming all zones share one mode (Simplification of reality)
        self.n_eq = N_BAR_DOPPLER # laser 397 driven equilibrium motional modes
        self.positions = np.array([0, 0, 1]) # Zone each ion is residing in

        self.N_BRIGHT = N_BRIGHT # count / ms
        self.N_DARK = N_DARK # count / ms
        self.omega_rabi = OMEGA_RABI # rad/s
        self.RESONANCE_HZ = RESONANCE_HZ # 1/s
        self.secular_freq = SECULAR_FREQ
        self.eta = ETA
        self.T2_star = T2_STAR # 1ms coherence

        self.laser_state = "off" # Check if any laser is currently on, required for free_evolution
        self.laser_freq = self.RESONANCE_HZ # get laser frequency to calculate detuning

    def current_detuning_rad(self):
        return 2 * np.pi * (self.laser_freq - self.RESONANCE_HZ)

    def reset_to_ground(self) -> None:
        for i in range(self.N_IONS):
            self.states[i, :] = np.array([1+0j, 0+0j])

    def apply_rotation(self, ion_index: int, theta: float, phi: float) -> None:
        c, s = np.cos(theta/2), np.sin(theta/2)

        rotation_matrix = np.array([
            [c,                       -1j*np.exp(-1j*phi)*s],
            [-1j*np.exp(1j*phi)*s,    c                    ],
        ])
        # apply rotation
        self.states[ion_index, :] = rotation_matrix @ self.states[ion_index, :]

    def free_evolve(self, ion_index, detuning_rad, duration):
        alpha, beta = self.states[ion_index, :]
        beta = beta * np.exp(1j * detuning_rad * duration)

        # T2* dephasing on the coherence:
        damp = np.exp(-duration / (self.T2_star))
        beta = beta * damp

        self.states[ion_index, :] = np.array([alpha, beta])

    def sample_fluorescence(self, ion_index: int, duration: float) -> int:
        p_excited = np.abs(self.states[ion_index, 1])**2

        random_num = np.random.rand()
        if random_num < p_excited:
            # collapse to |1>
            self.states[ion_index, :] = np.array([0+0j, 1+0j])
            return int(np.random.poisson(self.N_DARK * duration * 1e3))
        else:
            # collapse to |0>
            self.states[ion_index, :] = np.array([1+0j, 0+0j])
            return int(np.random.poisson(self.N_BRIGHT * duration * 1e3))

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

        for i in range(self.N_IONS):
            if self.positions[i] == 0: # Only act on active zone
                self.states[i, :] = U @ self.states[i, :]

        # phonon bookkeeping (approximate)
        if kind == "rsb":
            self.n_bar = max(0.0, self.n_bar - p_excited)
        elif kind == "bsb":
            self.n_bar = self.n_bar + p_excited
        
ion = IonChain()