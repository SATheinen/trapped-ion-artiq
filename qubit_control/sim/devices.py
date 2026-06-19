import numpy as np
from sim.ion_chain import ion
from sim.core import time_manager
from config import COOLING_ZONE
from artiq.language.types import TFloat, TInt32, TNone

class SimPMT:

    def __init__(self, device_mgr):
        self.device_mgr = device_mgr # Ignore
        self.ion = ion

    def count(self, ion_index, duration: TFloat) -> TInt32:
        return self.ion.sample_fluorescence(ion_index, duration)
    
class SimDDS729():

    def __init__(self, device_mgr):
        self.device_mgr = device_mgr # Ignore
        self.ion = ion
        self.time_manager = time_manager
        self._mode = "single"

        self.frequency = None
        self.phase = 0.0

        self._t_on = None
        self.sw = SimDDS729.Switch(self)

    def set_frequency(self, frequency: TFloat) -> TNone:
        self._mode = "single"
        self.frequency = frequency
        self.ion.laser_freq = frequency

    def set_phase(self, phi: TFloat) -> TNone:
        self.phase = phi

    def set_dual_tone(self, f_red, f_blue, amplitude, sum_phase):
        self._mode = "dual"
        self._dual_phase = sum_phase
        # f_red, f_blue and amplitude are only necessary for real Hardware

    def _begin_pulse(self):
        # Turn laser on
        self._t_on = self.time_manager.current_time()
        self.time_manager._laser_on = True

    def _end_pulse(self):
        # Check if laser was turned on before
        if self._t_on == None:
            return
        
        # Get pulse duration
        duration = self.time_manager.current_time() - self._t_on
        # Calculate detuning
        detuning_rad = 2 * np.pi * (self.frequency - self.ion.RESONANCE_HZ)

        if self._mode == "single":
            self.ion.apply_pulse(duration, detuning_rad, self.phase)
        if self._mode == "dual":
            self.ion.apply_ms_gate(duration)

        # Turn laser off
        self._t_on = None
        self.time_manager._laser_on = False

    class Switch():
        def __init__(self, dds):
            self.state = "off"
            self._dds = dds

        def on(self):
            self.state = "on"
            self._dds._begin_pulse()

        def off(self):
            self.state = "off"
            self._dds._end_pulse()

class SimDDS397Cool():

    def __init__(self, device_mgr):
        self.device_mgr = device_mgr # Ignore
        self.ion = ion

        self.frequency = None
        self.phase = 0.0

        self._t_on = None
        self.sw = SimDDS729.Switch(self)

    def set_frequency(self, frequency: TFloat) -> TNone:
        self.frequency = frequency

    def set_phase(self, phi: TFloat) -> TNone:
        self.phase = phi

    def _begin_pulse(self):
        # Turn laser on
        self._t_on = time_manager.current_time()

    def _end_pulse(self):
        # Check if laser was turned on before
        if self._t_on == None:
            return

        # Get pulse duration
        duration = time_manager.current_time() - self._t_on

        # 397 laser depopulates the motional modes
        for i in np.where(self.ion.positions == COOLING_ZONE)[0]:
            self.ion.n_bar[i] = self.ion.n_eq + (self.ion.n_bar[i] - self.ion.n_eq) * np.exp(-2000 * duration)

        # Turn laser off
        self._t_on = None

class SimDDS397Pump():

    def __init__(self, device_mgr):
        self.device_mgr = device_mgr # Ignore
        self.ion = ion

        self.frequency = None
        self.phase = 0.0

        self._t_on = None
        self.sw = SimDDS729.Switch(self)

    def set_frequency(self, frequency: TFloat) -> TNone:
        self.frequency = frequency

    def set_phase(self, phi: TFloat) -> TNone:
        self.phase = phi

    def _begin_pulse(self):
        # Turn laser on
        self._t_on = time_manager.current_time()

    def set_target_zone(self, zone):
        self.target_zone = zone

    def _end_pulse(self):
        if self._t_on is None:
            return
        hit = np.where(self.ion.positions == self.target_zone)[0]
        print(f"[PUMP] target={self.target_zone}  resetting={list(hit)}  positions={list(self.ion.positions)}")
        for i in hit:
            self.ion.reset_ion(int(i))
        self._t_on = None

class SimDCElectrodes:

    def __init__(self, dmgr):
        self.dmgr = dmgr
        self.ion_chain = ion
        self._voltage_history = []
        self._current_voltages = None

    def apply_route_heating(self, ion_index, from_zone, to_zone, heating_mean):
        heat_amount = int(np.random.poisson(heating_mean))
        self.ion_chain.shuttle(ion_index, from_zone, to_zone, heating=heat_amount)

    def set_voltages(self, V):
        """Mirror of Zotino.set_dac()"""
        t = time_manager.current_time()
        self._voltage_history.append((t, np.asarray(V).copy()))
        self._current_voltages = np.asarray(V).copy()

    def apply_merge(self, a, b, mean):
      self.ion_chain.merge(a, b, int(np.random.poisson(mean)))

    def apply_split(self, ion, to_zone, mean):
        self.ion_chain.split(ion, to_zone, int(np.random.poisson(mean)))

    def apply_swap(self, x, y, mean):
        self.ion_chain.swap(x, y, int(np.random.poisson(mean)))