"""Scenario-independent QUBO construction for the two-intersection signal problem.

Modelling rule (see REPORT.md, Sec. 2):
  The official cost decomposes exactly into per-approach queue costs plus switch costs:
      C(x) = sum_{approach k} D_k(x_{S_k}) + w_s * sum_{i,t} [x_{i,t} xor x_{i,t-1}]
  where D_k = sum_t (q_{k,t} + w_o * max(0, q_{k,t} - storage)) depends only on the
  green bits of the intersection owning approach k (its *support* S_k, 4 bits),
  except the downstream linked approach of B, whose inflow comes from A (support 8 bits).
  * Switch term: exact quadratic, x_t + x_{t-1} - 2 x_t x_{t-1}.
  * Queue terms: each D_k is a non-quadratic (Lindley-recursion) pseudo-Boolean function.
    We replace it by its L2-optimal quadratic projection on its support, i.e. the
    Walsh-Fourier expansion truncated at order 2 (equivalently least squares over the
    support cube with uniform weights). This uses only the single-approach queue
    recursion; it never searches for, ranks, or encodes the optimal schedule.
  * Optional penalty multiplier lambda_o rescales the overflow part (ablation knob).
No auxiliary variables are needed: n = 8 qubits.
"""
import itertools
import numpy as np

from .scenario import NODES, APPROACHES, round_half_up

T = 4
N = 8


def var_index(node, t):
    return NODES.index(node) * T + t


def _green_bit(node, approach, t):
    """(index, polarity): approach is green iff x[idx] == polarity (NS=1, EW=0)."""
    return var_index(node, t), (1 if approach == "NS" else 0)


def approach_cost(sc, node, approach, x, lam_o=1.0):
    """Queue cost (delay + lam_o*w_o*overflow) of one approach under full bit vector x.
    Uses only the bits in this approach's support. Mirrors the official recursion."""
    cap, sto, wo = sc["capacity"], sc["storage"], sc["overflow_weight"]
    link = sc["link"]
    q = 0.0
    qa = 0.0  # upstream (A linked approach) queue, only needed for B linked approach
    downstream = node == link["to"] and approach == link["approach"]
    pending = 0
    cost = 0.0
    for t in range(T):
        q += sc["arrivals"][node][approach][t]
        if downstream:
            q += pending
            qa += sc["arrivals"][link["from"]][approach][t]
            ia, pa = _green_bit(link["from"], approach, t)
            if x[ia] == pa:
                s_up = min(cap, qa)
                qa -= s_up
                pending = round_half_up(link["fraction"], s_up)
            else:
                pending = 0
        i, p = _green_bit(node, approach, t)
        if x[i] == p:
            q -= min(cap, q)
        cost += q + lam_o * wo * max(0.0, q - sto)
    return cost


def support(sc, node, approach):
    s = [var_index(node, t) for t in range(T)]
    link = sc["link"]
    if node == link["to"] and approach == link["approach"]:
        s = [var_index(link["from"], t) for t in range(T)] + s
    return sorted(s)


def quadratic_projection(f, idx):
    """Order-2 truncated Walsh expansion of f on the cube {0,1}^idx, returned as
    (offset, linear dict, quadratic dict) in x (0/1) variables."""
    m = len(idx)
    pts = np.array(list(itertools.product([0, 1], repeat=m)), dtype=float)
    vals = np.array([f(p) for p in pts])
    pairs = list(itertools.combinations(range(m), 2))
    # basis in spin variables s = 1-2x; Walsh functions are orthogonal under uniform measure
    s = 1 - 2 * pts
    c0 = vals.mean()
    c1 = (s * vals[:, None]).mean(axis=0)
    c2 = {pr: (s[:, pr[0]] * s[:, pr[1]] * vals).mean() for pr in pairs}
    # convert sum c0 + c1_i s_i + c2_ij s_i s_j back to x variables
    off = c0 + c1.sum() + sum(c2.values())
    lin = {idx[i]: -2 * c1[i] for i in range(m)}
    quad = {}
    for (a, b), c in c2.items():
        lin[idx[a]] += -2 * c
        lin[idx[b]] += -2 * c
        quad[(idx[a], idx[b])] = 4 * c
    return off, lin, quad


def build_qubo(sc, lam_o=1.0, lam_s=1.0):
    """Return dict with upper-triangular Q (N x N), offset, mapping, auxiliaries."""
    Q = np.zeros((N, N))
    offset = 0.0
    for node in NODES:
        for ap in APPROACHES:
            idx = support(sc, node, ap)

            def f(p, node=node, ap=ap, idx=idx):
                x = [0] * N
                for k, v in zip(idx, p):
                    x[k] = int(v)
                return approach_cost(sc, node, ap, x, lam_o)

            off, lin, quad = quadratic_projection(f, idx)
            offset += off
            for i, v in lin.items():
                Q[i, i] += v
            for (i, j), v in quad.items():
                Q[min(i, j), max(i, j)] += v
    ws = lam_s * sc["switch_weight"]
    for node in NODES:
        for t in range(1, T):
            i, j = var_index(node, t - 1), var_index(node, t)
            Q[i, i] += ws
            Q[j, j] += ws
            Q[i, j] += -2 * ws
    Q[np.abs(Q) < 1e-12] = 0.0
    return {"Q": Q, "offset": offset, "n": N, "lam_o": lam_o, "lam_s": lam_s}


def qubo_energy(qubo, x):
    x = np.asarray(x, dtype=float)
    return float(x @ qubo["Q"] @ x + qubo["offset"])


def all_bits(n=N):
    """Array (2^n, n); row r is the schedule whose string is format(r,'0nb') (bit0 = MSB = A slot1)."""
    return np.array([[int(c) for c in format(r, f"0{n}b")] for r in range(2 ** n)], dtype=float)


def energy_table(qubo):
    X = all_bits(qubo["n"])
    return np.einsum("ri,ij,rj->r", X, qubo["Q"], X) + qubo["offset"]


def to_ising(qubo):
    """x_i = (1 - z_i)/2  ->  E = const + sum h_i z_i + sum J_ij z_i z_j."""
    Q = qubo["Q"]
    n = qubo["n"]
    h = np.zeros(n)
    J = {}
    const = qubo["offset"]
    for i in range(n):
        const += Q[i, i] / 2
        h[i] += -Q[i, i] / 2
        for j in range(i + 1, n):
            if Q[i, j] != 0:
                const += Q[i, j] / 4
                h[i] += -Q[i, j] / 4
                h[j] += -Q[i, j] / 4
                J[(i, j)] = Q[i, j] / 4
    return h, J, const


def mapping():
    return [{"variable": k, "schedule_bit": k + 1, "intersection": NODES[k // T], "slot": k % T + 1,
             "meaning": "1=NS green, 0=EW green", "auxiliary": False} for k in range(N)]
