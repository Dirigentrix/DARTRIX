import os
import sys
import unittest
from dataclasses import dataclass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from audit.ccp import (  # noqa: E402
    CCP2_ID,
    Context,
    Decision,
    GuardResult,
    InMemoryEscalationSink,
    InMemoryStore,
    QuarantineStation,
    _content_hash,
    _safe,
)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


@dataclass
class Thing:
    name: str
    value: int


class SafeHashTests(unittest.TestCase):
    def test_safe_converts_dataclass_and_sets(self):
        out = _safe({'t': Thing('a', 1), 's': {2, 1}, 'd': Decision.BLOCK})
        self.assertEqual(out, {'t': {'name': 'a', 'value': 1}, 's': [1, 2], 'd': 'BLOCK'})

    def test_content_hash_is_deterministic_sha256(self):
        g = GuardResult(CCP2_ID, Decision.QUARANTINE, 'r', ['r'], 'call')
        h1 = _content_hash({'a': 1}, {'b': 2}, g)
        h2 = _content_hash({'a': 1}, {'b': 2}, g)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)


class QuarantineStationTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.store = InMemoryStore()
        self.station = QuarantineStation(
            store=self.store,
            clock=self.clock,
            ttl_s=10.0,
            revalidator=lambda payload, snapshot: payload.get('ok', False),
        )
        self.guard = GuardResult(CCP2_ID, Decision.QUARANTINE, 'CCP2.temp', ['CCP2.temp'], 'call')

    def test_freeze_stores_frozen_record(self):
        rid = self.station.freeze({'ok': True}, {'calls': 1}, self.guard, ctx=Context(trace_id='t'))
        rec = self.store.get(rid)
        self.assertEqual(rec['state'], 'FROZEN')
        self.assertEqual(rec['ccp_id'], CCP2_ID)
        self.assertEqual(rec['trace_id'], 't')
        self.assertEqual(self.station.quarantine_size, 1)

    def test_revalidate_thaws_or_rejects(self):
        ok_id = self.station.freeze({'ok': True}, {}, self.guard)
        bad_id = self.station.freeze({'ok': False}, {}, self.guard)
        self.assertEqual(self.station.revalidate(ok_id), 'THAWED')
        self.assertEqual(self.station.revalidate(bad_id), 'REJECTED')
        self.assertEqual(self.station.quarantine_size, 0)
        with self.assertRaises(ValueError):
            self.station.revalidate(ok_id)

    def test_expired_and_escalation(self):
        sink = InMemoryEscalationSink()
        rid = self.station.freeze({'ok': False}, {}, self.guard)
        self.assertEqual(self.station.expired(), [])
        self.clock.t = 11.0
        self.assertEqual(self.station.expired(), [rid])
        self.assertEqual(self.station.escalate_expired(sink), [rid])
        self.assertEqual(self.store.get(rid)['state'], 'ESCALATED')
        self.assertEqual(sink.events[0]['reason'], 'ttl_expired')
        self.assertEqual(self.station.quarantine_size, 0)

    def test_tick_records_age_and_escalates(self):
        sink = InMemoryEscalationSink()
        rid = self.station.freeze({'ok': False}, {}, self.guard)
        self.clock.t = 20.0
        self.assertEqual(self.station.tick(sink), [rid])
        self.assertEqual(len(sink.events), 1)


if __name__ == '__main__':
    unittest.main()
