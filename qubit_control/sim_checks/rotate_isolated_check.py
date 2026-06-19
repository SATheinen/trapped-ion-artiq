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
from config import N_IONS, INTERACTION_ZONE
import numpy as np

class RotateIsolatedCheck(EnvExperiment):
      
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
        theta, phi = -np.pi/2, np.pi/2 # Ry(−π/2), a rotation the CNOT uses

        ion.psi = qt.tensor([qt.basis(2,0)]*N_IONS) 
        ion.apply_rotation(0, theta, phi)
        ref = ion.psi.ptrace(0)

        # ACTUAL: through the laser + transport path, with the gate occupied (exercises clearing)
        ion.psi = qt.tensor([qt.basis(2,0)]*N_IONS)
        ion.positions = np.array([2, 3, 0, 5, 6])   # ion0@2 (to rotate), ion1@3 (gate)
        self.trap_dc._positions = np.array([2, 3, 0, 5, 6])
        self.qec._rotate_isolated(0, theta, phi)
        act = ion.psi.ptrace(0)

        gate_ions = list(np.where(ion.positions == INTERACTION_ZONE)[0])
        print("state match (want <1e-9):", round((act - ref).norm(), 12))
        print("gate occupants (want [0]):", gate_ions)
        assert (act - ref).norm() < 1e-9 and gate_ions == [0]
        print("OK _rotate_isolated")