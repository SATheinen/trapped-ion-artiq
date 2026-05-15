from artiq.experiment import EnvExperiment, kernel, NumberValue
from artiq.language.types import TFloat, TInt32
from system.modules.laser_729 import Laser729Module
from system.modules.detection import DetectionModule
import numpy as np
import matplotlib.pyplot as plt

class RabiFlop(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_argument("measure_duration", NumberValue(default=1e-3))
        self.setattr_argument("pulse_min_duration", NumberValue(default=0e-6))
        self.setattr_argument("pulse_max_duration", NumberValue(default=50e-6))
        self.setattr_argument("n_shots", NumberValue(default=100))
        self.setattr_argument("pulse_n_durations", NumberValue(default=100))
        self.setattr_argument("laser_frequency", NumberValue(default=200e6))

        self.laser729 = Laser729Module()
        self.laser729.build(self)
        self.detection = DetectionModule()
        self.detection.build(self)

    def prepare(self):
        self.measure_duration = float(self.measure_duration)
        self.pulse_min_duration = float(self.pulse_min_duration)
        self.pulse_max_duration = float(self.pulse_max_duration)
        self.n_shots = int(self.n_shots)
        self.pulse_n_durations = int(self.pulse_n_durations)
        self.laser_frequency = float(self.laser_frequency)

        self.pulse_durations = np.linspace(self.pulse_min_duration, self.pulse_max_duration, self.pulse_n_durations)
        shot_results = np.zeros(self.n_shots)
        duration_results = np.zeros(self.pulse_n_durations)

        self.set_dataset("shot_photon_count", shot_results)
        self.set_dataset("duration_photon_count", duration_results)

    ##################################
    # sim-only
    def reset_ion_state(self):
        from sim.ion_chain import ion
        ion.set_state(state=0)

    def sim_apply_pulse(self, duration):
        self.laser729._dds_729.apply_pulse(duration)
    ##################################

    def run(self):

        # Set Laser frequency
        self.init_devices()

        for i, pulse_duration in enumerate(self.pulse_durations):
            for shot in range(self.n_shots):
                
                # sim-only
                self.reset_ion_state()
                self.sim_apply_pulse(pulse_duration)

                # Real Hardware
                self.pulse(pulse_duration) # Send laser pulse
                self.measure(shot)

            average_photons = np.mean(self.get_dataset("shot_photon_count")) # Average counts over shots
            self.mutate_dataset("duration_photon_count", i, average_photons) # write to dataset

    @kernel
    def init_devices(self):
        self.laser729.set_frequency(self.laser_frequency)

    @kernel
    def pulse(self, duration: TFloat):
        self.laser729.pulse(duration)            

    @kernel
    def measure(self, shot: TInt32):
        count = self.detection.count(self.measure_duration)
        self.mutate_dataset("shot_photon_count", shot, count)

    def analyze(self):
        mean_counts = self.get_dataset("duration_photon_count")
        plt.plot(self.pulse_durations, mean_counts)
        plt.tight_layout()
        plt.show()