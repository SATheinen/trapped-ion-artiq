import numpy as np
from sim.ion_chain import ion
from artiq.language.types import TFloat, TInt32

class SimPMT:

    def __init__(self):
        self.ion = ion

    def count(self, duration: TFloat) -> TInt32:
        return self.ion.sample_fluorescence(duration)