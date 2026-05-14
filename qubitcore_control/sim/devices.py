import numpy as np
from sim.ion_chain import ion
from artiq.language.types import TFloat, TInt32

class SimPMT:

    def __init__(self, device_mgr):
        self.device_mgr = device_mgr # Ignore
        self.ion = ion

    def count(self, duration: TFloat) -> TInt32:
        return self.ion.sample_fluorescence(duration)