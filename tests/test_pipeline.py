import json
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from qtraffic.scenario import load_scenario  # noqa: E402
from qtraffic.scorer import official_cost, all_schedules  # noqa: E402
from qtraffic.qubo import build_qubo, energy_table, to_ising, approach_cost, qubo_energy, all_bits  # noqa: E402
from qtraffic.baselines import greedy  # noqa: E402

R = os.path.join(ROOT, "official", "scenario_R.json")


@pytest.mark.parametrize("bits,cost", [("10101010", 116.0), ("11111111", 146.0),
                                       ("00000000", 237.0), ("01111001", 92.5)])
def test_verification_vectors(bits, cost):
    assert official_cost(load_scenario(R), bits) == cost


def test_decomposition_is_exact():
    sc = load_scenario(R)
    for s in all_schedules():
        x = [int(c) for c in s]
        d = sum(approach_cost(sc, n, a, x) for n in "AB" for a in ("NS", "EW"))
        d += sc["switch_weight"] * sum(x[i * 4 + t] != x[i * 4 + t - 1] for i in range(2) for t in range(1, 4))
        assert abs(d - official_cost(sc, s)) < 1e-9


def test_ising_matches_qubo():
    q = build_qubo(load_scenario(R))
    h, J, c = to_ising(q)
    X = all_bits()
    for x in X[::7]:
        z = 1 - 2 * x
        e = c + h @ z + sum(v * z[i] * z[j] for (i, j), v in J.items())
        assert abs(e - qubo_energy(q, x)) < 1e-9


def test_qubo_minimizer_R():
    sc = load_scenario(R)
    E = energy_table(build_qubo(sc))
    C = np.array([official_cost(sc, s) for s in all_schedules()])
    assert C[int(E.argmin())] == C.min() == 72.0


def test_greedy_R():
    sc = load_scenario(R)
    assert official_cost(sc, greedy(sc)) == 92.5  # greedy reproduces verification vector 0111|1001


def test_run_outputs(tmp_path):
    from run import run
    r = run(R, 0, str(tmp_path))
    for f in ("qubo.json", "circuit.qasm", "counts.json", "schedule.json"):
        assert (tmp_path / f).exists()
    counts = json.load(open(tmp_path / "counts.json"))["counts"]
    assert sum(counts.values()) == 4096 and all(len(k) == 8 for k in counts)
    assert r["training"]["objective_evaluations"] <= 300
    assert r["consistency_tvd_numpy_vs_qiskit"] < 1e-9
    assert r["qaoa_raw"]["lift"] > 0.5
    # determinism
    r2 = run(R, 0, None, write=False)
    assert r2["qaoa_raw"]["E_Q"] == r["qaoa_raw"]["E_Q"]
    # QASM re-import reproduces the same circuit distribution
    from qiskit import qasm3
    from qiskit.quantum_info import Statevector
    qc = qasm3.loads(open(tmp_path / "circuit.qasm").read())
    qc.remove_final_measurements()
    p = Statevector(qc).probabilities_dict()
    shots = 4096
    top = max(counts, key=counts.get)
    assert abs(p[top[::-1]] - counts[top] / shots) < 0.03
