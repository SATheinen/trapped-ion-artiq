from artiq.language.core import set_time_manager, _DummyTimeManager

class SimCore:
    def __init__(self, dmgr, **kwargs):
        set_time_manager(_DummyTimeManager())
    
    def reset(self):
        pass
    
    def seconds_to_mu(self, t):
        return int(t * 1e9)
    
    def mu_to_seconds(self, mu):
        return mu * 1e-9
    
    def run(self, func, args, kwargs):
        return func(*args, **kwargs)