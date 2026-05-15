import numpy as np
from sim.ion_chain import ion
from artiq.language.types import TFloat, TInt32, TNone

class SimPMT:

    def __init__(self, device_mgr):
        self.device_mgr = device_mgr # Ignore
        self.ion = ion

    def count(self, duration: TFloat) -> TInt32:
        return self.ion.sample_fluorescence(duration)
    
class SimDDS729():

    def __init__(self, device_mgr):
        self.device_mgr = device_mgr # Ignore
        self.ion = ion

        self.frequency = None
        self.sw = self.Switch()

    def set_frequency(self, frequency: TFloat) -> TNone:
        self.frequency = frequency

    def apply_pulse(self, duration: TFloat) -> TNone:
        delta = 2 * np.pi * (self.frequency - ion.RESONANCE_HZ)
        ion.apply_pulse(duration, delta)

    class Switch():
        def __init__(self):
            self.switch = "off"

        def on(self):
            self.switch = "on"

        def off(self):
            self.switch = "off"