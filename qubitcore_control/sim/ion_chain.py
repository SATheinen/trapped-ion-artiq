import numpy as np
import qutip as qt

class IonChain:

    def __init__(self):
        self.N_BRIGHT = 40.0 # count / ms
        self.N_DARK = 0.5 # count / ms
        self.omega_rabi = 2 * np.pi * 50e3 # rad/s
        self.RESONANCE_HZ = 200e6 # 1/s
        self.psi0 = qt.basis(2, 0)
        self.psi1 = qt.basis(2, 1)
        self.state = self.psi0

    def apply_pulse(self, duration, delta):
        H = (delta / 2) * qt.sigmaz() + (self.omega_rabi / 2) * qt.sigmax() # define Hamiltonian for state evolution

        times = [0, duration] # start and end time
        result = qt.mesolve(H, self.state, times, [], [])
        self.state = result.states[-1] # state at end of pulse

    def sample_fluorescence(self, duration):

        projector0 = self.psi0 * self.psi0.dag()
        prob0 = qt.expect(projector0, self.state)

        # State collapses
        random_num = np.random.rand()
        if random_num < prob0:
            self.state = self.psi0
            return int(np.random.poisson(self.N_BRIGHT * duration * 1e3))
        else:
            self.state = self.psi1
            return int(np.random.poisson(self.N_DARK * duration * 1e3))
    
    # Set state by hand
    def set_state(self, state):
        if state == 0:
            self.state = self.psi0
        elif state == 1:
            self.state = self.psi1
        else:
            raise ValueError("This function only supports setting states to 1 or 0")
        
ion = IonChain()