'''CCP audit architecture for DARTRIX.

CCP-1 MetalDetectorGuard: stateless gate with terminal BLOCK.
CCP-2 ColdChainGuard: stateful, continuous call and result invariants.
Szokowka QuarantineStation: freezes flagged payloads, revalidates them and escalates expired records.
IntakePipeline: CCP-1, then CCP-2, then quarantine.

Standard library only. No third-party HTTP clients.
'''

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, Tuple
from uuid import uuid4

CCP1_ID = 'CCP-1-METAL'
CCP2_ID = 'CCP-2-COLDCHAIN'
TRACER_NAME = 'dartrix.audit'


# ---------------------------------------------------------------------------
# Metrics abstractions
# ---------------------------------------------------------------------------

def _label_key(labels: Dict[str, Any]) -> Tuple[Tuple[str, str], ...]:
    return tuple(sorted((str(k), str(v)) for k, v in labels.items()))


class Meter:
    '''Base meter. Instruments report every observation through record().

    The base implementation discards observations. Subclasses (tests, OTel)
    override record() to receive them.
    '''

    def __init__(self) -> None:
        self._instruments: Dict[Tuple[str, str], Any] = {}

    def record(self, name: str, kind: str, value: float, labels: Dict[str, Any]) -> None:
        return None

    def _instrument(self, key: Tuple[str, str], factory: Callable[[], Any]) -> Any:
        if key not in self._instruments:
            self._instruments[key] = factory()
        return self._instruments[key]

    def counter(self, name: str) -> 'Counter':
        return self._instrument(('counter', name), lambda: Counter(name, self))

    def histogram(self, name: str) -> 'Histogram':
        return self._instrument(('histogram', name), lambda: Histogram(name, self))

    def gauge(self, name: str) -> 'Gauge':
        return self._instrument(('gauge', name), lambda: Gauge(name, self))


class NoopMeter(Meter):
    '''Meter that accepts all observations and keeps nothing external.'''


class Counter:
    '''Monotonic counter, keyed by labels.'''

    def __init__(self, name: str, meter: Meter) -> None:
        self.name = name
        self._meter = meter
        self.values: Dict[Tuple[Tuple[str, str], ...], float] = defaultdict(float)

    def add(self, value: float = 1, **labels: Any) -> None:
        if value < 0:
            raise ValueError('counter cannot decrease')
        self.values[_label_key(labels)] += value
        self._meter.record(self.name, 'counter', value, labels)

    def total(self, **labels: Any) -> float:
        return self.values[_label_key(labels)]


class Gauge:
    '''Up/down value, used for quarantine_size.'''

    def __init__(self, name: str, meter: Meter) -> None:
        self.name = name
        self._meter = meter
        self.value: float = 0.0

    def add(self, delta: float, **labels: Any) -> None:
        self.value += delta
        self._meter.record(self.name, 'gauge', delta, labels)


class Histogram:
    '''Distribution of observations.'''

    def __init__(self, name: str, meter: Meter) -> None:
        self.name = name
        self._meter = meter
        self.observations: List[float] = []

    def record(self, value: float, **labels: Any) -> None:
        self.observations.append(float(value))
        self._meter.record(self.name, 'histogram', float(value), labels)


class _OTelMeter(Meter):
    '''Forwards observations to an OpenTelemetry meter, creating instruments lazily.'''

    def __init__(self, otel_meter_obj: Any) -> None:
        super().__init__()
        self._otel = otel_meter_obj
        self._otel_instruments: Dict[Tuple[str, str], Any] = {}

    def record(self, name: str, kind: str, value: float, labels: Dict[str, Any]) -> None:
        key = (kind, name)
        inst = self._otel_instruments.get(key)
        if inst is None:
            if kind == 'counter':
                inst = self._otel.create_counter(name)
            elif kind == 'histogram':
                inst = self._otel.create_histogram(name)
            else:
                inst = self._otel.create_up_down_counter(name)
            self._otel_instruments[key] = inst
        attrs = {str(k): str(v) for k, v in labels.items()}
        if kind == 'histogram':
            inst.record(value, attributes=attrs)
        else:
            inst.add(value, attributes=attrs)


def otel_meter(name: str = TRACER_NAME) -> Meter:
    '''Return an OpenTelemetry-backed Meter when the SDK API is importable, otherwise a NoopMeter.'''
    try:
        from opentelemetry import metrics as otel_metrics
    except ImportError:
        return NoopMeter()
    return _OTelMeter(otel_metrics.get_meter(name))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Decision(str, Enum):
    BLOCK = 'BLOCK'
    ALLOW = 'ALLOW'
    QUARANTINE = 'QUARANTINE'
    ESCALATE = 'ESCALATE'


@dataclass
class Context:
    trace_id: str = ''
    tenant: str = 'default'
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0


@dataclass
class GuardResult:
    ccp_id: str
    decision: Decision
    rule_id: Optional[str] = None
    violations: List[str] = field(default_factory=list)
    phase: Optional[str] = None

    @property
    def allowed(self) -> bool:
        return self.decision == Decision.ALLOW


@dataclass
class CallInvariant:
    rule_id: str
    predicate: Callable[[Context, ToolCall, Dict[str, Any]], bool]


@dataclass
class ResultInvariant:
    rule_id: str
    predicate: Callable[[Context, ToolCall, Any, Dict[str, Any]], bool]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(obj: Any) -> Any:
    '''Convert an arbitrary object into a JSON-serializable structure.'''
    if isinstance(obj, Enum):
        return _safe(obj.value)
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else str(obj)
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _safe(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, dict):
        return {str(k): _safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        items = [_safe(v) for v in obj]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(obj, (bytes, bytearray)):
        return bytes(obj).hex()
    return str(obj)


def _content_hash(payload: Any, snapshot: Any, guard_result: Any) -> str:
    '''Deterministic SHA-256 over payload, snapshot and guard result.'''
    material = {
        'payload': _safe(payload),
        'snapshot': _safe(snapshot),
        'guard_result': _safe(guard_result),
    }
    blob = json.dumps(material, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


def _span(name: str, **attributes: Any):
    '''OpenTelemetry span context manager, or a no-op when OTel is not installed.'''
    try:
        from opentelemetry import trace
    except ImportError:
        return nullcontext()
    attrs = {
        k: (v if isinstance(v, (str, bool, int, float)) else str(v))
        for k, v in attributes.items()
        if v is not None
    }
    return trace.get_tracer(TRACER_NAME).start_as_current_span(name, attributes=attrs)


# ---------------------------------------------------------------------------
# CCP-1: MetalDetectorGuard (stateless, terminal BLOCK)
# ---------------------------------------------------------------------------

class MetalDetectorGuard:
    ccp_id = CCP1_ID

    PII_PATTERNS = {
        'email': re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
        'phone': re.compile(r'(?<!\d)(?:\+\d{1,3}[ -]?)?\d{3}[ -]?\d{3}[ -]?\d{3}(?!\d)'),
        'pesel': re.compile(r'(?<!\d)\d{11}(?!\d)'),
    }

    def __init__(
        self,
        allowlist: Iterable[str],
        schema: Optional[Dict[str, Dict[str, Any]]] = None,
        max_cost_usd: float = 1.0,
        meter: Optional[Meter] = None,
    ) -> None:
        self.allowlist = frozenset(allowlist)
        self.schema = dict(schema or {})
        self.max_cost_usd = float(max_cost_usd)
        self.meter = meter if meter is not None else NoopMeter()

    def check(self, ctx: Optional[Context], call: ToolCall) -> GuardResult:
        self.meter.counter('ccp_checks_total').add(1, ccp=self.ccp_id)
        violations: List[str] = []
        rule_id: Optional[str] = None

        def fail(rule: str, message: str) -> None:
            nonlocal rule_id
            if rule_id is None:
                rule_id = rule
            violations.append(message)

        if call.name not in self.allowlist:
            fail('CCP1.allowlist_tools', f'allowlist_tools:{call.name}')

        spec = self.schema.get(call.name)
        if spec is not None:
            for name in spec.get('required', ()):
                if name not in call.args:
                    fail('CCP1.schema', f'schema:missing:{name}')
            for name, typ in spec.get('types', {}).items():
                if name in call.args and not isinstance(call.args[name], typ):
                    fail('CCP1.schema', f'schema:type:{name}')

        if call.cost_usd > self.max_cost_usd:
            fail('CCP1.max_cost_usd', 'max_cost_usd')

        text = json.dumps(_safe(call.args), ensure_ascii=False, sort_keys=True)
        for kind, pattern in self.PII_PATTERNS.items():
            if pattern.search(text):
                fail('CCP1.pii', f'pii:{kind}')

        if violations:
            self.meter.counter('ccp_blocked_total').add(1, ccp=self.ccp_id)
            return GuardResult(self.ccp_id, Decision.BLOCK, rule_id, violations)
        return GuardResult(self.ccp_id, Decision.ALLOW)


# ---------------------------------------------------------------------------
# CCP-2: ColdChainGuard (stateful, continuous)
# ---------------------------------------------------------------------------

class ColdChainGuard:
    ccp_id = CCP2_ID

    def __init__(
        self,
        call_invariants: Iterable[CallInvariant] = (),
        result_invariants: Iterable[ResultInvariant] = (),
        meter: Optional[Meter] = None,
        escalate_after: int = 3,
    ) -> None:
        self.call_invariants = list(call_invariants)
        self.result_invariants = list(result_invariants)
        self.meter = meter if meter is not None else NoopMeter()
        self.escalate_after = int(escalate_after)
        self._traces: Dict[str, Dict[str, Any]] = {}

    def _trace_state(self, ctx: Optional[Context]) -> Dict[str, Any]:
        key = ctx.trace_id if ctx is not None else ''
        if key not in self._traces:
            self._traces[key] = {'calls': 0, 'results': 0, 'violations': 0, 'last_rule': None}
        return self._traces[key]

    def snapshot(self, ctx: Optional[Context]) -> Dict[str, Any]:
        return dict(self._trace_state(ctx))

    def _verdict(self, ctx: Optional[Context], phase: str, failed_rules: List[str]) -> GuardResult:
        state = self._trace_state(ctx)
        state['violations'] += 1
        state['last_rule'] = failed_rules[0]
        self.meter.counter('ccp_quarantine_total').add(1, ccp=self.ccp_id, phase=phase)
        decision = Decision.ESCALATE if state['violations'] >= self.escalate_after else Decision.QUARANTINE
        return GuardResult(self.ccp_id, decision, failed_rules[0], list(failed_rules), phase)

    def check_call(self, ctx: Optional[Context], call: ToolCall) -> GuardResult:
        state = self._trace_state(ctx)
        state['calls'] += 1
        self.meter.counter('ccp_checks_total').add(1, ccp=self.ccp_id, phase='call')
        failed = [inv.rule_id for inv in self.call_invariants if not inv.predicate(ctx, call, state)]
        if failed:
            return self._verdict(ctx, 'call', failed)
        return GuardResult(self.ccp_id, Decision.ALLOW, phase='call')

    def check_result(self, ctx: Optional[Context], call: ToolCall, result: Any) -> GuardResult:
        state = self._trace_state(ctx)
        state['results'] += 1
        self.meter.counter('ccp_checks_total').add(1, ccp=self.ccp_id, phase='result')
        failed = [inv.rule_id for inv in self.result_invariants if not inv.predicate(ctx, call, result, state)]
        if failed:
            return self._verdict(ctx, 'result', failed)
        return GuardResult(self.ccp_id, Decision.ALLOW, phase='result')


# ---------------------------------------------------------------------------
# Storage and escalation
# ---------------------------------------------------------------------------

class RecordStore(Protocol):
    def put(self, record_id: str, record: Dict[str, Any]) -> None: ...
    def get(self, record_id: str) -> Dict[str, Any]: ...
    def update(self, record_id: str, **fields: Any) -> None: ...
    def items(self) -> List[Tuple[str, Dict[str, Any]]]: ...


class InMemoryStore:
    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}

    def put(self, record_id: str, record: Dict[str, Any]) -> None:
        if record_id in self._data:
            raise KeyError(f'record already exists: {record_id}')
        self._data[record_id] = dict(record)

    def get(self, record_id: str) -> Dict[str, Any]:
        return self._data[record_id]

    def update(self, record_id: str, **fields: Any) -> None:
        self._data[record_id].update(fields)

    def items(self) -> List[Tuple[str, Dict[str, Any]]]:
        return list(self._data.items())


class EscalationSink(Protocol):
    def escalate(self, record_id: str, record: Dict[str, Any], reason: str) -> None: ...


class InMemoryEscalationSink:
    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def escalate(self, record_id: str, record: Dict[str, Any], reason: str) -> None:
        self.events.append({'record_id': record_id, 'reason': reason, 'record': dict(record)})


# ---------------------------------------------------------------------------
# Szokowka: QuarantineStation
# ---------------------------------------------------------------------------

class QuarantineStation:
    FROZEN = 'FROZEN'
    THAWED = 'THAWED'
    REJECTED = 'REJECTED'
    ESCALATED = 'ESCALATED'

    def __init__(
        self,
        store: Optional[RecordStore] = None,
        clock: Optional[Callable[[], float]] = None,
        ttl_s: float = 300.0,
        revalidator: Optional[Callable[[Any, Any], bool]] = None,
        meter: Optional[Meter] = None,
    ) -> None:
        self.store: RecordStore = store if store is not None else InMemoryStore()
        self.clock: Callable[[], float] = clock if clock is not None else time.monotonic
        self.ttl_s = float(ttl_s)
        self.revalidator = revalidator
        self.meter = meter if meter is not None else NoopMeter()
        self._size_gauge = self.meter.gauge('quarantine_size')

    @property
    def quarantine_size(self) -> float:
        return self._size_gauge.value

    def freeze(
        self,
        payload: Any,
        snapshot: Any,
        guard_result: GuardResult,
        ctx: Optional[Context] = None,
    ) -> str:
        record_id = uuid4().hex
        with _span('szokowka.freeze', ccp_id=guard_result.ccp_id, rule_id=guard_result.rule_id, record_id=record_id):
            record = {
                'state': self.FROZEN,
                'payload': _safe(payload),
                'snapshot': _safe(snapshot),
                'violations': _safe(guard_result.violations),
                'rule_id': guard_result.rule_id,
                'ccp_id': guard_result.ccp_id,
                'trace_id': ctx.trace_id if ctx is not None else '',
                'content_hash': _content_hash(payload, snapshot, guard_result),
                'frozen_at_mono': float(self.clock()),
                'ttl_s': self.ttl_s,
            }
            self.store.put(record_id, record)
            self.meter.counter('freeze_total').add(1)
            self._size_gauge.add(1)
        return record_id

    def revalidate(self, record_id: str, revalidator: Optional[Callable[[Any, Any], bool]] = None) -> str:
        with _span('szokowka.revalidate', record_id=record_id):
            rec = self.store.get(record_id)
            if rec['state'] != self.FROZEN:
                raise ValueError(f'record {record_id} is not FROZEN: {rec["state"]}')
            fn = revalidator if revalidator is not None else self.revalidator
            if fn is None:
                raise ValueError('no revalidator configured')
            ok = bool(fn(rec['payload'], rec['snapshot']))
            new_state = self.THAWED if ok else self.REJECTED
            self.store.update(record_id, state=new_state, revalidated_at_mono=float(self.clock()))
            self._size_gauge.add(-1)
            self.meter.counter('thawed_total' if ok else 'rejected_total').add(1)
        return new_state

    def expired(self) -> List[str]:
        now = float(self.clock())
        return [
            rid for rid, rec in self.store.items()
            if rec['state'] == self.FROZEN and now - rec['frozen_at_mono'] > rec['ttl_s']
        ]

    def escalate_expired(self, sink: EscalationSink) -> List[str]:
        escalated: List[str] = []
        for rid in self.expired():
            rec = self.store.get(rid)
            with _span('szokowka.ttl_expired', record_id=rid, ccp_id=rec.get('ccp_id')):
                sink.escalate(rid, rec, reason='ttl_expired')
                self.store.update(rid, state=self.ESCALATED)
                self._size_gauge.add(-1)
                self.meter.counter('szokowka_ttl_expired_total').add(1)
            escalated.append(rid)
        return escalated

    def tick(self, sink: EscalationSink) -> List[str]:
        now = float(self.clock())
        ages = [
            now - rec['frozen_at_mono']
            for _, rec in self.store.items()
            if rec['state'] == self.FROZEN
        ]
        if ages:
            self.meter.histogram('quarantine_oldest_age_s').record(max(ages))
        return self.escalate_expired(sink)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class IntakePipeline:
    '''CCP-1 gate, then CCP-2 call check, then quarantine for QUARANTINE and ESCALATE verdicts.'''

    def __init__(
        self,
        metal: MetalDetectorGuard,
        cold: ColdChainGuard,
        quarantine: QuarantineStation,
        sink: Optional[EscalationSink] = None,
    ) -> None:
        self.metal = metal
        self.cold = cold
        self.quarantine = quarantine
        self.sink = sink

    def _freeze_if_needed(self, ctx: Optional[Context], payload: Any, result: GuardResult) -> Optional[str]:
        if result.decision not in (Decision.QUARANTINE, Decision.ESCALATE):
            return None
        snapshot = self.cold.snapshot(ctx)
        record_id = self.quarantine.freeze(payload, snapshot, result, ctx=ctx)
        if result.decision == Decision.ESCALATE and self.sink is not None:
            self.sink.escalate(record_id, self.quarantine.store.get(record_id), reason='cold_chain_escalation')
        return record_id

    def process_call(self, ctx: Optional[Context], call: ToolCall) -> Dict[str, Any]:
        verdict = self.metal.check(ctx, call)
        if verdict.decision == Decision.BLOCK:
            return {'decision': Decision.BLOCK, 'stage': CCP1_ID, 'record_id': None, 'violations': verdict.violations}
        result = self.cold.check_call(ctx, call)
        record_id = self._freeze_if_needed(ctx, {'call': call}, result)
        return {'decision': result.decision, 'stage': CCP2_ID, 'record_id': record_id, 'violations': result.violations}

    def process_result(self, ctx: Optional[Context], call: ToolCall, result_value: Any) -> Dict[str, Any]:
        result = self.cold.check_result(ctx, call, result_value)
        record_id = self._freeze_if_needed(ctx, {'call': call, 'result': result_value}, result)
        return {'decision': result.decision, 'stage': CCP2_ID, 'record_id': record_id, 'violations': result.violations}
