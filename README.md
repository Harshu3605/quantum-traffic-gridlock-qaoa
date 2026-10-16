# Quantum Traffic Gridlock — QUBO + QAOA signal coordination

IBM Qiskit Fall Fest 2026 (QC@IITI). This pipeline coordinates traffic-light phases at two linked intersections (A → B) over four slots. It builds a QUBO from a documented traffic-modelling rule, trains QAOA with a numpy statevector, samples the bound Qiskit circuit 4,096 times, and compares the result against every baseline the problem statement asks for.

## Quick start
```bash
pip install -r requirements.txt
python run.py --scenario official/scenario_R.json --seed 0 --out outputs/R/seed_0
python official/scorer.py --scenario official/scenario_R.json --schedule outputs/R/seed_0/schedule.json
python experiments.py --out outputs/experiments      # robustness, ablations, 30 random scenarios (~2 min)
python -m pytest -q tests
```
Run options: `--p {1..4}` (default 4), `--init {interp,ramp,random}` (default `interp`), `--lam-o <float>` (overflow-penalty multiplier, default 1.0). The pipeline needs only the CPU and no network, and one run takes under 2 s.

## Bit order (used everywhere)
`x = A1 A2 A3 A4 B1 B2 B3 B4`. `1` = North–South green, `0` = East–West green. Qubit *k* is QUBO variable *k*, which is character *k+1* of every schedule string. `counts.json` keys are in this schedule order. The native Qiskit key is the reversed string.

## Outputs (per `--out` dir)
| file | content |
|---|---|
| `qubo.json` | Upper-triangular `Q`, `offset`, the equivalent Ising `h, J, const`, the variable→schedule-bit mapping and `auxiliary_variables: []` (none used; 8 qubits) |
| `circuit.qasm` | The final bound-parameter QAOA circuit in OpenQASM 3 |
| `counts.json` | Exactly 4,096 raw shots of that circuit as bitstring → count |
| `schedule.json` | Top-level `bits` holds the primary schedule (the most frequent raw-QAOA sample), so the official `scorer.py` reads it directly. Also decoded: most frequent sample, best sample, QUBO minimizer, and the hybrid result (labelled) |
| `results.json` | All baselines, sampling metrics (E_Q, lift, enrichment), training info and a consistency check |

## Layout
```
qtraffic/scenario.py   JSON loading (tolerant of key aliases), validation
official/              organisers' scorer.py + scenario_R.json + README, copied UNMODIFIED
qtraffic/scorer.py     official_cost() calls official/scorer.py; simulate() is our own re-implementation (cross-check)
qtraffic/qubo.py       modelling rule -> QUBO / Ising
qtraffic/qaoa.py       numpy statevector training (<=300 evals) + Qiskit circuit + sampling
qtraffic/baselines.py  alternating, greedy, enumeration, random mean, QUBO ceiling, metrics, hybrid
run.py                 required CLI;  experiments.py  validation suite;  tests/  pytest
scenarios/H_sample.json  SYNTHETIC stand-in for H (scenario R = official/scenario_R.json, the organisers' file)
outputs/R/seed_0..4, outputs/H_sample/seed_0..4, outputs/experiments/experiments.json
```

**Scorer.** Every reported cost comes from the organisers' `official/scorer.py`, called unchanged. Our own simulator and the per-approach QUBO decomposition match it exactly: on all 256 schedules for 40 random scenarios, including fractions such as 0.45 and 0.65 where decimal half-up rounding matters (`tests/test_official.py`). Scenario JSON uses the official schema (`service_capacity`, `storage_capacity`, `link.phase`). A missing key raises an error instead of falling back to a default.

**Note on H.** The official scenario H is not in this folder yet. `scenarios/H_sample.json` is a SYNTHETIC scenario within the hidden ranges. When H is released, run it without changing any code:
`for s in 0 1 2 3 4; do python run.py --scenario H.json --seed $s --out outputs/H/seed_$s; done`

See [REPORT.md](REPORT.md) for the derivation and results, and [AI_DISCLOSURE.md](AI_DISCLOSURE.md) for the AI-use disclosure.
