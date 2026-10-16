# Quantum Traffic Gridlock — Technical Report

## 1. Traffic model and official cost
Decision bits are x = (A1..A4, B1..B4), with 1 = NS green and 0 = EW green. For each approach k (node n, direction d), the queue follows the PS recursion:
q_{k,t} = q_{k,t-1} + a_{k,t} + u_{k,t} − min(c, q_{k,t-1} + a_{k,t} + u_{k,t})·g_{k,t}.
Here g is the green indicator: x for NS and 1−x for EW. The term u is the transfer, and it is non-zero only for B's linked approach: u_{t+1} = ⌊f·s^A_t + ½⌋, where s^A_t is the number of vehicles A's linked approach serves in slot t. The cost is C(x) = Σ_t Σ_k [q_{k,t} + w_o·max(0, q_{k,t} − storage)] + w_s·#switches. Every cost in this report is computed by the organisers' unmodified `official/scorer.py`, which reproduces 116, 146, 237 and 92.5. Our own simulator matches it exactly: on all 256 schedules for 40 random scenarios, including the decimal half-up transfer rounding.

## 2. QUBO derivation (scenario-independent modelling rule)
**Exact decomposition.** C(x) = Σ_k D_k(x_{S_k}) + w_s Σ_{i,t} (x_{i,t} ⊕ x_{i,t−1}). Each per-approach queue cost D_k depends only on its *support* S_k:
- For three of the four approach groups, S_k is the four bits of the approach's own intersection.
- For B's linked approach, S_k also includes A's four bits, because its inflow is A's linked departures. This dependence carries the A→B coordination.

The decomposition is verified exactly on all 256 schedules (`test_decomposition_is_exact`).

**Switch term.** This term is already quadratic: x_t ⊕ x_{t−1} = x_t + x_{t−1} − 2x_t x_{t−1}. It is encoded exactly.

**Queue terms.** D_k is not quadratic. The min and max operations inside the Lindley recursion create interactions of order up to |S_k|. We replace each D_k by its *L2-optimal quadratic surrogate on its own support*. In spin variables s = 1−2x, D_k = Σ_{A⊆S_k} ĉ_A Π_{i∈A} s_i (Walsh–Fourier expansion), and we keep the terms with |A| ≤ 2. Under the uniform measure, this truncation is the least-squares best quadratic, so no schedule is preferred in the fit. The coefficients ĉ_A = 2^{−|S_k|} Σ D_k(s)·Π s_i are computed by running the single-approach queue recursion over that approach's support cube. Linearity then gives the full QUBO: Q = Σ_k proj₂(D_k) + exact switch terms.

**Integrity.** The rule is identical for every scenario. It uses only traffic dynamics: arrivals, capacity, storage, transfer and weights. It never ranks schedules, never locates the optimum, and never encodes a target answer, and enumeration of the official cost appears only in the benchmarks. There is one honest caveat. Because the support of B's linked approach is all 8 bits, computing that one approach's projection touches all 256 assignments of that single approach's queue. Summed over approaches, the result equals the global order-2 Walsh truncation of C. It is still a fixed approximation rule that has no knowledge of the minimizer.

**Size.** 8 binary variables, 8 qubits, no auxiliary variables. The fully linked approach makes the coupling graph complete, with 28 ZZ terms. The Ising form uses x = (1−z)/2.

**Penalties.** Overflow is soft, as specified, with weight w_o. A multiplier λ_o on the overflow part is kept as an ablation knob, default 1, so the QUBO matches the official weights.

## 3. QAOA design
- **Ansatz.** |+⟩^8, then p layers of e^{−iγH_C} (RZZ and RZ gates) followed by an RX(2β) mixer. Default p = 4, the maximum allowed. Training normalises the cost to zero mean and unit standard deviation over the cube, so the γ ranges are scenario-independent. The physical angles γ/σ are bound into the exported circuit.
- **Training.** Exact numpy statevector for 256 amplitudes. The objective is the expected QUBO energy, because lift is a mean-cost metric.
- **Initialisation (INTERP).** Score 7 linear-ramp (TQA) starts at p = 1. Then for each depth d = 1…p, run COBYLA and linearly interpolate the angles to depth d+1. All of this shares a hard **300-evaluation** budget that the code enforces. The seed adds a small jitter to the starting angles.
- **Sampling and consistency.** Final sampling uses Qiskit `StatevectorSampler(seed)` with exactly 4,096 shots. We check that the Qiskit statevector of the bound circuit matches the trained numpy distribution (TVD ≈ 1e−15). A test also re-imports `circuit.qasm` and checks it against `counts.json`.
- **Resources.** One run takes about 0.4–2 s on CPU, far below the 10-minute limit.

## 4. Results (5 seeds: 0–4; costs are official costs)
| | R | H_sample (synthetic) |
|---|---|---|
| (1) best alternating | 116.0 (1010\|1010) | 194.0 |
| (2) greedy (larger queue, ties NS) | 92.5 (0111\|1001) | 188.0 |
| (3) exact optimum C* | **72.0** (1110\|1010) | **183.0** (1001\|0011) |
| (4) uniform-random mean C_rand | 151.25 | 247.65 |
| (5) QUBO exact minimizer (surrogate ceiling) | 72.0, regret 0 % | 188.0, regret 2.7 % |
| corr(QUBO, official) over 256 schedules | 0.995 | 0.991 |
| (6) raw QAOA E_Q (mean over seeds) | 88.2 | 194.5 |
| lift: mean / **worst seed** | 0.796 / **0.792** | 0.822 / **0.819** |
| elite enrichment (13 best) | 12.55× | 10.61× |
| P(optimal schedule) per shot | 8.3 % | 8.5 % |
| hybrid QAOA + bit-flip local search (labelled, not raw) | 72.0 | 183.0 |

On both scenarios, raw QAOA's mean sample cost beats the alternating baseline. Its mean does not beat greedy, which is a single deterministic schedule: on R, E_Q = 88.2 against greedy's 92.5, but on H_sample E_Q is 194.5, worse than greedy's 188. About 8 % of shots hit the exact optimum.

**Generalisation.** 30 random scenarios from the published hidden ranges, with a fixed generator seed of 2026; files are in `outputs/experiments/random_scenarios`.
- QUBO regret: mean 0.9 %, at most 5 % on 93 % of scenarios, and exactly zero on 60 %.
- Worst case: 10.6 % (rand17). The next worst is 8.0 %.
- Lift: mean 0.84. The worst seed's lift has a median of 0.85 and a minimum of 0.64.
- Enrichment: mean 12.3×.
- Greedy's mean regret is 5.4 %.
- The labelled hybrid reached C* on all 30 scenarios for every seed.

**Ablations (5 seeds each; worst-seed lift shown).**
| p | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| R, INTERP | 0.613 | 0.729 | 0.772 | **0.792** |
| R, linear ramp only | 0.613 | 0.687 | 0.692 | 0.515 |
| R, random init | 0.613 | 0.593 | 0.591 | 0.597 |
| H_sample, INTERP | 0.504 | 0.704 | 0.784 | **0.819** |
| H_sample, random init | 0.504 | 0.498 | 0.513 | 0.509 |

Only INTERP improves steadily with depth. Without layer-wise warm starts, COBYLA with 300 evaluations gets stuck at p ≥ 3. The overflow multiplier λ_o ∈ {0.5, 1, 1.5, 2} changes lift by less than 0.02. On H_sample, λ_o = 0.5 happens to remove the 2.7 % regret. We kept λ_o = 1 because tuning it on the evaluation scenario would be overfitting.

## 5. Limitations (honest)
- The quadratic surrogate is approximate. Regret can reach about 10 % when queue saturation creates strong higher-order interactions. A fix with auxiliary slack variables (≤ 8 spare qubits) is a possible extension that we did not implement.
- Training uses the exact noiseless statevector, which is legitimate in simulation because training shots are optional. We performed no noise or hardware study.
- At 8 qubits, enumeration is trivial, so we claim no quantum advantage. QAOA here is a sampler whose distribution is strongly concentrated on low-cost schedules: about 12× elite enrichment.
- H_sample is synthetic. The official H (released at hour 18) and S must be run with the unchanged code.
