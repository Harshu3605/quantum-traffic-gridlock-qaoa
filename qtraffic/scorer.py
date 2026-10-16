"""Own re-implementation (simulate) cross-checked against official/scorer.py, which is
used for every reported cost (official_cost).

Official-cost simulator re-implemented from the problem statement (Sec. 3 & 5).

cost = delay + overflow_weight*overflow + switch_weight*switches
"""
from .scenario import NODES, APPROACHES, round_half_up


def schedule_bits(s):
    """str '01111001' / list -> list[int] of length 8 (A1..A4,B1..B4)."""
    if isinstance(s, str):
        s = s.replace("|", "").replace(" ", "")
        return [int(c) for c in s]
    return [int(b) for b in s]


def simulate(sc, bits):
    bits = schedule_bits(bits)
    T = sc["slots"]
    cap, sto = sc["capacity"], sc["storage"]
    link = sc["link"]
    q = {(n, a): 0.0 for n in NODES for a in APPROACHES}
    pending = 0  # transfer arriving at B linked approach at start of next slot
    delay = overflow = 0.0
    for t in range(T):
        for n in NODES:
            for a in APPROACHES:
                q[(n, a)] += sc["arrivals"][n][a][t]
        q[("B", link["approach"])] += pending
        pending = 0
        for i, n in enumerate(NODES):
            g = "NS" if bits[i * T + t] == 1 else "EW"
            served = min(cap, q[(n, g)])
            q[(n, g)] -= served
            if n == link["from"] and g == link["approach"]:
                pending = round_half_up(link["fraction"], served)
        for k in q:
            delay += q[k]
            overflow += max(0.0, q[k] - sto)
    switches = 0
    for i in range(len(NODES)):
        for t in range(1, T):
            switches += bits[i * T + t] != bits[i * T + t - 1]
    cost = delay + sc["overflow_weight"] * overflow + sc["switch_weight"] * switches
    return {"cost": cost, "delay": delay, "overflow": overflow, "switches": switches}


def to_official(sc):
    """Scenario in the organisers' scorer.py schema (built from the normalised fields)."""
    return {"name": sc["name"], "arrivals": sc["arrivals"],
            "service_capacity": int(sc["capacity"]), "storage_capacity": int(sc["storage"]),
            "overflow_weight": sc["overflow_weight"], "switch_weight": sc["switch_weight"],
            "link": {"from": "A", "to": "B", "phase": sc["link"]["approach"],
                     "fraction": sc["link"]["fraction"]}}


def official_evaluate(sc, bits):
    """Authoritative evaluation: calls the organisers' official/scorer.py unchanged."""
    from official.scorer import evaluate
    return evaluate(to_official(sc), schedule_bits(bits))


def official_cost(sc, bits):
    return float(official_evaluate(sc, bits)["cost"])


def all_schedules(n=8):
    return [format(i, f"0{n}b") for i in range(2 ** n)]
