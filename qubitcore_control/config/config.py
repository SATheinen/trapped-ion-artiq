"""Central configuration: physics constants and default calibration values.

Both the simulator (sim/ion_chain.py) and the experiments/services import from
here so values stay consistent. NumberValue defaults reference these constants
so the GUI still exposes them as per-run overrides.

When calibration experiments produce fitted values, write them to persistent
ARTIQ datasets (e.g. `calibration.omega_rabi`) and prefer those at runtime
over the defaults defined here.
"""
import numpy as np

# 729nm qubit transition
RESONANCE_HZ = 200e6              # carrier frequency (Hz)
OMEGA_RABI   = 2 * np.pi * 50e3   # carrier Rabi frequency (rad/s)
ETA          = 0.1                # Lamb-Dicke parameter
T2_STAR      = 1e-3               # dephasing time (s)

# Motional mode
SECULAR_FREQ  = 2 * np.pi * 1e6   # axial secular frequency (rad/s)
N_BAR_DOPPLER = 20.0              # equilibrium n̄ under Doppler cooling
N_BAR_INITIAL = 10e4              # n̄ at simulator startup, before any cooling

# Detection (PMT counts / ms)
N_BRIGHT = 40.0
N_DARK   = 0.5

# Ion chain
N_IONS = 3
