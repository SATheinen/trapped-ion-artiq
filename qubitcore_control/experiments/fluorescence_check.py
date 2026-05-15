from artiq.experiment import EnvExperiment, kernel, NumberValue
from artiq.language.types import TFloat, TInt32
import numpy as np
from system.modules.detection import DetectionModule


class FluorescenceCheck(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_argument("duration", NumberValue(default=1e-3))
        self.setattr_argument("n_shots", NumberValue(default=100))
        self.detection = DetectionModule()
        self.detection.build(self)

    def prepare(self):
        self.n_shots = int(self.n_shots)
        self.duration = float(self.duration)

        bright_result = np.zeros(self.n_shots)
        dark_result = np.zeros(self.n_shots)

        self.set_dataset("bright_fluorescence_count", bright_result)
        self.set_dataset("dark_fluorescence_count", dark_result)

    ##################################
    # sim-only
    def prepare_state(self, state):
        from sim.ion_chain import ion
        ion.set_state(state)
    ##################################

    def run(self):
        
        # Bright experiment
        # sim-only
        self.prepare_state(state=0)

        for shot in range(self.n_shots):
            self.measure_bright(shot)

        # Dark experiment
        # sim-only
        self.prepare_state(state=1)

        for shot in range(self.n_shots):
            self.measure_dark(shot)

    @kernel
    def measure_bright(self, shot: TInt32):
        count = self.detection.count(self.duration)
        self.mutate_dataset("bright_fluorescence_count", shot, count) # Dataset name, index, value

    @kernel
    def measure_dark(self, shot: TInt32):
        count = self.detection.count(self.duration)
        self.mutate_dataset("dark_fluorescence_count", shot, count) # Dataset name, index, value
    
    def analyze(self):
        mean_bright = np.mean(self.get_dataset("bright_fluorescence_count"))
        mean_dark = np.mean(self.get_dataset("dark_fluorescence_count"))
        print(f"Bright mean:{mean_bright}, Dark mean:{mean_dark}")