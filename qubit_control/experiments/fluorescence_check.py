from artiq.experiment import EnvExperiment, kernel, NumberValue
from artiq.language.types import TFloat, TInt32
import numpy as np
from system.modules.detection import DetectionModule
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.services.cooling import CoolingService
from config import RESONANCE_HZ, OMEGA_RABI

class FluorescenceCheck(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_argument("duration", NumberValue(default=1e-3))
        self.setattr_argument("n_shots", NumberValue(default=100))
        self.setattr_argument("laser_frequency", NumberValue(default=RESONANCE_HZ))
        self.setattr_argument("laser_phase", NumberValue(default=0))

        self.detection = DetectionModule()
        self.detection.build(self)
        self.laser_729 = Laser729Module()
        self.laser_729.build(self)
        self.laser_397_cool = Laser397CoolModule()
        self.laser_397_cool.build(self)
        self.laser_397_pump = Laser397PumpModule()
        self.laser_397_pump.build(self)

        self.cooling = CoolingService()
        self.cooling.build(self.laser_729, self.laser_397_cool, self.laser_397_pump)

    def prepare(self):
        self.n_shots = int(self.n_shots)
        self.duration = float(self.duration)
        self.laser_frequency = float(self.laser_frequency)
        self.laser_phase = float(self.laser_phase)

        bright_result = np.zeros(self.n_shots)
        dark_result = np.zeros(self.n_shots)

        self.set_dataset("bright_fluorescence_count", bright_result)
        self.set_dataset("dark_fluorescence_count", dark_result)

    def init_device(self):
        self.laser_729.set_frequency(self.laser_frequency)
        self.laser_729.set_phase(self.laser_phase)

    def run(self):

        self.init_device()

        ## Bright experiment

        # Cool motional modes
        self.cooling.doppler_cool()
        # Return to groundstate
        self.cooling.optical_pump()

        for shot in range(self.n_shots):
            self.measure_bright(shot)

        ## Dark experiment

        # Cool motional modes
        self.cooling.doppler_cool()
        # Return to groundstate
        self.cooling.optical_pump()

        # Apply 90 degree rotation
        self.laser_729.pulse(np.pi / OMEGA_RABI) # 180 degree rotation

        for shot in range(self.n_shots):
            self.measure_dark(shot)

    @kernel
    def measure_bright(self, shot: TInt32):
        count = self.detection.count(ion_index=1, duration=self.duration)
        self.mutate_dataset("bright_fluorescence_count", shot, count) # Dataset name, index, value

    @kernel
    def measure_dark(self, shot: TInt32):
        count = self.detection.count(ion_index=1, duration=self.duration)
        self.mutate_dataset("dark_fluorescence_count", shot, count) # Dataset name, index, value
    
    def analyze(self):
        mean_bright = np.mean(self.get_dataset("bright_fluorescence_count"))
        mean_dark = np.mean(self.get_dataset("dark_fluorescence_count"))
        print(f"Bright mean:{mean_bright}, Dark mean:{mean_dark}")