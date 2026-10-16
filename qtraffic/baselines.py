"""Classical baselines and sampling-quality metrics (Sec. 8-9 of the problem statement)."""
import numpy as np

from .scenario import NODES, round_half_up
from .scorer import official_cost, all_schedules
from .qubo import energy_table

# the four alternating schedules: each intersection alternates starting with NS or EW
ALTERNATING = ["10101010", "10100101", "01011010", "01010101"]


def cost_table(sc):
    S = all_schedules()
    return S, np.array([official_cost(sc, s) for s in S])


def greedy(sc):
    """Per slot, each intersection serves its larger queue after arrivals (ties -> NS)."""
    T, cap, link = sc["slots"], sc["capacity"], sc["link"]
    q = {(n, a): 0.0 for n in NODES for a in ("NS", "EW")}
    bits = [0] * 8
    pending = 0
    for t in range(T):
        for n in NODES:
            for a in ("NS", "EW"):
                q[(n, a)] += sc["arrivals"][n][a][t]
        q[("B", link["approach"])] += pending
        pending = 0
        for i, n in enumerate(NODES):
            g = "NS" if q[(n, "NS")] >= q[(n, "EW")] else "EW"
            bits[i * T + t] = 1 if g == "NS" else 0
            s = min(cap, q[(n, g)])
            q[(n, g)] -= s
            if n == link["from"] and g == link["approach"]:
                pending = round_half_up(link["fraction"], s)
    return "".join(map(str, bits))


def elite_set(S, C, k=13):
    order = sorted(range(len(S)), key=lambda r: (C[r], S[r]))
    return set(S[r] for r in order[:k])


def sample_metrics(sc, counts, S=None, C=None):
    if S is None:
        S, C = cost_table(sc)
    cmap = dict(zip(S, C))
    shots = sum(counts.values())
    EQ = sum(cmap[b] * c for b, c in counts.items()) / shots
    Cstar, Crand = float(C.min()), float(C.mean())
    elite = elite_set(S, C)
    frac = sum(c for b, c in counts.items() if b in elite) / shots
    p_opt = sum(c for b, c in counts.items() if cmap[b] == Cstar) / shots
    best = min(counts, key=lambda b: (cmap[b], b))
    return {"E_Q": float(EQ), "C_star": Cstar, "C_rand": Crand,
            "lift": float((Crand - EQ) / (Crand - Cstar)) if Crand > Cstar else float("nan"),
            "elite_fraction": frac, "enrichment": frac / (13 / 256), "p_optimal": p_opt,
            "best_sampled": best, "best_sampled_cost": float(cmap[best]), "shots": shots}


def local_search(sc, start):
    """Hybrid refinement (labelled separately): steepest-descent single-bit flips on official cost."""
    cur, cc = start, official_cost(sc, start)
    while True:
        nb = [cur[:i] + ("1" if cur[i] == "0" else "0") + cur[i + 1:] for i in range(8)]
        cs = [official_cost(sc, b) for b in nb]
        k = int(np.argmin(cs))
        if cs[k] >= cc:
            return cur, cc
        cur, cc = nb[k], cs[k]


def baselines(sc, qubo):
    S, C = cost_table(sc)
    alt = min(ALTERNATING, key=lambda b: (official_cost(sc, b), b))
    g = greedy(sc)
    E = energy_table(qubo)
    qmin = S[int(np.argmin(E))]
    ex = S[int(np.argmin(C))]
    qc = official_cost(sc, qmin)
    return {
        "best_alternating": {"schedule": alt, "cost": official_cost(sc, alt)},
        "greedy": {"schedule": g, "cost": official_cost(sc, g)},
        "exact_enumeration": {"schedule": ex, "cost": float(C.min()),
                              "n_optimal": int((C == C.min()).sum())},
        "uniform_random_expected": {"cost": float(C.mean())},
        "qubo_exact_minimizer": {"schedule": qmin, "cost": qc,
                                 "regret_pct": float(100 * (qc - C.min()) / C.min())},
        "qubo_cost_correlation": float(np.corrcoef(E, C)[0, 1]),
    }
