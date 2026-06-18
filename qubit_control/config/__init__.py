"""Central configuration: physics constants and default calibration values.

Both the simulator (sim/ion_chain.py) and the experiments/services import from
here so values stay consistent.
"""
import numpy as np

# 729nm qubit transition
RESONANCE_HZ = 200e6              # carrier frequency (Hz)
OMEGA_RABI   = 2 * np.pi * 50e3   # carrier Rabi frequency (rad/s)
ETA          = 0.1                # Lamb-Dicke parameter
T2_STAR      = 1e-3               # dephasing time (s)

# MS Gate
MS_LOOPS = 1
MS_GATE_TIME = np.pi / (ETA * OMEGA_RABI) * np.sqrt(MS_LOOPS / 2)
MS_DETUNING_OFFSET = 2 * np.pi * MS_LOOPS / MS_GATE_TIME   # δ − ω_m  (rad/s)
MS_SUM_PHASE = 0
MS_AMPLITUDE = 0.5

# Motional mode
SECULAR_FREQ  = 2 * np.pi * 1e6   # axial secular frequency (rad/s)
N_BAR_DOPPLER = 20.0              # equilibrium n̄ under Doppler cooling
N_BAR_INITIAL = 10e4              # n̄ at simulator startup, before any cooling

# Detection (PMT counts / ms)
N_BRIGHT = 40.0
N_DARK   = 0.5

# Ion chain
N_IONS = 5
INTERACTION_ZONE = 3              # = Gate Zone, single source of truth — must match routes.yaml
COOLING_ZONE = INTERACTION_ZONE   # Simplification, because dont use coolerants, but need n < 0.1 for ms gate
READOUT_ZONE = 6 
INITIAL_POSITIONS = [2, 3, 4, 5, 6]
DATA_IONS = [0, 2, 4]
ANCILLA_IONS = [1, 3]
E_CHARGE = 1.602176634e-19
M_CA = 40.078 * 1.66053906660e-27
ELECTRODE_PITCH = 100e-6 
N_ELECTRODES = 9
N_ZONES = 7
ADJACENCY = {z: [n for n in (z-1, z+1) if 0 <= n < N_ZONES] for z in range(N_ZONES)}
MERGE_HEATING = 5.0    # means (Poisson); all ≫ transport's 1.0
SPLIT_HEATING = 10.0   # separation through the double well is the hottest op
SWAP_HEATING  = 8.0    # junction-reorder cost

BEAM_ZONES = {
      "dds_729":      INTERACTION_ZONE,  # gate, rotations, thermometry probe
      "dds_397_cool": COOLING_ZONE,      # Doppler/sideband cooling (= gate)
      "dds_397_pump": READOUT_ZONE,      # optical pumping / reset (mid-circuit, away from data)
      "ttl_pmt":      READOUT_ZONE,      # detection
  }