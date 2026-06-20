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
from config import N_IONS, INTERACTION_ZONE, INITIAL_POSITIONS
import numpy as np

class CNOTPortableCheck(EnvExperiment):
      
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
        ion.dephasing_on = False
        zero, one = qt.basis(2,0), qt.basis(2,1)

        def prep(kc, kt):
            kets = [zero]*5; kets[0], kets[1] = kc, kt
            ion.psi = qt.tensor(kets)
            ion.positions = np.array(INITIAL_POSITIONS)   # c=ion0@gate, t=ion1@2, room at 4
            self.trap_dc._positions = np.array(INITIAL_POSITIONS)

        def run_route():
            self.shuttling.route_for_cnot(0, 1)
            return ion.psi.full().flatten()[[0, 8, 16, 24]]

        cols = []
        for bc in (0,1):
            for bt in (0,1):
                prep(qt.basis(2,bc), qt.basis(2,bt)); v = run_route()
                print(bc, bt, "->", np.round(np.abs(v)**2, 2)); cols.append(v)
        prep((zero+one).unit(), zero); v = run_route()
        print("|<Φ+|out>|² =", round(abs((np.array([1,0,0,1])/np.sqrt(2)).conj()@v)**2, 3))
        U = np.column_stack(cols)
        U_ideal = np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype=complex)
        print("process overlap (want ≈1.0):", round(abs(np.trace(U_ideal.conj().T @ U))/4, 4))
        assert round(abs(np.trace(U_ideal.conj().T @ U))/4, 1) == 1.0