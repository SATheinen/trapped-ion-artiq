from collections import deque
from config import (N_IONS, N_ZONES, INTERACTION_ZONE as GATE,
                    READOUT_ZONE, INITIAL_POSITIONS,
                    DATA_IONS, ANCILLA_IONS, ADJACENCY)

NAMES = {}
for i, zone in enumerate(DATA_IONS):
    NAMES[f"D{i}"] = zone
for i, zone in enumerate(ANCILLA_IONS):
    NAMES[f"A{i}"] = zone