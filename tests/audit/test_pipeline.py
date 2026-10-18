import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from audit.ccp import (  # noqa: E402
    CallInvariant,
    ColdChainGuard,
    Context,
    Decision,
    InMemoryEscalationSink,
    InMemoryStore,
    IntakePipeline,
    MetalDetectorGuard,
    QuarantineStation,
    ResultInvariant,
    ToolCall,
)


class IntakePipelineTests(unittest.TestCase):
    def build(self, call_inv=(), result_inv=(), escalate_after=3):
        store = InMemoryStore()
        sink = InMemoryEscalationSink()
        pipeline = IntakePipeline(
            metal=MetalDetectorGuard(allowlist=['search', 'read']),
            cold=ColdChainGuard(call_invariants=call_inv, result_invariants=result_inv, escalate_after=escalate_after),
            quarantine=QuarantineStation(store=store, ttl_s=60.0),
            sink=sink,
        )
        return pipeline, store, sink

    def test_ccp1_block_is_terminal_and_not_frozen(self):
        pipeline, store, _ = self.build()
        out = pipeline.process_call(Context(trace_id='p'), ToolCall('delete_all'))
        self.assertEqual(out['decision'], Decision.BLOCK)
        self.assertEqual(out['stage'], 'CCP-1-METAL')
        self.assertIsNone(out['record_id'])
        self.assertEqual(store.items(), [])

    def test_ccp2_quarantine_freezes_record(self):
        pipeline, store, _ = self.build(call_inv=[CallInvariant('CCP2.never', lambda c, k, s: False)])
        out = pipeline.process_call(Context(trace_id='p'), ToolCall('search'))
        self.assertEqual(out['decision'], Decision.QUARANTINE)
        self.assertEqual(store.get(out['record_id'])['state'], 'FROZEN')

    def test_allowed_call_is_not_frozen(self):
        pipeline, store, _ = self.build()
        out = pipeline.process_call(Context(trace_id='p'), ToolCall('search'))
        self.assertEqual(out['decision'], Decision.ALLOW)
        self.assertIsNone(out['record_id'])
        self.assertEqual(store.items(), [])

    def test_escalate_notifies_sink(self):
        pipeline, _, sink = self.build(call_inv=[CallInvariant('x', lambda c, k, s: False)], escalate_after=1)
        out = pipeline.process_call(Context(trace_id='p'), ToolCall('search'))
        self.assertEqual(out['decision'], Decision.ESCALATE)
        self.assertEqual(sink.events[0]['reason'], 'cold_chain_escalation')

    def test_result_path_freezes_bad_result(self):
        pipeline, store, _ = self.build(result_inv=[ResultInvariant('CCP2.res', lambda c, k, r, s: r != 'bad')])
        out = pipeline.process_result(Context(trace_id='p'), ToolCall('read'), 'bad')
        self.assertEqual(out['decision'], Decision.QUARANTINE)
        self.assertEqual(store.get(out['record_id'])['state'], 'FROZEN')


if __name__ == '__main__':
    unittest.main()
