from artiq.experiment import EnvExperiment, kernel, delay, NumberValue, us
from artiq.language.types import TInt32, TFloat, TNone
from system.modules.laser_729 import Laser729Module
from system.modules.laser_397 import Laser397CoolModule, Laser397PumpModule
from system.modules.trap_dc import TrapDCModule
from system.modules.detection import DetectionModule
from system.services.cooling import CoolingService
from system.services.ion_shuttling import ShuttlingService
from system.services.readout import ReadoutService
from system.services.qec import QECService
from config import N_IONS, INTERACTION_ZONE, INITIAL_POSITIONS, READOUT_ZONE, DATA_IONS
import numpy as np

class ExtractSyndromeCheck(EnvExperiment):
      
    def build(self):
        self.setattr_device("core")
        self.laser_729 = Laser729Module()    
        self.laser_729.build(self)
        self.laser_397_cool = Laser397CoolModule()  
        self.laser_397_cool.build(self)
        self.laser_397_pump = Laser397PumpModule()   
        self.laser_397_pump.build(self)
        self.detection = DetectionModule()      
        self.detection.build(self)
        self.trap_dc = TrapDCModule()        
        self.trap_dc.build(self)

        self.cooling = CoolingService()
        self.cooling.build(self.laser_729, self.laser_397_cool,
                            self.laser_397_pump)
        
        self.shuttling = ShuttlingService()
        self.shuttling.build(self.trap_dc, self.cooling)

        self.readout = ReadoutService()
        self.readout.build(self.detection, self.laser_397_pump, self.trap_dc)

        self.qec = QECService()
        self.qec.build(self.shuttling, self.cooling, self.laser_729, self.readout, self.trap_dc)

    def run(self):
        from sim.ion_chain import ion
        import qutip as qt
        np.random.seed(0)
        ion.dephasing_on = False
        zero = qt.basis(2,0); p1 = lambda i: float(ion.psi.ptrace(i)[1,1].real)
        INIT = list(INITIAL_POSITIONS); POST = [0,5,4,6,1]

        def reset_to(layout):
            ion.psi = qt.tensor([zero]*5)
            ion.positions = np.array(layout); self.trap_dc._positions = np.array(layout)

        for d in DATA_IONS:                                   # (a) inject: restores INIT, flips only d
            reset_to(INIT)
            self.qec.inject_x(d)
            assert list(self.trap_dc._positions) == INIT
            assert round(p1(d)) == 1 and all(round(p1(j))==0 for j in range(5) if j != d)
        print("OK inject_x")

        for (s0,s1), flag in [((0,0),None),((1,0),0),((1,1),2),((0,1),4)]:   # (b) correct: round-trip
            reset_to(POST); assert self.qec.correct(s0,s1) == flag
            assert list(self.trap_dc._positions) == POST
        print("OK correct round-trip")

        reset_to(POST) # (c) logical routes reach readout
        for d in DATA_IONS:
            self.shuttling.route_logical(d)
            assert self.trap_dc.get_zone(d) == READOUT_ZONE
        print("OK logical routes")