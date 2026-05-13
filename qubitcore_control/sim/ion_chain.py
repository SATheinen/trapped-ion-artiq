import numpy as np

class IonChain:

    def __init__(self):
        self.N_BRIGHT = 40.0
        self.N_DARK = 0.5
        self.state = 0

    def sample_fluorescence(self, duration):
        if self.state == 0:
            return int(np.random.poisson(self.N_BRIGHT * duration * 1e3))
        elif self.state == 1:
            return int(np.random.poisson(self.N_DARK * duration * 1e3))
        else:
            raise ValueError("States can only be |0> or |1>")
        
    def set_state(self, state):
        self.state = state
        
ion = IonChain()