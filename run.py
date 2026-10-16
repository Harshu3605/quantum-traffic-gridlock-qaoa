"""Required entry point:  python run.py --scenario <scenario.json> --seed <int> --out <dir>"""
import argparse
import json
import os
import time

import numpy as np

from qtraffic.scenario import load_scenario
from qtraffic.scorer import official_evaluate as simulate  # authoritative official/scorer.py
from qtraffic.qubo import build_qubo, mapping, to_ising
from qtraffic.qaoa import QAOATrainer, build_circuit, sample, circuit_probs
from qtraffic.baselines import baselines, sample_metrics, cost_table, local_search

SHOTS = 4096
DEFAULT_P = 4


def run(scenario_path, seed, out, p=DEFAULT_P, lam_o=1.0, init="interp", write=True):
    t0 = time.time()
    sc = load_scenario(scenario_path)
    qubo = build_qubo(sc, lam_o=lam_o)
    tr = QAOATrainer(qubo, p=p, seed=seed)
    tr.train(init=init)
    gam, bet = tr.physical_angles()
    qc = build_circuit(qubo, gam, bet)
    counts = sample(qc, SHOTS, seed)
    assert sum(counts.values()) == SHOTS
    # consistency: bound Qiskit circuit distribution == trained numpy distribution
    pq = circuit_probs(build_circuit(qubo, gam, bet, measure=False))
    pn = np.zeros(256)
    pn[tr.perm] = np.abs(tr.state(tr.params)) ** 2
    tvd = 0.5 * np.abs(pq - pn).sum()
    S, C = cost_table(sc)
    base = baselines(sc, qubo)
    m = sample_metrics(sc, counts, S, C)
    cmap = dict(zip(S, C))
    top = sorted(counts, key=lambda b: (-counts[b], b))[:10]
    hy = min((local_search(sc, b) for b in top), key=lambda r: (r[1], r[0]))
    most = top[0]
    result = {
        "scenario": sc["name"], "seed": seed, "p": p, "lam_o": lam_o, "init": init,
        "baselines": base, "qaoa_raw": m,
        "qaoa_most_frequent": {"schedule": most, "cost": float(cmap[most])},
        "hybrid_qaoa_plus_local_search": {"schedule": hy[0], "cost": float(hy[1]),
                                          "note": "classical refinement of top-10 samples; NOT raw QAOA output"},
        "training": {"objective_evaluations": tr.n_evals,
                     "final_objective_normalised": tr.objective_noeval(tr.params),
                     "energy_scale": tr.scale, "params_normalised": tr.params.tolist(),
                     "gammas_physical": list(map(float, gam)), "betas": list(map(float, bet))},
        "consistency_tvd_numpy_vs_qiskit": float(tvd),
        "runtime_s": time.time() - t0,
    }
    if write:
        os.makedirs(out, exist_ok=True)
        h, J, const = to_ising(qubo)
        with open(os.path.join(out, "qubo.json"), "w") as f:
            json.dump({
                "form": "minimize x^T Q x + offset, Q upper triangular, x in {0,1}^8",
                "Q": qubo["Q"].tolist(), "offset": qubo["offset"],
                "ising": {"convention": "x_i=(1-z_i)/2, E = const + sum h_i z_i + sum J_ij z_i z_j",
                          "h": h.tolist(), "J": [[i, j, v] for (i, j), v in J.items()], "const": const},
                "variables": mapping(), "auxiliary_variables": [], "num_qubits": 8,
                "penalty_multipliers": {"overflow": lam_o, "switch": 1.0},
                "derivation": "per-approach order-2 Walsh projection of the exact queue recursion "
                              "+ exact switch terms (see REPORT.md)",
            }, f, indent=1)
        from qiskit import qasm3
        with open(os.path.join(out, "circuit.qasm"), "w") as f:
            f.write(qasm3.dumps(qc))
        with open(os.path.join(out, "counts.json"), "w") as f:
            json.dump({"bit_order": "schedule order: chars 1-4 = A slots 1-4, chars 5-8 = B slots 1-4; "
                                    "1=NS green, 0=EW green. Qubit k measures char k+1 "
                                    "(Qiskit little-endian key = reversed string).",
                       "shots": SHOTS, "seed": seed, "counts": counts}, f, indent=1)
        with open(os.path.join(out, "schedule.json"), "w") as f:
            json.dump({
                "bit_order": "A slot1..4 then B slot1..4; 1 = North-South green, 0 = East-West green",
                "bits": most,  # primary raw-QAOA schedule; read directly by official/scorer.py
                "primary": "qaoa_most_frequent (raw QAOA mode)",
                "qaoa_most_frequent": {"bits": most, "A": most[:4], "B": most[4:], **simulate(sc, most)},
                "qaoa_best_sampled": {"bits": m["best_sampled"], **simulate(sc, m["best_sampled"])},
                "qubo_exact_minimizer": base["qubo_exact_minimizer"],
                "hybrid_qaoa_plus_local_search": result["hybrid_qaoa_plus_local_search"],
            }, f, indent=1)
        with open(os.path.join(out, "results.json"), "w") as f:
            json.dump(result, f, indent=1)
        with open(os.path.join(out, "training_history.json"), "w") as f:
            json.dump(tr.history, f)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--p", type=int, default=DEFAULT_P)
    ap.add_argument("--lam-o", type=float, default=1.0)
    ap.add_argument("--init", default="interp", choices=["interp", "ramp", "random"])
    a = ap.parse_args()
    r = run(a.scenario, a.seed, a.out, p=a.p, lam_o=a.lam_o, init=a.init)
    b, m = r["baselines"], r["qaoa_raw"]
    print(f"[{r['scenario']} seed={a.seed} p={a.p}] C*={m['C_star']:.2f} C_rand={m['C_rand']:.2f} "
          f"E_Q={m['E_Q']:.2f} lift={m['lift']:.3f} enrichment={m['enrichment']:.2f} P(opt)={m['p_optimal']:.3f}")
    print(f"  alternating={b['best_alternating']['cost']} greedy={b['greedy']['cost']} "
          f"QUBO-min={b['qubo_exact_minimizer']['cost']} (regret {b['qubo_exact_minimizer']['regret_pct']:.1f}%) "
          f"hybrid={r['hybrid_qaoa_plus_local_search']['cost']}")
    print(f"  evals={r['training']['objective_evaluations']} tvd={r['consistency_tvd_numpy_vs_qiskit']:.2e} "
          f"time={r['runtime_s']:.1f}s -> {a.out}")


if __name__ == "__main__":
    main()
