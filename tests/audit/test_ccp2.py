import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from audit.ccp import CallInvariant, ColdChainGuard, Context, Decision, ResultInvariant, ToolCall  # noqa: E402


class ColdChainGuardTests(unittest.TestCase):
    def setUp(self):
        self.calls = [CallInvariant('CCP2.call_budget', lambda ctx, call, st: st['calls'] <= 2)]
        self.results = [ResultInvariant('CCP2.result_ok', lambda ctx, call, res, st: res != 'bad')]

    def test_call_passes_then_quarantines(self):
        guard = ColdChainGuard(call_invariants=self.calls, escalate_after=5)
        ctx = Context(trace_id='a')
        self.assertEqual(guard.check_call(ctx, ToolCall('x')).decision, Decision.ALLOW)
        self.assertEqual(guard.check_call(ctx, ToolCall('x')).decision, Decision.ALLOW)
        r = guard.check_call(ctx, ToolCall('x'))
        self.assertEqual(r.decision, Decision.QUARANTINE)
        self.assertEqual(r.rule_id, 'CCP2.call_budget')

    def test_escalates_after_repeated_violations(self):
        guard = ColdChainGuard(call_invariants=[CallInvariant('r', lambda c, k, s: False)], escalate_after=2)
        ctx = Context(trace_id='b')
        self.assertEqual(guard.check_call(ctx, ToolCall('x')).decision, Decision.QUARANTINE)
        self.assertEqual(guard.check_call(ctx, ToolCall('x')).decision, Decision.ESCALATE)

    def test_state_is_isolated_per_trace(self):
        guard = ColdChainGuard(call_invariants=self.calls)
        for _ in range(3):
            guard.check_call(Context(trace_id='one'), ToolCall('x'))
        self.assertEqual(guard.check_call(Context(trace_id='two'), ToolCall('x')).decision, Decision.ALLOW)

    def test_result_invariant_violation(self):
        guard = ColdChainGuard(result_invariants=self.results)
        ctx = Context(trace_id='c')
        self.assertEqual(guard.check_result(ctx, ToolCall('x'), 'good').decision, Decision.ALLOW)
        r = guard.check_result(ctx, ToolCall('x'), 'bad')
        self.assertEqual(r.decision, Decision.QUARANTINE)
        self.assertEqual(r.phase, 'result')

    def test_snapshot_reflects_counts(self):
        guard = ColdChainGuard(call_invariants=self.calls)
        ctx = Context(trace_id='d')
        guard.check_call(ctx, ToolCall('x'))
        self.assertEqual(guard.snapshot(ctx)['calls'], 1)


if __name__ == '__main__':
    unittest.main()
