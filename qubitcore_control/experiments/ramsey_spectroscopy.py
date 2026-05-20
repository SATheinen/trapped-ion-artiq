from artiq.experiment import EnvExperiment, kernel, delay, NumberValue
from artiq.language.types import TFloat, TInt32, TNone
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.detection import DetectionModule
from system.services.cooling import CoolingService
from scipy.optimize import curve_fit
import numpy as np
import matplotlib.pyplot as plt

class RamseySpectroscopy(EnvExperiment):

    def build(self):
        self.setattr_argument("T_min", NumberValue(default=0.0, unit='s'))
        self.setattr_argument("T_max", NumberValue(default=1e-3, unit='s'))
        self.setattr_argument("n_points", NumberValue(default=100))
        self.setattr_argument("n_shots", NumberValue(default=100))
        self.setattr_argument("detuning_hz", NumberValue(default=1e3))
        self.setattr_argument("measure_duration", NumberValue(default=1e-3))

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
        self.T_min = float(self.T_min)
        self.T_max = float(self.T_max)
        self.n_points = int(self.n_points)
        self.n_shots = int(self.n_shots)
        self.detuning_hz = float(self.detuning_hz)
        self.measure_duration = float(self.measure_duration)

        self.wait_times = np.linspace(self.T_min, self.T_max, self.n_points)
        self.set_dataset("wait_times", self.wait_times, broadcast=True)
        self.set_dataset("p_excited", np.zeros(self.n_points), broadcast=True)
        self.set_dataset("counts", np.zeros((self.n_points, self.n_shots)), broadcast=True)

    def run(self):
        self.cooling.doppler_cool()

        for i in range(self.n_points):
            for shot in range(self.n_shots):
                self.cooling.optical_pump()
                T = self.wait_times[i]
                counts = self.pulses_and_count(T)
                self.mutate_dataset("counts", (i, shot), counts)

    @kernel
    def pulses_and_count(self, T: TFloat) -> TInt32:
        self.laser729.pulse(2 * np.pi * 50e3 / (np.pi / 2))
        delay(T)
        self.laser729.pulse(2 * np.pi * 50e3 / (np.pi / 2))
        counts = self.detection.count(ion_index=0, duration=self.measure_duration)
        return counts

    def analyze(self):
        counts_2d = self.get_dataset("counts")
        threshold = (40.0 + 0.5)/2 * self.measure_duration * 1e3
        self.p_excited = (counts_2d < threshold).mean(axis=1)

        plt.plot(self.wait_times, self.p_excited)

        # Curve fitting
        def ramsey_model(T, A, f, phi, T2, offset):
            return A * np.cos(2*np.pi*f*T + phi) * np.exp(-T/T2) + offset
        
        p0 = [0.5, self.detuning_hz, 0, 1e-3, 0.5]
        bounds = ([0, 0, -np.pi, 1e-6, 0.0],
                  [1, 1e5, np.pi, 1.0, 1.0])
        popt, pcov = curve_fit(ramsey_model, self.wait_times, self.p_excited,
                               p0=p0, bounds=bounds, maxfev=10000)
        A, f_fit, phi_fit, T2_fit, offset_fit = popt

        self.set_dataset("calibration.T2_star", T2_fit, persist=True)
        self.set_dataset("calibration.laser_detuning_hz", f_fit, persist=True)