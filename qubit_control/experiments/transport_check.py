from artiq.experiment import EnvExperiment, kernel, delay, NumberValue, us
from artiq.language.types import TInt32, TFloat, TNone
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.trap_dc import TrapDCModule
from system.services.cooling import CoolingService
from system.services.ion_shuttling import ShuttlingService
from config import N_IONS
import numpy as np

class TransportCheck(EnvExperiment):
      
    def build(self):
        self.setattr_device("core")
        self.laser_729 = Laser729Module()    
        self.laser_729.build(self)
        self.laser_397_cool = Laser397CoolModule()  
        self.laser_397_cool.build(self)
        self.laser_397_pump = Laser397PumpModule()   
        self.laser_397_pump.build(self)
        self.trap_dc = TrapDCModule()        
        self.trap_dc.build(self)

        self.cooling = CoolingService()
        self.cooling.build(self.laser_729, self.laser_397_cool,
                            self.laser_397_pump)
        
        self.shuttling = ShuttlingService()
        self.shuttling.build(self.trap_dc, self.cooling)
        
    def run(self):

        # Case A
        before = [self.trap_dc.get_zone(i) for i in range(N_IONS)]
        try:
            self.shuttling.transport(2, 0)        # D1 at 4 -> 0, must cross zone 3 (A0)
            print("FAIL: expected ValueError")
        except ValueError as e:
            print("OK blocked:", e)               # expect: zone 3 held by ion 1
        after = [self.trap_dc.get_zone(i) for i in range(N_IONS)]
        assert before == after                    # the atomicity check, nothing moved

        # Case B
        self.shuttling.transport(0, 0)            # D0 at 2-> 0, path 1,0 empty
        assert self.trap_dc.get_zone(0) == 0

        # Case C
        try:
            self.shuttling.transport(3, 4)        # A1 at 5-> 4, target held by D1
            print("FAIL")
        except ValueError as e:
            print("OK target blocked:", e)        # expect: zone 4 held by ion 2

        from sim.ion_chain import IonChain as ion
        GATE = self.trap_dc.interaction_zone
        synced = lambda: list(self.trap_dc._positions) == list(ion.positions)

        # MERGE — A0(ion1) is at gate 3, D0(ion0) at 2 (adjacent)
        self.shuttling.merge(0, 1)
        assert self.trap_dc.get_zone(0) == GATE and self.trap_dc.get_zone(1) == GATE
        assert synced(); print("OK merge")

        # SPLIT — D0 back out to zone 2 (now empty)
        nb = ion.n_bar.copy()
        self.shuttling.split(0, 2)
        assert self.trap_dc.get_zone(0) == 2 and self.trap_dc.get_zone(1) == GATE
        assert ion.n_bar[0] > nb[0] and ion.n_bar[1] > nb[1]   # both heated
        assert synced(); print("OK split")

        # SWAP — A1(ion3,z5) <-> D2(ion4,z6); layout is back to [2,3,4,5,6]
        self.shuttling.swap(3, 4)
        assert self.trap_dc.get_zone(3) == 6 and self.trap_dc.get_zone(4) == 5
        assert synced(); print("OK swap")

        # RAISE checks
        for call, label in [((0, 2), "merge non-adjacent"), ]:
            try: self.shuttling.merge(*call); print("FAIL", label)
            except ValueError as e: print("OK", label+":", e)
        try: self.shuttling.swap(0, 4); print("FAIL swap non-adjacent")
        except ValueError as e: print("OK swap non-adjacent:", e)