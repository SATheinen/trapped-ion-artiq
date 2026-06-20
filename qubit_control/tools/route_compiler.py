from collections import deque
from config import (N_IONS, N_ZONES, INTERACTION_ZONE as GATE,
                    READOUT_ZONE, INITIAL_POSITIONS,
                    DATA_IONS, ANCILLA_IONS, ADJACENCY)

ROUTE_FOR_CNOT = {}
ROUTE_TO_READOUT = {}
ROUTE_TO_GATE = {}

NAMES = {}
for k, ion in enumerate(DATA_IONS):
    NAMES[ion] = f"D{k}"
for k, ion in enumerate(ANCILLA_IONS):
    NAMES[ion] = f"A{k}"

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

def cnot_positions(pos, c, t):
    """Replicate qec.cnot's position evolution exactly, raise if any step is impossible."""
    pos = list(pos)
    def free_neighbours(z):
        return [n for n in ADJACENCY[z] if occ(pos, n) < 0]
    def transport(i, to):
        if pos[i] == to: return
        if not path_clear(pos, pos[i], to):
            raise RuntimeError(f"cnot transport {NAMES[i]} {pos[i]}->{to} blocked")
        pos[i] = to
    # rot c x2
    for _ in range(2):
        o = occ(pos, GATE)
        if o >= 0 and o != c:
            fn = free_neighbours(GATE)
            if not fn: raise RuntimeError("rot c: no free neighbour to clear gate")
            transport(o, fn[0])
        transport(c, GATE)
    # rot t
    o = occ(pos, GATE)
    if o >= 0 and o != t:
        fn = free_neighbours(GATE)
        if not fn: raise RuntimeError("rot t: no free neighbour to clear gate")
        transport(o, fn[0])
    transport(t, GATE)
    # merge
    pos[c] = GATE; pos[t] = GATE
    # split t
    fn = [z for z in ADJACENCY[GATE] if occ(pos, z) < 0]
    if not fn: raise RuntimeError("split: no free neighbour")
    pos[t] = fn[0]
    # rot c
    o = occ(pos, GATE)
    if o >= 0 and o != c:
        fn2 = free_neighbours(GATE)
        if not fn2: raise RuntimeError("final rot c: no free neighbour")
        transport(o, fn2[0])
    transport(c, GATE)
    return tuple(pos)

def show(pos):
    row = ["__"] * N_ZONES
    for i, p in enumerate(pos):
        row[p] = NAMES[i]
    return "[" + " ".join(row) + "]"

# ---- run the full round ----
pos = tuple(INITIAL_POSITIONS)  # D0,A0,D1,A1,D2
CNOTS = [(0,1),(2,1),(2,3),(4,3)]
print("initial      ", show(pos))
total_swaps = total_transports = 0
for k, (c, t) in enumerate(CNOTS, 1):
    goal = (lambda c,t: (lambda s: s[c]==GATE and s[t]==GATE-1 and occ(s,GATE+1) < 0))(c,t)
    ops, pos2 = route(pos, goal)
    if ops is None:
        print(f"CNOT{k} ({NAMES[c]}->? ctrl/tgt): ROUTING IMPOSSIBLE")
        break
    ns = sum(1 for o in ops if o[0]=="swap")
    nt = sum(1 for o in ops if o[0]=="transport")
    replay = [(o[0], o[1], o[3]) if o[0]=="transport" else o for o in ops]
    ROUTE_FOR_CNOT[(c, t)] = replay
    total_swaps += ns
    total_transports += nt
    print(f"\nCNOT{k}: gate ctrl={NAMES[c]} tgt={NAMES[t]}   route: {ns} swaps, {nt} transports")
    for o in ops:
        if o[0]=="transport": print(f"   transport {NAMES[o[1]]}: {o[2]}->{o[3]}")
        else: print(f"   swap {NAMES[o[1]]}<->{NAMES[o[2]]}")
    print("   after route ", show(pos2))
    pos3 = cnot_positions(pos2, c, t)
    print(f"   cnot OK      {show(pos3)}  (preserved: {pos3==pos2})")
    assert pos3 == pos2
    pos = pos3
print(f"\nTOTAL routing cost: {total_swaps} swaps, {total_transports} transports")

print(f"\n=== Phase B: route each ancilla to READOUT_ZONE={READOUT_ZONE} (no-passing) ===")
# continue from the post-CNOT4 chain
for anc in ANCILLA_IONS:  # A0=ion1, A1=ion3
    goal = (lambda a: (lambda s: s[a]==READOUT_ZONE))(anc)
    ops, pos2 = route(pos, goal)
    if ops is None:
        print(f"  {NAMES[anc]} -> readout: IMPOSSIBLE"); continue
    ns = sum(1 for o in ops if o[0]=="swap"); nt = sum(1 for o in ops if o[0]=="transport")
    replay = [(o[0], o[1], o[3]) if o[0]=="transport" else o for o in ops]
    ROUTE_TO_READOUT[anc] = replay
    print(f"\n  {NAMES[anc]} -> readout: {ns} swaps, {nt} transports")
    for o in ops:
        if o[0]=="transport": print(f"     transport {NAMES[o[1]]}: {o[2]}->{o[3]}")
        else: print(f"     swap {NAMES[o[1]]}<->{NAMES[o[2]]}")
    print("     ", show(pos2))
    pos = pos2  # measure+reset doesn't move ions

print("\n=== 4d/5 correction: route each flagged DATA ion to the gate (+free neighbour to clear) ===")
# worst case: start from the post-extraction chain
for data in DATA_IONS:  # D0, D1, D2
    goal = (lambda d: (lambda s: s[d]==GATE and any(occ(s,n)<0 for n in ADJACENCY[GATE])))(data)
    ops, pos2 = route(pos, goal)
    if ops is None:
        print(f"  correct {NAMES[data]}: IMPOSSIBLE"); continue
    ns = sum(1 for o in ops if o[0]=="swap"); nt = sum(1 for o in ops if o[0]=="transport")
    replay = [(o[0], o[1], o[3]) if o[0]=="transport" else o for o in ops]
    ROUTE_TO_GATE[data] = replay
    print(f"  correct {NAMES[data]}: {ns} swaps, {nt} transports -> {show(pos2)}")

print(f"Route for cnot: {ROUTE_FOR_CNOT}")
print(f"Route to gate: {ROUTE_TO_GATE}")
print(f"Route to readout: {ROUTE_TO_READOUT}")