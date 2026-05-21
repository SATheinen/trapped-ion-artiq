from artiq.experiment import EnvExperiment, kernel, NumberValue
from artiq.language.types import TFloat, TInt32
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.detection import DetectionModule
from system.services.cooling import CoolingService
import numpy as np

class RabiFlop(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_argument("measure_duration", NumberValue(default=1e-3))
        self.setattr_argument("pulse_min_duration", NumberValue(default=0e-6))
        self.setattr_argument("pulse_max_duration", NumberValue(default=50e-6))
        self.setattr_argument("n_shots", NumberValue(default=100))
        self.setattr_argument("pulse_n_durations", NumberValue(default=100))
        self.setattr_argument("laser_frequency", NumberValue(default=200e6))
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
        self.cooling.build(self.laser_397_cool, self.laser_397_pump, self.detection)

    def prepare(self):
        self.measure_duration = float(self.measure_duration)
        self.pulse_min_duration = float(self.pulse_min_duration)
        self.pulse_max_duration = float(self.pulse_max_duration)
        self.n_shots = int(self.n_shots)
        self.pulse_n_durations = int(self.pulse_n_durations)
        self.laser_frequency = float(self.laser_frequency)
        self.laser_phase = float(self.laser_phase)

        self.pulse_durations = np.linspace(self.pulse_min_duration, self.pulse_max_duration, self.pulse_n_durations)
        shot_results = np.zeros(self.n_shots)
        duration_results = np.zeros(self.pulse_n_durations)

        self.set_dataset("shot_photon_count", shot_results)
        self.set_dataset("duration_photon_count", duration_results)

    def run(self):
        
        # Set Laser frequency and phase
        self.init_device()

        # Motional mode cooling
        self.cooling.doppler_cool()

        for i, pulse_duration in enumerate(self.pulse_durations):
            for shot in range(self.n_shots):
                
                # Reset state
                self.cooling.optical_pump()                

                # Real Hardware
                self.pulse(pulse_duration) # Send laser pulse
                self.measure(shot)

            average_photons = np.mean(self.get_dataset("shot_photon_count")) # Average counts over shots
            self.mutate_dataset("duration_photon_count", i, average_photons) # write to dataset

    def init_device(self):
        self.laser_729.set_frequency(self.laser_frequency)
        self.laser_729.set_phase(self.laser_phase)

    @kernel
    def pulse(self, duration: TFloat):
        self.laser_729.pulse(duration)            

    @kernel
    def measure(self, shot: TInt32):
        count = self.detection.count(ion_index=0, duration=self.measure_duration)
        self.mutate_dataset("shot_photon_count", shot, count)

    def analyze(self):
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
        from scipy.optimize import curve_fit

        t = self.pulse_durations
        data = self.get_dataset("duration_photon_count")

        def rabi_model(t, omega, phi, A, offset):
            return A * np.cos(omega * t + phi) + offset

        p0 = [2 * np.pi * 50e3, 0, 20, 20]
        bounds = ([0, -np.pi, 0, 0],
                  [2 * np.pi * 200e3, np.pi, 40, 40])
        popt, pcov = curve_fit(rabi_model, t, data, p0=p0,
                            bounds=bounds, maxfev=10000)

        omega_fit, phi_fit, A_fit, offset_fit = popt
        t_pi = (np.pi - phi_fit) / omega_fit
        f_rabi = omega_fit / (2 * np.pi)
        t_fine = np.linspace(t.min(), t.max(), 2000)

        fig, ax = plt.subplots()
        ax.scatter(t * 1e6, data, s=10, label="data")
        ax.plot(t_fine * 1e6, rabi_model(t_fine, *popt), label="fit")
        ax.set_xlabel("Pulse duration (µs)")
        ax.set_ylabel("Photon count")
        ax.legend()
        plt.savefig("rabi_flop.pdf")
        print(f"π-time: {t_pi*1e6:.2f} µs  |  Rabi freq: {f_rabi/1e3:.2f} kHz")