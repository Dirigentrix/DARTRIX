import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from audit.ccp import (  # noqa: E402
    CCP1_ID,
    CCP2_ID,
    CallInvariant,
    ColdChainGuard,
    Context,
    Decision,
    Meter,
    MetalDetectorGuard,
    NoopMeter,
    ResultInvariant,
    ToolCall,
    otel_meter,
)


class RecordingMeter(Meter):
    def __init__(self):
        super().__init__()
        self.events = []

    def record(self, name, kind, value, labels):
        self.events.append((name, kind, value, dict(labels)))

    def total(self, name, **labels):
        return sum(
            v for n, k, v, lb in self.events
            if n == name and k == 'counter' and all(lb.get(a) == b for a, b in labels.items())
        )

    def names(self):
        return {n for n, _, _, _ in self.events}


class MeterTests(unittest.TestCase):
    def test_counter_accumulates_per_labels(self):
        m = RecordingMeter()
        c = m.counter('x')
        c.add(1, ccp='A')
        c.add(2, ccp='A')
        c.add(5, ccp='B')
        self.assertEqual(c.total(ccp='A'), 3)
        self.assertEqual(m.total('x', ccp='B'), 5)

    def test_counter_rejects_negative(self):
        with self.assertRaises(ValueError):
            RecordingMeter().counter('x').add(-1)

    def test_histogram_records(self):
        m = RecordingMeter()
        m.histogram('h').record(1.5)
        self.assertIn('h', m.names())
        self.assertEqual(m.events[-1][2], 1.5)

    def test_noop_meter_accepts_everything(self):
        n = NoopMeter()
        n.counter('a').add(1, ccp='x')
        n.histogram('b').record(2.0)
        n.gauge('g').add(-1)

    def test_otel_meter_returns_meter(self):
        m = otel_meter('test')
        self.assertIsInstance(m, Meter)
        m.counter('c').add(1, ccp='x')


class OtelMetricEmissionTests(unittest.TestCase):
    def test_ccp1_emits_checks_and_blocks(self):
        m = RecordingMeter()
        guard = MetalDetectorGuard(allowlist=['search'], meter=m)
        result = guard.check(Context(trace_id='t1'), ToolCall(name='delete_all'))
        self.assertEqual(result.decision, Decision.BLOCK)
        self.assertEqual(m.total('ccp_checks_total', ccp=CCP1_ID), 1)
        self.assertEqual(m.total('ccp_blocked_total', ccp=CCP1_ID), 1)

    def test_ccp1_does_not_emit_quarantine(self):
        m = RecordingMeter()
        guard = MetalDetectorGuard(allowlist=['search'], meter=m)
        guard.check(Context(trace_id='t1'), ToolCall(name='search'))
        guard.check(Context(trace_id='t1'), ToolCall(name='delete_all'))
        self.assertNotIn('ccp_quarantine_total', m.names())

    def test_ccp2_emits_phase_in_metrics(self):
        m = RecordingMeter()
        inv = [CallInvariant('CCP2.temp', lambda ctx, call, st: False)]
        guard = ColdChainGuard(call_invariants=inv, meter=m)
        result = guard.check_call(Context(trace_id='t2'), ToolCall(name='search'))
        self.assertEqual(result.decision, Decision.QUARANTINE)
        self.assertEqual(result.phase, 'call')
        self.assertEqual(m.total('ccp_quarantine_total', ccp=CCP2_ID, phase='call'), 1)
        self.assertEqual(m.total('ccp_checks_total', ccp=CCP2_ID, phase='call'), 1)

    def test_ccp2_result_phase_metrics(self):
        m = RecordingMeter()
        res_inv = [ResultInvariant('CCP2.result_temp', lambda ctx, call, res, st: res.get('temp', 0) <= 4)]
        guard = ColdChainGuard(result_invariants=res_inv, meter=m)
        result = guard.check_result(Context(trace_id='t3'), ToolCall(name='read'), {'temp': 9})
        self.assertEqual(result.phase, 'result')
        self.assertEqual(m.total('ccp_quarantine_total', ccp=CCP2_ID, phase='result'), 1)
        self.assertEqual(m.total('ccp_quarantine_total', ccp=CCP2_ID, phase='call'), 0)


if __name__ == '__main__':
    unittest.main()
