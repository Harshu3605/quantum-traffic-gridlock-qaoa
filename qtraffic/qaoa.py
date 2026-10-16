"""QAOA: exact-statevector training (numpy) + Qiskit circuit for the final 4,096-shot sampling.

Qubit k  <->  QUBO variable k  <->  schedule bit k+1 (A1..A4, B1..B4). |1> means x=1 (NS green).
Qiskit count keys are little-endian (qubit 0 rightmost); we reverse them to schedule order.
"""
import numpy as np
from scipy.optimize import minimize

from .qubo import energy_table, to_ising, N

MAX_EVALS = 300


class QAOATrainer:
    def __init__(self, qubo, p=3, seed=0, cvar_alpha=1.0):
        self.qubo, self.p, self.seed, self.alpha = qubo, p, seed, cvar_alpha
        E = energy_table(qubo)  # index r = schedule string as integer (bit0 = MSB)
        self.E = E
        # normalise energy scale so gamma ranges are scenario independent
        self.scale = float(E.std()) or 1.0
        self.Ez = (E - E.mean()) / self.scale
        # statevector index in qiskit convention: i = sum x_k 2^k ; map to schedule index r
        n = N
        self.perm = np.array([int(format(i, f"0{n}b")[::-1], 2) for i in range(2 ** n)])
        self.Ediag = self.Ez[self.perm]  # energy per statevector basis index
        self.n_evals = 0
        self.history = []

    def state(self, params):
        p = self.p
        g, b = params[:p], params[p:]
        n = N
        psi = np.full(2 ** n, 1 / np.sqrt(2 ** n), dtype=complex)
        for l in range(p):
            psi = psi * np.exp(-1j * g[l] * self.Ediag)
            c, s = np.cos(b[l]), -1j * np.sin(b[l])
            psi = psi.reshape([2] * n)
            for q in range(n):
                ax = n - 1 - q  # reshape axis for qubit q (little endian)
                a0 = np.take(psi, 0, axis=ax)
                a1 = np.take(psi, 1, axis=ax)
                psi = np.stack([c * a0 + s * a1, s * a0 + c * a1], axis=ax)
            psi = psi.reshape(-1)
        return psi

    def objective(self, params):
        if self.n_evals >= MAX_EVALS:
            return 1e9
        self.n_evals += 1
        pr = np.abs(self.state(params)) ** 2
        if self.alpha >= 1.0:
            val = float(pr @ self.Ediag)
        else:  # CVaR_alpha of the energy distribution
            o = np.argsort(self.Ediag)
            cp = np.cumsum(pr[o])
            w = np.clip(self.alpha - (cp - pr[o]), 0, pr[o])
            val = float(w @ self.Ediag[o] / self.alpha)
        self.history.append(val)
        return val

    def ramp(self, dt):
        p = self.p
        k = (np.arange(p) + 0.5) / p
        return np.concatenate([k * dt, (1 - k) * dt])

    def train(self, init="ramp"):
        rng = np.random.default_rng(self.seed)
        p = self.p
        if init == "interp":
            return self._train_interp(rng)
        if init == "ramp":
            # linear-ramp (TQA-like) schedules; small seeded jitter for robustness study
            cands = [self.ramp(dt) for dt in np.linspace(0.3, 1.5, 7) * p ** 0.5]
            cands = [c + rng.normal(0, 0.02, 2 * p) for c in cands]
        elif init == "random":
            cands = [np.concatenate([rng.uniform(0, 1.0, p), rng.uniform(0, np.pi / 2, p)]) for _ in range(7)]
        else:
            raise ValueError(init)
        vals = [self.objective(c) for c in cands]
        x0 = cands[int(np.argmin(vals))]
        budget = MAX_EVALS - self.n_evals
        res = minimize(self.objective, x0, method="COBYLA",
                       options={"maxiter": budget, "rhobeg": 0.15, "tol": 1e-6})
        best = res.x
        if self.objective_noeval(best) > min(vals):
            best = x0
        self.params = best
        return best

    def _train_interp(self, rng):
        """Layer-wise INTERP (Zhou et al. 2020): optimise depth 1, linearly interpolate the
        angles to depth d+1, re-optimise. The 300-evaluation budget is shared across depths."""
        P = self.p
        full_p = self.p
        cands = []
        for dt in np.linspace(0.3, 1.5, 7):
            self.p = 1
            cands.append(self.ramp(dt) + rng.normal(0, 0.02, 2))
        vals = [self.objective(c) for c in cands]
        x = cands[int(np.argmin(vals))]
        for d in range(1, full_p + 1):
            self.p = d
            if d > 1:
                g, b = x[:d - 1], x[d - 1:]
                grid = np.linspace(0, d - 2, d)
                x = np.concatenate([np.interp(grid, np.arange(d - 1), g),
                                    np.interp(grid, np.arange(d - 1), b)])
            remaining = MAX_EVALS - self.n_evals
            share = remaining // (full_p - d + 1)
            res = minimize(self.objective, x, method="COBYLA",
                           options={"maxiter": max(share, 2 * d + 2), "rhobeg": 0.1, "tol": 1e-6})
            if self.objective_noeval(res.x) <= self.objective_noeval(x):
                x = res.x
        self.p = P
        self.params = x
        return x

    def objective_noeval(self, params):
        pr = np.abs(self.state(params)) ** 2
        return float(pr @ self.Ediag)

    def physical_angles(self):
        """gammas for the *unnormalised* Hamiltonian H = sum h z + J zz (constants dropped)."""
        p = self.p
        return self.params[:p] / self.scale, self.params[p:]


def build_circuit(qubo, gammas, betas, measure=True):
    from qiskit import QuantumCircuit
    h, J, _ = to_ising(qubo)
    qc = QuantumCircuit(N, N if measure else 0)
    qc.h(range(N))
    for g, b in zip(gammas, betas):
        # exp(-i g H), H = sum h_i Z_i + sum J_ij Z_i Z_j
        for (i, j), v in J.items():
            qc.rzz(2 * g * v, i, j)
        for i in range(N):
            if h[i] != 0:
                qc.rz(2 * g * h[i], i)
        qc.rx(2 * b, range(N))
    if measure:
        qc.measure(range(N), range(N))
    return qc


def sample(qc, shots, seed):
    from qiskit.primitives import StatevectorSampler
    res = StatevectorSampler(seed=seed).run([qc], shots=shots).result()[0]
    raw = res.data.c.get_counts()
    return {k[::-1]: v for k, v in sorted(raw.items())}  # schedule-order keys


def circuit_probs(qc_nomeas):
    """Exact probabilities (schedule-order index) of the bound circuit — for consistency checks."""
    from qiskit.quantum_info import Statevector
    pr = Statevector(qc_nomeas).probabilities()
    out = np.zeros(2 ** N)
    for i, v in enumerate(pr):
        out[int(format(i, f"0{N}b")[::-1], 2)] = v
    return out
