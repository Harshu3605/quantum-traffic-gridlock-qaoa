"""Scenario loading / validation. Bit order everywhere: A slots 1-4 then B slots 1-4; 1 = NS green, 0 = EW green."""
import json
from decimal import Decimal, ROUND_HALF_UP

APPROACHES = ("NS", "EW")
NODES = ("A", "B")


def load_scenario(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return normalize(raw)


def normalize(raw):
    """Accept a few key aliases so organiser JSON variants still load."""
    _MISSING = object()

    def get(*keys, default=_MISSING):
        for k in keys:
            if k in raw:
                return raw[k]
        if default is _MISSING:
            raise ValueError(f"scenario missing required key (any of {keys})")
        return default

    arr = get("arrivals")
    if arr is None:
        raise ValueError("scenario needs 'arrivals'")
    arrivals = {}
    for n in NODES:
        node = arr.get(n) or arr.get(n.lower())
        arrivals[n] = {}
        for a in APPROACHES:
            v = node.get(a) if a in node else node.get(a.lower())
            arrivals[n][a] = [int(x) for x in v]
    T = int(get("slots", "num_slots", default=len(arrivals["A"]["NS"])))
    link = get("link")
    approach = str(link.get("phase", link.get("approach"))).upper()
    approach = {"1": "NS", "0": "EW", "N-S": "NS", "E-W": "EW"}.get(approach, approach)
    sc = {
        "name": str(get("name", "id", default="scenario")),
        "slots": T,
        "capacity": int(get("service_capacity", "capacity")),
        "storage": int(get("storage_capacity", "storage", "nominal_storage", "queue_storage")),
        "overflow_weight": float(get("overflow_weight")),
        "switch_weight": float(get("switch_weight", "switching_weight")),
        "link": {"from": "A", "to": "B", "approach": approach,
                 "fraction": link.get("fraction", link.get("transfer_fraction"))},
        "arrivals": arrivals,
        "raw": raw,  # untouched original, passed to the official scorer
    }
    if sc["link"]["fraction"] is None:
        raise ValueError("link needs 'fraction'")
    if T != 4:
        raise ValueError("mandatory model has 4 slots")
    if approach not in APPROACHES:
        raise ValueError(f"bad link approach {approach}")
    return sc


def round_half_up(fraction, departures):
    """Exact decimal half-up of fraction*departures, identical to official scorer.py."""
    amount = Decimal(str(fraction)) * Decimal(int(departures))
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
