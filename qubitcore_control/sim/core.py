from artiq.language.core import set_time_manager
from sim.ion_chain import ion

class _SimTimeManager:
    def __init__(self):
        self._t = 0.0
        self._laser_on = False   # set by SimDDS729 begin/end pulse

    def take_time(self, duration):
        self._advance(duration)

    def take_time_mu(self, duration_mu):
        self._advance(duration_mu * 1e-9)        # MU → s

    def _advance(self, dt):
        self._t += dt
        if not self._laser_on:                   # avoid double-counting δ
            for i in range(ion.N_IONS):
                detuning_rad = ion.current_detuning_rad()
                ion.free_evolve(i, detuning_rad, dt)

    def get_time_mu(self):   return int(self._t * 1e9)
    def set_time_mu(self, t): self._t = t * 1e-9
    def enter_parallel(self):   pass
    def enter_sequential(self): pass
    def exit(self):             pass

    # Public extension — invisible to ARTIQ:
    def current_time(self):  return self._t
    def set_laser_on(self, on):  self._laser_on = on

time_manager = _SimTimeManager()
set_time_manager(time_manager)

class SimCore:
    def __init__(self, dmgr, **kwargs):
        pass

    def reset(self):
        pass

    def seconds_to_mu(self, t):
        return int(t * 1e9)

    def mu_to_seconds(self, mu):
        return mu * 1e-9

    def run(self, func, args, kwargs):
        return func.artiq_embedded.function(*args, **kwargs)