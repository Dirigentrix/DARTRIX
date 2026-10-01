#!/usr/bin/env python3
"""Run a reproducible DARTRIX-D2 bistable network simulation."""

import argparse
import json
import math
import sys
from pathlib import Path

# Allow execution as `python scripts/simulate_d2.py` from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.engines.d2_network import D2Network  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=int, default=8)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--dt", type=float, default=0.01)
    parser.add_argument("--coupling", type=float, default=None,
                        help="coupling K (default: 0.8 * analytic K_c)")
    parser.add_argument("--noise", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--record-every", type=int, default=10)
    parser.add_argument("--output", type=str, default="-",
                        help="JSON output path; '-' prints to stdout")
    args = parser.parse_args()
    if args.nodes < 2:
        parser.error("--nodes must be at least 2")

    # Undirected ring: every node is coupled to its two nearest neighbors.
    weights = [[0.0] * args.nodes for _ in range(args.nodes)]
    for i in range(args.nodes):
        j = (i + 1) % args.nodes
        weights[i][j] = weights[j][i] = 1.0
    model = D2Network(weights, a=1.0, b=1.0, coupling=0.0,
                      noise=args.noise, seed=args.seed)
    kc = model.critical_coupling
    coupling = 0.8 * kc if args.coupling is None else args.coupling
    if not math.isfinite(coupling) or coupling < 0:
        parser.error("--coupling must be finite and non-negative")
    model.coupling = coupling
    # Symmetry-broken initial condition to show stochastic collective dynamics.
    initial = [(-1.0 if i % 2 else 1.0) * 0.5 for i in range(args.nodes)]
    history = model.simulate(args.steps, args.dt, initial, args.record_every)
    payload = {
        "model": "DARTRIX-D2", "nodes": args.nodes, "steps": args.steps,
        "dt": args.dt, "noise": args.noise, "seed": args.seed,
        "coupling_K": coupling, "analytic_K_c": kc,
        "coupling_ratio": coupling / kc if math.isfinite(kc) else 0.0,
        "final_mean_activity": D2Network.mean_activity(history[-1]),
        "final_polarization": D2Network.polarization(history[-1]),
        "history": history,
    }
    text = json.dumps(payload, indent=2)
    if args.output == "-":
        print(text)
    else:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print("Simulation written to {}".format(args.output))


if __name__ == "__main__":
    main()
