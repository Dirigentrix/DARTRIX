import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from audit.ccp import Context, Decision, MetalDetectorGuard, ToolCall  # noqa: E402


class MetalDetectorGuardTests(unittest.TestCase):
    def setUp(self):
        self.guard = MetalDetectorGuard(
            allowlist=['search', 'read'],
            schema={'search': {'required': ['query'], 'types': {'query': str}}},
            max_cost_usd=0.5,
        )
        self.ctx = Context(trace_id='t')

    def test_allowed_call_passes(self):
        r = self.guard.check(self.ctx, ToolCall('search', {'query': 'milk'}, cost_usd=0.1))
        self.assertEqual(r.decision, Decision.ALLOW)
        self.assertTrue(r.allowed)
        self.assertEqual(r.violations, [])

    def test_tool_not_in_allowlist_blocks(self):
        r = self.guard.check(self.ctx, ToolCall('delete_all'))
        self.assertEqual(r.decision, Decision.BLOCK)
        self.assertEqual(r.rule_id, 'CCP1.allowlist_tools')

    def test_missing_required_field_blocks(self):
        r = self.guard.check(self.ctx, ToolCall('search', {}))
        self.assertEqual(r.decision, Decision.BLOCK)
        self.assertIn('schema:missing:query', r.violations)

    def test_wrong_type_blocks(self):
        r = self.guard.check(self.ctx, ToolCall('search', {'query': 42}))
        self.assertIn('schema:type:query', r.violations)

    def test_cost_over_limit_blocks(self):
        r = self.guard.check(self.ctx, ToolCall('read', {}, cost_usd=0.9))
        self.assertEqual(r.rule_id, 'CCP1.max_cost_usd')

    def test_pii_blocks_without_leaking_value(self):
        r = self.guard.check(self.ctx, ToolCall('search', {'query': 'jan.kowalski@example.com'}))
        self.assertEqual(r.decision, Decision.BLOCK)
        self.assertIn('pii:email', r.violations)
        self.assertFalse(any('example.com' in v for v in r.violations))

    def test_stateless(self):
        call = ToolCall('search', {'query': 'x'})
        first = self.guard.check(self.ctx, call)
        second = self.guard.check(self.ctx, call)
        self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()
