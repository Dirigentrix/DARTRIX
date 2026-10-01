"""DARTRIX-D2: stochastic network of coupled bistable (double-well) nodes.

The deterministic node drift is -dV/dx = a*x - b*x**3 for
V(x) = b*x**4/4 - a*x**2/2. Coupling is K W x, with W symmetric,
non-negative and zero-diagonal. Around the uncoupled synchronized wells
x_i = +/-sqrt(a/b), the Jacobian is -2a I + K W. Thus the linear
stability threshold of that reference well state is K_c = 2a/lambda_max(W).
This is a local analytic threshold, not a claim about the global stochastic
phase transition; simulations should be used to assess finite-size behavior.
Only the Python standard library is required.
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Sequence, Tuple

Matrix = Sequence[Sequence[float]]
Vector = List[float]


def _validate_matrix(weights: Matrix) -> List[List[float]]:
    matrix = [[float(value) for value in row] for row in weights]
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise ValueError("weights must be a non-empty square matrix")
    for i in range(n):
        for j in range(n):
            value = matrix[i][j]
            if not math.isfinite(value) or value < 0:
                raise ValueError("weights must be finite and non-negative")
            if abs(value - matrix[j][i]) > 1e-12:
                raise ValueError("weights must be symmetric")
        if abs(matrix[i][i]) > 1e-12:
            raise ValueError("self-coupling (diagonal weights) must be zero")
    return matrix


def largest_eigenvalue_symmetric(matrix: Matrix, tolerance: float = 1e-12,
                                 max_iterations: int = 10000) -> float:
    """Estimate the spectral radius of a symmetric non-negative matrix.

    Power iteration is deterministic and converges to the Perron root for the
    non-negative matrices accepted by this module. Zero matrices return 0.
    """
    a = _validate_matrix(matrix)
    n = len(a)
    if tolerance <= 0 or max_iterations < 1:
        raise ValueError("tolerance and max_iterations must be positive")
    x = [1.0 / math.sqrt(n)] * n
    eigenvalue = 0.0
    for _ in range(max_iterations):
        y = [sum(a[i][j] * x[j] for j in range(n)) for i in range(n)]
        norm = math.sqrt(sum(v * v for v in y))
        if norm == 0.0:
            return 0.0
        y = [v / norm for v in y]
        next_value = sum(y[i] * sum(a[i][j] * y[j] for j in range(n))
                         for i in range(n))
        if abs(next_value - eigenvalue) <= tolerance * max(1.0, abs(next_value)):
            return next_value
        x, eigenvalue = y, next_value
    return eigenvalue


class D2Network:
    """Euler-Maruyama simulator for a network of stochastic bistable nodes.

    Parameters
    ----------
    weights: symmetric non-negative adjacency matrix, with zero diagonal.
    a, b: positive coefficients in drift a*x - b*x**3.
    coupling: non-negative scalar multiplying W @ x.
    noise: non-negative diffusion amplitude (standard Wiener convention).
    seed: optional seed for reproducible trajectories.
    """

    def __init__(self, weights: Matrix, a: float = 1.0, b: float = 1.0,
                 coupling: float = 0.0, noise: float = 0.1,
                 seed: Optional[int] = None) -> None:
        self.weights = _validate_matrix(weights)
        for name, value in (("a", a), ("b", b), ("coupling", coupling), ("noise", noise)):
            if not math.isfinite(value):
                raise ValueError("{} must be finite".format(name))
        if a <= 0 or b <= 0 or coupling < 0 or noise < 0:
            raise ValueError("a and b must be positive; coupling and noise non-negative")
        self.a, self.b = float(a), float(b)
        self.coupling, self.noise = float(coupling), float(noise)
        self.rng = random.Random(seed)
        self.state = [math.sqrt(self.a / self.b)] * len(self.weights)

    @property
    def size(self) -> int:
        return len(self.weights)

    @property
    def critical_coupling(self) -> float:
        """Local loss-of-stability threshold K_c around the reference wells."""
        rho = largest_eigenvalue_symmetric(self.weights)
        return math.inf if rho == 0.0 else 2.0 * self.a / rho

    def step(self, dt: float, state: Optional[Sequence[float]] = None) -> Vector:
        """Advance one Euler-Maruyama step and store/return the new state."""
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError("dt must be finite and positive")
        x = list(self.state if state is None else state)
        if len(x) != self.size or any(not math.isfinite(float(v)) for v in x):
            raise ValueError("state must contain one finite value per node")
        result = []
        scale = self.noise * math.sqrt(dt)
        for i, value in enumerate(x):
            interaction = sum(self.weights[i][j] * x[j] for j in range(self.size))
            drift = self.a * value - self.b * value ** 3 + self.coupling * interaction
            result.append(value + drift * dt + scale * self.rng.gauss(0.0, 1.0))
        self.state = result
        return list(result)

    def simulate(self, steps: int, dt: float, initial_state: Optional[Sequence[float]] = None,
                 record_every: int = 1) -> List[Vector]:
        """Return snapshots including the initial condition and sampled steps."""
        if steps < 0 or record_every < 1:
            raise ValueError("steps must be non-negative and record_every positive")
        if initial_state is not None:
            initial = list(initial_state)
            if len(initial) != self.size or any(not math.isfinite(float(v)) for v in initial):
                raise ValueError("initial_state must contain one finite value per node")
            self.state = [float(v) for v in initial]
        history = [list(self.state)]
        for index in range(1, steps + 1):
            current = self.step(dt)
            if index % record_every == 0 or index == steps:
                history.append(current)
        return history

    @staticmethod
    def mean_activity(state: Sequence[float]) -> float:
        if not state:
            raise ValueError("state cannot be empty")
        return sum(abs(float(value)) for value in state) / len(state)

    @staticmethod
    def polarization(state: Sequence[float]) -> float:
        """Signed mean state, a simple observable for collective alignment."""
        if not state:
            raise ValueError("state cannot be empty")
        return sum(float(value) for value in state) / len(state)
