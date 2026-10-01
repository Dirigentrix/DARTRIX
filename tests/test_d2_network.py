import math

import pytest

from core.engines.d2_network import D2Network, largest_eigenvalue_symmetric


def test_critical_coupling_for_two_node_edge():
    model = D2Network([[0.0, 1.0], [1.0, 0.0]], a=2.0, b=1.0)
    assert model.critical_coupling == pytest.approx(4.0)


def test_zero_weights_have_infinite_threshold():
    model = D2Network([[0.0, 0.0], [0.0, 0.0]])
    assert math.isinf(model.critical_coupling)
    assert largest_eigenvalue_symmetric([[0.0, 0.0], [0.0, 0.0]]) == 0.0


def test_euler_maruyama_step_matches_deterministic_drift_when_noise_zero():
    model = D2Network([[0.0, 1.0], [1.0, 0.0]], a=1.0, b=1.0,
                      coupling=0.5, noise=0.0, seed=42)
    result = model.step(0.1, [1.0, 2.0])
    assert result == pytest.approx([1.1, 1.7])


def test_seed_makes_trajectories_reproducible():
    weights = [[0.0, 1.0], [1.0, 0.0]]
    first = D2Network(weights, noise=0.2, seed=9).simulate(20, 0.01)
    second = D2Network(weights, noise=0.2, seed=9).simulate(20, 0.01)
    assert first == second


def test_symmetric_and_bistable_validation():
    with pytest.raises(ValueError, match="symmetric"):
        D2Network([[0.0, 1.0], [0.0, 0.0]])
    with pytest.raises(ValueError, match="positive"):
        D2Network([[0.0, 1.0], [1.0, 0.0]], a=0.0)
