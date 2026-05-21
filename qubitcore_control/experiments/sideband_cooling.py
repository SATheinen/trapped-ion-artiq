from artiq.experiment import EnvExperiment, kernel, delay, NumberValue
from artiq.language.types import TFloat, TInt32, TNone
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.detection import DetectionModule
from system.services.cooling import CoolingService
import numpy as np
from scipy.signal import find_peaks

class SidebandCooling(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_argument("RESONANCE_HZ", NumberValue(default=200e6, unit='Hz'))
        self.setattr_argument("secular_freq", NumberValue(default=2*np.pi*1e6, unit='Hz'))
        self.setattr_argument("n_points", NumberValue(default=1000))
        self.setattr_argument("max_freq", NumberValue(default=3e6, unit='Hz'))
        self.setattr_argument("min_freq", NumberValue(default=-3e6, unit='Hz'))
        self.setattr_argument("measure_duration", NumberValue(default=1e-3, unit='s'))
        self.setattr_argument("probe_duration", NumberValue(default=1e-3, unit='s'))

        self.detection = DetectionModule()
        self.detection.build(self)
        self.laser_729 = Laser729Module()
        self.laser_729.build(self)
        self.laser_397_cool = Laser397CoolModule()
        self.laser_397_cool.build(self)
        self.laser_397_pump = Laser397PumpModule()
        self.laser_397_pump.build(self)

        self.cooling = CoolingService()
        self.cooling.build(self.laser_397_cool, self.laser_397_pump, self.detection)

    def prepare(self):
        self.RESONANCE_HZ = float(self.RESONANCE_HZ)
        self.secular_freq = float(self.secular_freq)
        self.n_points = int(self.n_points)
        self.max_freq = float(self.max_freq)
        self.min_freq = float(self.min_freq)
        self.measure_duration = float(self.measure_duration)

        self.freq_scan = np.linspace(self.min_freq, self.max_freq, self.n_points)
        self.set_dataset("freq", self.freq_scan, broadcast=True)
        self.set_dataset("counts", np.zeros(self.n_points), broadcast=True)
    
    def init_device(self):
        self.laser_729.set_frequency(self.RESONANCE_HZ)
        self.laser_729.set_phase(0)

    def run(self):

        self.init_device()
        self.cooling.doppler_cool()

        for i in range(self.n_points):
            self.run_point(i)

    @kernel
    def run_point(self, index):
        self.cooling.optical_pump()
        self.cooling.doppler_cool()

        self.laser_729.set_frequency(self.RESONANCE_HZ + self.freq_scan[index])
        self.laser_729.pulse(duration=self.probe_duration)
        counts = self.detection.count(ion_index=0, duration=self.measure_duration)

        self.mutate_dataset("counts", index, counts)

    def analyze(self):
        freq = self.get_dataset("freq")
        counts = self.get_dataset("counts")

        # find peaks near -omega_m, 0, +omega_m
        omega_m = self.secular_freq
        def find_peak(f0, window=200e3):
            mask = (freq > f0-window) & (freq < f0+window)
            return counts[mask].min()
        
        A_rsb = find_peak(-omega_m/(2*np.pi))
        A_bsb = find_peak(+omega_m/(2*np.pi))
        A_car = find_peak(0)

        # thermometry: A_rsb / A_bsb = n / (n+1)
        ratio = A_rsb / A_bsb
        n_bar = ratio / (1 - ratio)
        print(f"Carrier: {A_car:.3f}, RSB: {A_rsb:.3f}, BSB: {A_bsb:.3f}")
        print(f"Estimated n_bar = {n_bar:.2f}")