from artiq.experiment import EnvExperiment
import numpy as np, qutip as qt
from sim.ion_chain import ion
from config import N_IONS, INTERACTION_ZONE, MS_GATE_TIME

zero, one = qt.basis(2, 0), qt.basis(2, 1)

def cnot(c, t):                                   # decomposition under test (signs TBD by the test)
    ion.apply_rotation(c, -np.pi/2, np.pi/2)      # Ry_c(−π/2)
    ion.apply_rotation(t,  -np.pi/2, 0.0)         # Rx_t(−π/2)
    ion.apply_rotation(c, -np.pi/2, 0.0)          # Rx_c(−π/2)
    ion.apply_ms_gate(MS_GATE_TIME)               # XX(π/4)
    ion.apply_rotation(c,  np.pi/2, np.pi/2)      # Ry_c(+π/2)

class CNOTCheck(EnvExperiment):
    def build(self):
        self.setattr_device("core")               # no other devices: pure sim-state check

    def run(self):
        def prep(kc, kt):
            kets = [zero] * N_IONS
            kets[0], kets[1] = kc, kt                                  # control=ion0, target=ion1
            ion.psi = qt.tensor(kets)
            ion.positions = np.array([INTERACTION_ZONE, INTERACTION_ZONE, 0, 4, 5])  # only 0,1 at gate

        def run_cnot():
            cnot(0, 1)                                                 # the LOCAL cnot, not ion.cnot
            return ion.psi.full().flatten()[[0, 8, 16, 24]]           # c-t amplitudes (others |0>)

        # (1) populations — necessary, not sufficient
        for bc in (0, 1):
            for bt in (0, 1):
                prep(qt.basis(2, bc), qt.basis(2, bt)); v = run_cnot()
                print(bc, bt, "->", np.round(np.abs(v)**2, 2))         # target flips iff control=1

        # (2) Bell phase
        prep((zero + one).unit(), zero); v = run_cnot()
        phi_p = np.array([1, 0, 0, 1]) / np.sqrt(2)
        phi_m = np.array([1, 0, 0, -1]) / np.sqrt(2)
        print("|<Φ+|out>|² =", round(abs(phi_p.conj() @ v)**2, 3),
            "  |<Φ−|out>|² =", round(abs(phi_m.conj() @ v)**2, 3))   # want 1.0 and 0.0

        # (3) full process overlap, global-phase-invariant
        cols = []
        for bc in (0, 1):
            for bt in (0, 1):
                prep(qt.basis(2, bc), qt.basis(2, bt)); cols.append(run_cnot())
        U = np.column_stack(cols)
        U_ideal = np.array([[1,0,0,0],[0,1,0,0],[0,0,0,1],[0,0,1,0]], dtype=complex)
        overlap = abs(np.trace(U_ideal.conj().T @ U)) / 4
        print("process overlap (want ≈1.0):", round(overlap, 4))
        if overlap < 0.999:
            print("U_impl =\n", np.round(U, 3))