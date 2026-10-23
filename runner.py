"""Deterministic event-loop runner for DARTRIX.

Flow per event: Event -> SOIF log (SoifTimeline) -> Node state update with
clamping -> output (one JSON line per step). Standard library only.

Usage:
    python3 runner.py                       # built-in demo stream
    python3 runner.py --events ev.jsonl     # one JSON event per line
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from soif_timeline import SoifTimeline  # noqa: E402


@dataclass(frozen=True)
class Event:
    kind: str
    node: str
    delta: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Event":
        return Event(kind=str(data["kind"]), node=str(data["node"]), delta=float(data["delta"]))


class Node:
    """A stateful component whose value is always kept within [lo, hi]."""

    def __init__(self, name: str, value: float = 0.0, lo: float = 0.0, hi: float = 1.0):
        if lo > hi:
            raise ValueError(f"node {name}: lo ({lo}) > hi ({hi})")
        self.name = name
        self.lo = lo
        self.hi = hi
        self.value = max(lo, min(hi, value))

    def apply(self, delta: float) -> bool:
        """Apply delta with clamping. Returns True if the result was clamped."""
        raw = self.value + delta
        self.value = max(self.lo, min(self.hi, raw))
        return self.value != raw


class Runner:
    """Stepped, deterministic runner. Same inputs always produce the same state transitions."""

    def __init__(
        self,
        nodes: Iterable[Node],
        timeline: SoifTimeline,
        emit: Optional[Callable[[str], None]] = None,
    ):
        self.nodes: Dict[str, Node] = {}
        for node in nodes:
            if node.name in self.nodes:
                raise ValueError(f"duplicate node name: {node.name}")
            self.nodes[node.name] = node
        self.timeline = timeline
        self.emit = emit if emit is not None else print
        self.tick = 0

    def step(self, event: Event) -> Dict[str, Any]:
        if event.node not in self.nodes:
            raise KeyError(f"unknown node: {event.node}")
        self.tick += 1
        node = self.nodes[event.node]

        event_id = self.timeline.log_event({
            "module": "Runner",
            "type": "EVENT",
            "napięcie": 0.0,
            "mode": "STEP",
            "details": {"tick": self.tick, "kind": event.kind, "node": event.node, "delta": event.delta},
        })

        before = node.value
        clamped = node.apply(event.delta)

        self.timeline.log_event({
            "module": node.name,
            "type": "STATE_UPDATE",
            "napięcie": node.value,
            "mode": "STEP",
            "details": {
                "tick": self.tick,
                "event_id": event_id,
                "before": before,
                "after": node.value,
                "clamped": clamped,
            },
        })

        record = {
            "tick": self.tick,
            "event_id": event_id,
            "kind": event.kind,
            "node": node.name,
            "delta": event.delta,
            "before": before,
            "after": node.value,
            "clamped": clamped,
        }
        self.emit(json.dumps(record, sort_keys=True))
        return record

    def run(self, events: Iterable[Event]) -> List[Dict[str, Any]]:
        return [self.step(event) for event in events]

    def snapshot(self) -> Dict[str, float]:
        return {name: node.value for name, node in sorted(self.nodes.items())}


DEMO_NODES = (
    ("sync", 0.5, 0.0, 1.0),
    ("load", 0.2, 0.0, 1.0),
)

DEMO_EVENTS = (
    {"kind": "COMM", "node": "sync", "delta": 0.3},
    {"kind": "DATA", "node": "load", "delta": 0.5},
    {"kind": "SYSTEM", "node": "sync", "delta": 0.4},
    {"kind": "DATA", "node": "load", "delta": -0.9},
)


def build_demo_runner(log_path: str, emit: Optional[Callable[[str], None]] = None) -> Runner:
    nodes = [Node(name, value, lo, hi) for name, value, lo, hi in DEMO_NODES]
    return Runner(nodes, SoifTimeline(log_path), emit=emit)


def load_events(path: str) -> List[Event]:
    events = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                events.append(Event.from_dict(json.loads(line)))
    return events


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="DARTRIX deterministic event runner")
    parser.add_argument("--events", help="JSONL file with events (default: built-in demo)")
    parser.add_argument("--log", default=os.path.join(ROOT, "logs", "soif_timeline.jsonl"),
                        help="SOIF timeline JSONL output path")
    args = parser.parse_args(argv)

    runner = build_demo_runner(args.log)
    events = load_events(args.events) if args.events else [Event.from_dict(e) for e in DEMO_EVENTS]
    runner.run(events)
    print(json.dumps({"final": runner.snapshot()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
