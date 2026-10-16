"""Cross-checks against the organisers' official/scorer.py (unmodified copy)."""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from official.scorer import evaluate  # noqa: E402
from qtraffic.scenario import normalize, load_scenario  # noqa: E402
from qtraffic.scorer import simulate, all_schedules, official_cost  # noqa: E402
from qtraffic.qubo import approach_cost  # noqa: E402
from qtraffic.baselines import greedy  # noqa: E402


def rand_official(rng):
    return {"arrivals": {n: {a: [int(v) for v in rng.integers(0, 9, 4)] for a in ("NS", "EW")} for n in "AB"},
            "service_capacity": int(rng.integers(4, 7)), "storage_capacity": int(rng.integers(5, 9)),
            "overflow_weight": float(rng.choice([2, 3.5, 4, 6])), "switch_weight": float(rng.choice([0.25, 0.5, 1.5])),
            # include fractions where float floor(x+0.5) and Decimal half-up could disagree
            "link": {"from": "A", "to": "B", "phase": str(rng.choice(["NS", "EW"])),
                     "fraction": float(rng.choice([0.4, 0.45, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.43, 0.57]))}}


@pytest.mark.parametrize("k", range(40))
def test_own_simulator_and_decomposition_equal_official(k):
    raw = rand_official(np.random.default_rng(k))
    sc = normalize(raw)
    for s in all_schedules():
        off = evaluate(raw, s)
        own = simulate(sc, s)
        assert abs(own["cost"] - off["cost"]) < 1e-9, (k, s)
        x = [int(c) for c in s]
        d = sum(approach_cost(sc, n, a, x) for n in "AB" for a in ("NS", "EW")) + sc["switch_weight"] * off["switches"]
        assert abs(d - off["cost"]) < 1e-6


def test_missing_key_fails_loudly():
    raw = json.load(open(os.path.join(ROOT, "official", "scenario_R.json")))
    del raw["storage_capacity"]
    with pytest.raises(ValueError):
        normalize(raw)


def test_official_cli_reads_our_schedule(tmp_path):
    from run import run
    r = run(os.path.join(ROOT, "official", "scenario_R.json"), 0, str(tmp_path))
    sch = json.load(open(tmp_path / "schedule.json"))["qaoa_most_frequent"]
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"bits": sch["bits"]}))
    out = subprocess.run([sys.executable, os.path.join(ROOT, "official", "scorer.py"),
                          "--scenario", os.path.join(ROOT, "official", "scenario_R.json"), "--schedule", str(p)],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out)["cost"] == sch["cost"] == r["qaoa_most_frequent"]["cost"]


def test_greedy_official():
    sc = load_scenario(os.path.join(ROOT, "official", "scenario_R.json"))
    assert official_cost(sc, greedy(sc)) == 92.5
