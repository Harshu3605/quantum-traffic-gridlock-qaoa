"""Experimental validation: seed robustness, generalisation over random hidden-range scenarios,
and ablations over depth, initialisation and overflow-penalty multiplier.

    python experiments.py --out outputs/experiments [--n-random 30]
"""
import argparse
import json
import os
import time

import numpy as np

from run import run

SEEDS = [0, 1, 2, 3, 4]
SCEN = {"R": "official/scenario_R.json", "H": "official/scenario_H.json"}


def random_scenario(rng, k):
    return {
        "name": f"rand{k:02d}",
        "service_capacity": int(rng.integers(4, 7)), "storage_capacity": int(rng.integers(5, 9)),
        "overflow_weight": round(float(rng.uniform(2, 6)), 2),
        "switch_weight": float(rng.choice([0.25, 0.5, 0.75, 1.0, 1.25, 1.5])),
        "link": {"from": "A", "to": "B", "phase": str(rng.choice(["NS", "EW"])),
                 "fraction": round(float(rng.uniform(0.4, 0.8)), 2)},
        "arrivals": {n: {a: rng.integers(0, 9, 4).tolist() for a in ("NS", "EW")} for n in ("A", "B")},
    }


def summarize(rs):
    lifts = [r["qaoa_raw"]["lift"] for r in rs]
    return {"lift_mean": float(np.mean(lifts)), "lift_min": float(np.min(lifts)),
            "lift_min_clipped": float(np.clip(np.min(lifts), 0, 1)),
            "enrichment_mean": float(np.mean([r["qaoa_raw"]["enrichment"] for r in rs])),
            "p_opt_mean": float(np.mean([r["qaoa_raw"]["p_optimal"] for r in rs])),
            "E_Q_mean": float(np.mean([r["qaoa_raw"]["E_Q"] for r in rs])),
            "runtime_max_s": float(np.max([r["runtime_s"] for r in rs]))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="outputs/experiments")
    ap.add_argument("--n-random", type=int, default=30)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    report = {}

    # 1. seed robustness on R and H (default configuration)
    for name in ("R", "H"):
        rs = [run(SCEN[name], s, None, write=False) for s in SEEDS]
        report[f"seeds_{name}"] = {"per_seed": [{"seed": r["seed"], **{k: r["qaoa_raw"][k] for k in
                                    ("E_Q", "lift", "enrichment", "p_optimal", "best_sampled_cost")}}
                                   for r in rs], "baselines": rs[0]["baselines"], **summarize(rs)}

    # 2. ablations on R and H: depth x init, and overflow multiplier
    abl = []
    for name in ("R", "H"):
        for p in (1, 2, 3, 4):
            for init in ("interp", "ramp", "random"):
                rs = [run(SCEN[name], s, None, p=p, init=init, write=False) for s in SEEDS]
                abl.append({"scenario": name, "p": p, "init": init, "lam_o": 1.0, **summarize(rs)})
        for lam in (0.5, 1.5, 2.0):
            rs = [run(SCEN[name], s, None, lam_o=lam, write=False) for s in SEEDS]
            abl.append({"scenario": name, "p": 4, "init": "interp", "lam_o": lam,
                        "qubo_regret_pct": rs[0]["baselines"]["qubo_exact_minimizer"]["regret_pct"],
                        **summarize(rs)})
    report["ablations"] = abl

    # 3. generalisation over random scenarios drawn from the published hidden ranges
    rng = np.random.default_rng(2026)
    gen = []
    sdir = os.path.join(a.out, "random_scenarios")
    os.makedirs(sdir, exist_ok=True)
    for k in range(a.n_random):
        sc = random_scenario(rng, k)
        path = os.path.join(sdir, f"{sc['name']}.json")
        with open(path, "w") as f:
            json.dump(sc, f)
        rs = [run(path, s, None, write=False) for s in SEEDS]
        b = rs[0]["baselines"]
        gen.append({"scenario": sc["name"], "C_star": b["exact_enumeration"]["cost"],
                    "C_rand": b["uniform_random_expected"]["cost"],
                    "greedy": b["greedy"]["cost"], "alternating": b["best_alternating"]["cost"],
                    "qubo_min_cost": b["qubo_exact_minimizer"]["cost"],
                    "qubo_regret_pct": b["qubo_exact_minimizer"]["regret_pct"],
                    "qubo_corr": b["qubo_cost_correlation"],
                    "hybrid_cost_min_seed": max(r["hybrid_qaoa_plus_local_search"]["cost"] for r in rs),
                    **summarize(rs)})
    report["generalisation"] = gen
    reg = [g["qubo_regret_pct"] for g in gen]
    report["generalisation_summary"] = {
        "n": len(gen), "qubo_regret_mean_pct": float(np.mean(reg)), "qubo_regret_max_pct": float(np.max(reg)),
        "frac_regret_zero": float(np.mean([r == 0 for r in reg])),
        "frac_regret_le5": float(np.mean([r <= 5 for r in reg])),
        "lift_mean": float(np.mean([g["lift_mean"] for g in gen])),
        "worst_seed_lift_min": float(np.min([g["lift_min"] for g in gen])),
        "worst_seed_lift_median": float(np.median([g["lift_min"] for g in gen])),
        "enrichment_mean": float(np.mean([g["enrichment_mean"] for g in gen])),
        "greedy_regret_mean_pct": float(np.mean([100 * (g["greedy"] - g["C_star"]) / g["C_star"] for g in gen])),
        "runtime_max_s": float(np.max([g["runtime_max_s"] for g in gen])),
    }
    report["total_time_s"] = time.time() - t0
    with open(os.path.join(a.out, "experiments.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps({k: report[k] for k in ("generalisation_summary",)}, indent=1))
    for n in ("R", "H"):
        s = report[f"seeds_{n}"]
        print(n, {k: round(s[k], 3) for k in ("lift_mean", "lift_min", "enrichment_mean", "p_opt_mean")})
    for r in abl:
        print(r["scenario"], "p", r["p"], r["init"], "lam_o", r["lam_o"],
              "lift_mean %.3f lift_min %.3f enr %.2f" % (r["lift_mean"], r["lift_min"], r["enrichment_mean"]),
              ("regret %.1f%%" % r["qubo_regret_pct"]) if "qubo_regret_pct" in r else "")
    print("total %.0fs" % report["total_time_s"])


if __name__ == "__main__":
    main()
