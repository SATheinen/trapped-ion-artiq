from artiq.experiment import EnvExperiment, kernel, delay, NumberValue
from artiq.language.types import TFloat, TInt32, TNone
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.detection import DetectionModule
from system.services.cooling import CoolingService
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

class SidebandCooling(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_argument("RESONANCE_HZ", NumberValue(default=200e6, unit='Hz'))
        self.setattr_argument("secular_freq", NumberValue(default=2*np.pi*1e6))
        self.setattr_argument("n_points", NumberValue(default=1000))
        self.setattr_argument("n_shots", NumberValue(default=100))
        self.setattr_argument("max_freq", NumberValue(default=3e6, unit='Hz'))
        self.setattr_argument("min_freq", NumberValue(default=-3e6, unit='Hz'))
        self.setattr_argument("measure_duration", NumberValue(default=1e-3, unit='s'))
        self.setattr_argument("probe_duration", NumberValue(default=5e-6, unit='s'))

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
        self.n_shots = int(self.n_shots)
        self.max_freq = float(self.max_freq)
        self.min_freq = float(self.min_freq)
        self.measure_duration = float(self.measure_duration)

        self.freq_scan = np.linspace(self.min_freq, self.max_freq, self.n_points)
        self.set_dataset("freq", self.freq_scan, broadcast=True)
        self.set_dataset("p_excited", np.zeros(self.n_shots), broadcast=True)
        self._counts = np.zeros((self.n_points, self.n_shots))
    
    def init_device(self):
        self.laser_729.set_frequency(self.RESONANCE_HZ)
        self.laser_729.set_phase(0)

    def run(self):

        self.init_device()
        self.cooling.doppler_cool()

        for i in range(self.n_points):
            for shot in range(self.n_shots):
                self._counts[i, shot] = self.run_point(i)
                
    @kernel
    def run_point(self, index):
        self.cooling.optical_pump()
        self.cooling.doppler_cool()

        self.laser_729.set_frequency(self.RESONANCE_HZ + self.freq_scan[index])
        self.laser_729.pulse(duration=self.probe_duration)
        counts = self.detection.count(ion_index=0, duration=self.measure_duration)

        return counts

    def analyze(self):
        freq = self.get_dataset("freq")
        counts = self.get_dataset("counts")

        # threshold discrimination
        threshold = (40.0 + 0.5) / 2 * self.measure_duration * 1e3
        p_excited = (self._counts < threshold).mean(axis=1)

        # find peaks near -omega_m, 0, +omega_m
        omega_m = self.secular_freq
        def find_peak(f0, window=200e3):
            mask = (freq > f0-window) & (freq < f0+window)
            return p_excited[mask].max()
        
        A_rsb = find_peak(-omega_m/(2*np.pi))
        A_bsb = find_peak(+omega_m/(2*np.pi))
        A_car = find_peak(0)

        # thermometry: A_rsb / A_bsb = n / (n+1)
        ratio = A_rsb / A_bsb
        n_bar = ratio / (1 - ratio)
        print(f"Carrier: {A_car:.3f}, RSB: {A_rsb:.3f}, BSB: {A_bsb:.3f}")
        print(f"Estimated n_bar = {n_bar:.2f}")

        plt.rcParams.update({
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelsize": 12,
            "xtick.direction": "in",
            "ytick.direction": "in",
        })

        DATA_COLOR = "#2b6cb0"
        REF_COLOR  = "#c53030"
        PEAK_COLOR = "#2f855a"

        omega_m_hz = omega_m / (2 * np.pi)

        fig, ax = plt.subplots(figsize=(8.5, 4.8))

        for f0, label in [(-omega_m_hz, r"$-\omega_m$"),
                          (0.0,          r"$\omega_0$"),
                          (+omega_m_hz, r"$+\omega_m$")]:
            ax.axvline(f0 / 1e6, color=REF_COLOR, lw=0.8, ls="--", alpha=0.5)
            ax.text(f0 / 1e6, 1.02, label, color=REF_COLOR,
                    ha="center", va="bottom", fontsize=9,
                    transform=ax.get_xaxis_transform())

        ax.plot(
            freq / 1e6, counts,
            marker="o", ms=2.8, mfc=DATA_COLOR, mec="none", lw=0,
            alpha=0.65, label="counts",
        )

        for f0, A in [(-omega_m_hz, A_rsb), (0.0, A_car), (+omega_m_hz, A_bsb)]:
            ax.plot(f0 / 1e6, A, marker="v",
                    color=PEAK_COLOR, ms=9, mec="white", mew=0.8)

        ax.set_xlabel(r"Detuning $\delta/2\pi$  (MHz)")
        ax.set_ylabel("Photon counts")
        ax.set_xlim(freq.min() / 1e6, freq.max() / 1e6)
        ax.grid(True, alpha=0.25, linestyle=":")

        info = (
            f"$A_\\mathrm{{car}} = {A_car:.1f}$\n"
            f"$A_\\mathrm{{RSB}} = {A_rsb:.1f}$\n"
            f"$A_\\mathrm{{BSB}} = {A_bsb:.1f}$\n"
            f"$\\bar n = {n_bar:.2f}$"
        )
        ax.text(
            0.985, 0.96, info, transform=ax.transAxes,
            ha="right", va="top", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor="white", edgecolor="#bbb", alpha=0.92),
        )
        ax.legend(loc="lower right", framealpha=0.9, fontsize=9)
        ax.set_title("Sideband spectroscopy", loc="left", fontsize=13, pad=10)

        fig.tight_layout()
        fig.savefig("sideband_cooling.pdf", bbox_inches="tight")
        plt.close(fig)