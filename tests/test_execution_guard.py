import asyncio
import time
import pytest
from core.execution_guard import ExecutionGuard, ExecutionConfig, CircuitState, CircuitOpenError


def test_normal_flow_keeps_closed():
    guard = ExecutionGuard(name="basic", config=ExecutionConfig(failure_threshold=2))
    @guard
    def operation(): return "ok"
    assert operation() == "ok"
    assert guard.state == CircuitState.CLOSED
    assert guard.metrics.successful_calls == 1
    assert guard.metrics.failed_calls == 0


def test_threshold_opens_circuit():
    guard = ExecutionGuard(name="open", config=ExecutionConfig(failure_threshold=2))
    @guard
    def failing(): raise RuntimeError("failure")
    with pytest.raises(RuntimeError): failing()
    assert guard.state == CircuitState.CLOSED
    with pytest.raises(RuntimeError): failing()
    assert guard.state == CircuitState.OPEN
    with pytest.raises(CircuitOpenError) as exc_info: failing()
    assert "Obwód otwarty" in str(exc_info.value)


def test_success_resets_failure_counter():
    guard = ExecutionGuard(name="reset", config=ExecutionConfig(failure_threshold=3))
    @guard
    def sometimes_fails(fail):
        if fail: raise RuntimeError("oops")
        return "ok"
    with pytest.raises(RuntimeError): sometimes_fails(True)
    with pytest.raises(RuntimeError): sometimes_fails(True)
    assert guard._failure_count == 2
    assert sometimes_fails(False) == "ok"
    assert guard._failure_count == 0
    assert guard.state == CircuitState.CLOSED
    with pytest.raises(RuntimeError): sometimes_fails(True)
    with pytest.raises(RuntimeError): sometimes_fails(True)
    assert guard.state == CircuitState.CLOSED


def test_open_to_halfopen_to_closed():
    guard = ExecutionGuard(name="recovery", config=ExecutionConfig(failure_threshold=2, recovery_timeout=.1, half_open_max_tests=2))
    @guard
    def bad(): raise RuntimeError("down")
    @guard
    def good(): return "up"
    for _ in range(2):
        with pytest.raises(RuntimeError): bad()
    assert guard.state == CircuitState.OPEN
    time.sleep(.15)
    assert guard.state == CircuitState.HALF_OPEN
    assert good() == "up"
    assert good() == "up"
    assert guard.state == CircuitState.CLOSED


def test_halfopen_failure_reopens():
    guard = ExecutionGuard(name="relapse", config=ExecutionConfig(failure_threshold=1, recovery_timeout=.1, half_open_max_tests=2))
    @guard
    def always_bad(): raise RuntimeError("still broken")
    with pytest.raises(RuntimeError): always_bad()
    assert guard.state == CircuitState.OPEN
    time.sleep(.15)
    assert guard.state == CircuitState.HALF_OPEN
    with pytest.raises(RuntimeError): always_bad()
    assert guard.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_async_flow():
    guard = ExecutionGuard(name="async")
    @guard
    async def async_op(delay=.01):
        await asyncio.sleep(delay)
        return "async_ok"
    assert await async_op() == "async_ok"
    assert guard.state == CircuitState.CLOSED
    assert guard.metrics.successful_calls == 1


@pytest.mark.asyncio
async def test_async_failure():
    guard = ExecutionGuard(name="async_fail", config=ExecutionConfig(failure_threshold=1))
    @guard
    async def async_fail():
        await asyncio.sleep(.01)
        raise RuntimeError("async error")
    with pytest.raises(RuntimeError): await async_fail()
    assert guard.state == CircuitState.OPEN
    with pytest.raises(CircuitOpenError): await async_fail()


def test_excluded_exceptions_not_counted():
    class SafeSkip(Exception): pass
    guard = ExecutionGuard(name="exclude", config=ExecutionConfig(failure_threshold=2, exclude_exceptions=(SafeSkip,)))
    @guard
    def raise_exc(exc): raise exc
    with pytest.raises(SafeSkip): raise_exc(SafeSkip("ignored"))
    assert guard._failure_count == 0
    assert guard.state == CircuitState.CLOSED
    with pytest.raises(RuntimeError): raise_exc(RuntimeError("counted"))
    assert guard._failure_count == 1


def test_callbacks_fire_on_transitions():
    states_received = []
    guard = ExecutionGuard(name="callbacks", config=ExecutionConfig(failure_threshold=2, recovery_timeout=.1))
    guard.on_open = lambda: states_received.append("OPEN")
    guard.on_closed = lambda: states_received.append("CLOSED")
    @guard
    def fail(): raise RuntimeError("x")
    @guard
    def ok(): return "✓"
    with pytest.raises(RuntimeError): fail()
    with pytest.raises(RuntimeError): fail()
    assert "OPEN" in states_received
    time.sleep(.15)
    ok(); ok()
    assert "CLOSED" in states_received


def test_metrics_populated():
    guard = ExecutionGuard(name="metrics")
    @guard
    def fast(): return "quick"
    @guard
    def slow():
        time.sleep(.2)
        return "slow"
    fast(); slow()
    status = guard.get_status()
    assert status["metrics"]["total"] == 2
    assert status["metrics"]["successful"] == 2
    assert status["metrics"]["avg_duration_ms"] > 0
    assert status["metrics"]["last_duration_ms"] > 150


def test_reset_clears_state():
    guard = ExecutionGuard(name="reset_test", config=ExecutionConfig(failure_threshold=1))
    @guard
    def fail(): raise RuntimeError("down")
    with pytest.raises(RuntimeError): fail()
    assert guard.state == CircuitState.OPEN
    guard.reset()
    assert guard.state == CircuitState.CLOSED
    assert guard.metrics.total_calls == 0
    assert guard._failure_count == 0


def test_custom_time_provider():
    fake_time = [1000.0]
    guard = ExecutionGuard(name="time_provider", config=ExecutionConfig(failure_threshold=1, recovery_timeout=5.0))
    guard.time_provider = lambda: fake_time[0]
    @guard
    def fail(): raise RuntimeError("x")
    with pytest.raises(RuntimeError): fail()
    assert guard.state == CircuitState.OPEN
    fake_time[0] = 1004.9
    assert guard.state == CircuitState.OPEN
    fake_time[0] = 1005.0
    assert guard.state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_concurrent_access_safe():
    guard = ExecutionGuard(name="concurrent", config=ExecutionConfig(failure_threshold=5))
    @guard
    async def flaky(i):
        if i % 3 == 0: raise RuntimeError(f"fail {i}")
        return i
    results = await asyncio.gather(*(flaky(i) for i in range(10)), return_exceptions=True)
    assert guard.metrics.total_calls == 10
    transitions = [t for t in guard.metrics.state_transitions if t["to"] == "open"]
    assert len(transitions) <= 1
