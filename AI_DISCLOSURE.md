# AI-use disclosure (outside report page limit)

**AI tool used.** Claude (Anthropic, model Claude Opus 5.5) through Claude Code, a coding assistant. The rules (Sec. 10) permit AI assistants and general-purpose libraries, provided teams declare the assistance and verify the results independently. This page does that.

**Who did what.**
| Area | Team (humans) | AI assistant |
|---|---|---|
| Problem understanding and scope | Read the problem statement and set the goal: an end-to-end pipeline that follows every PS requirement and reports results honestly | Turned the PS into a requirement checklist (CLI, files, limits, baselines, metrics) |
| Official inputs | Obtained the scorer and scenario R. Followed up with the organisers until scenario H was released, then supplied H | Used the files unmodified and ran H with unchanged code |
| Modelling and QUBO | Required strict compliance with the PS rules, including no hard-coded or answer-encoding QUBO, and accepted the documented rule | Proposed and implemented the per-approach decomposition and the order-2 Walsh projection |
| QAOA and experiments | Required compliance with the PS resource limits and honest reporting of results | Wrote the QAOA code, the baselines, the ablations and the 30-scenario generalisation test |
| Submission checks | Caught that a pasted submission checklist belonged to another track, and confirmed the correct one | Mapped every item of the correct checklist to a file |
| Repository and submission | Chose the repository name, created the public GitHub repo, made the initial commit and push, and uploads the Drive submission | Added later commits and the `v1.x-submission` tags, and assembled the Drive folder and zip |
| Documentation | Asked for a plain-language explainer so the team could understand and present the work, and reviewed the outputs | Drafted the README, the report, this disclosure and the explainer |

**How the results were verified (not taken on trust from the AI).**
- Every reported cost comes from the organisers' `official/scorer.py`, used unmodified. It reproduces the PS verification costs 116, 146, 237 and 92.5.
- Our simulator and the QUBO decomposition were asserted equal to the official scorer on 40 random scenarios × 256 schedules. The QUBO↔Ising conversion was also checked (52 automated tests).
- The Qiskit circuit and the trained numpy state agree to a TVD of about 1e−15. A test re-imports `circuit.qasm`.
- Results are deterministic per seed. Anyone can regenerate every number with the commands in README.md.

**Responsibility.** The team takes responsibility for the submission, including the AI-assisted parts.
