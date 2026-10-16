# AI-use disclosure (outside report page limit)

**Tool.** Claude (Anthropic, model Claude Opus 5.5), used through Claude Code.

**What the AI did.**
- Read the problem statement.
- Proposed the formulation: exact per-approach decomposition plus an order-2 Walsh projection.
- Wrote all code in `qtraffic/`, `run.py`, `experiments.py` and `tests/`.
- Ran the experiments and drafted README.md, REPORT.md, this disclosure and the plain-language explainer (`docs/`), including the scripts that render them to PDF.

**What the team did.**
- Provided the problem statement and the organisers' official scorer and scenario files.
- Directed the work, chose the repository, and created and published the GitHub repo.
- Reviewed the outputs.

**How results were verified independently of the AI's claims.**
- All reported costs come from the organisers' `official/scorer.py`, used unmodified. Our simulator and QUBO decomposition are asserted equal to it on 40 random scenarios × 256 schedules. The four verification costs come from the PS.
- The decomposition C = Σ D_k + switches is asserted exactly on all 256 schedules (unit test).
- The QUBO↔Ising conversion is asserted equal on sample states (unit test).
- The Qiskit circuit distribution is compared to the trained numpy distribution (TVD ≈ 1e−15 on every run). A test re-imports `circuit.qasm` and compares it to `counts.json`.
- Determinism: the same seed gives identical results (unit test).
- All numbers in REPORT.md are copied from `outputs/experiments/experiments.json` and `outputs/*/seed_*/results.json`, which anyone can regenerate with the commands in README.md.

**Team responsibility.** The team must review the derivation, and rerun the pipeline on the official H before submission. The AI did not have H.
