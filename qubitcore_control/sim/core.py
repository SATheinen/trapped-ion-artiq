from artiq.language.core import set_time_manager

class NoOpTimeManager:
    _time = 0

    def take_time(self, duration):
        self._time += duration

    def take_time_mu(self, duration):
        self._time += duration

    def get_time_mu(self):
        return self._time

    def set_time_mu(self, t):
        self._time = t

    def enter_parallel(self):
        pass

    def enter_sequential(self):
        pass

    def exit(self):
        pass

set_time_manager(NoOpTimeManager())

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