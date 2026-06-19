from collections import deque
from config import (N_IONS, N_ZONES, INTERACTION_ZONE as GATE,
                    READOUT_ZONE, INITIAL_POSITIONS,
                    DATA_IONS, ANCILLA_IONS, ADJACENCY)

NAMES = {}
for i, zone in enumerate(DATA_IONS):
    NAMES[f"D{i}"] = zone
for i, zone in enumerate(ANCILLA_IONS):
    NAMES[f"A{i}"] = zone

def occ(pos, z):
    for i, p in enumerate(pos):
        if p == z:
            return i
    return -1

def path_clear(pos, frm, to):
    step = 1 if to > frm else -1
    for z in range(frm+step, to+step, step):
        if occ(pos, z) >= 0:
            return False
    return True

def legal_moves(pos):
    """Yield (op_label, new_pos). transport = move ion to any reachable free zone (no-passing).
       swap = exchange two zone-adjacent ions."""
    moves = []
    for i in range(N_IONS):
        for to in range(N_ZONES):
            if to == pos[i]:
                continue
            if occ(pos, to) >= 0:
                continue
            if path_clear(pos, pos[i], to):
                np_ = list(pos); np_[i] = to
                moves.append((("transport", i, pos[i], to), tuple(np_)))
    for x in range(N_IONS):
        for y in range(x+1, N_IONS):
            if pos[y] in ADJACENCY[pos[x]]:
                np_ = list(pos); np_[x], np_[y] = np_[y], np_[x]
                moves.append((("swap", x, y), tuple(np_)))
    return moves

def route(pos, goal):
    """BFS shortest op sequence from pos to first state satisfying goal(state)."""
    pos = tuple(pos)
    if goal(pos):
        return [], pos
    seen = {pos}
    q = deque([(pos, [])])
    while q:
        cur, path = q.popleft()
        for op, nxt in legal_moves(cur):
            if nxt in seen:
                continue
            if goal(nxt):
                return path + [op], nxt
            seen.add(nxt)
            q.append((nxt, path + [op]))
    return None, None