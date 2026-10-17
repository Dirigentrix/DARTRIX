"""Dual Execution and Reasoning Integrity engine with OpenTelemetry.

Execution Integrity: guardrails, OTel tracing of tool calls, and reconciliation
between declared actions and recorded spans.

Reasoning Integrity: evidence store, claim extraction, claim validation,
confidence ledger, and a reasoning.validation span carrying claim counters.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

SERVICE_NAME = "dartrix-audit"
NEGATION_TOKENS = (" not ", " no ", " never ", " nie ", " brak ")


# ---------------------------------------------------------------------------
# Execution Integrity
# ---------------------------------------------------------------------------

class GuardrailViolation(Exception):
    pass


class Guardrails:
    """Deterministic checks applied before a tool call is allowed to run."""

    def __init__(self, allowed_tools: List[str], max_calls: int = 50):
        self.allowed_tools = set(allowed_tools)
        self.max_calls = max_calls
        self.calls = 0

    def check(self, tool_name: str) -> None:
        if tool_name not in self.allowed_tools:
            raise GuardrailViolation(f"tool not allowed: {tool_name}")
        if self.calls >= self.max_calls:
            raise GuardrailViolation(f"call budget exceeded: {self.max_calls}")
        self.calls += 1


class ExecutionTracer:
    """Wraps an OpenTelemetry tracer with an in-memory exporter for reconciliation."""

    def __init__(self) -> None:
        self.exporter = InMemorySpanExporter()
        provider = TracerProvider(
            resource=Resource.create({"service.name": SERVICE_NAME})
        )
        provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.provider = provider
        self.tracer = provider.get_tracer("dartrix.audit.execution")

    def run_tool(self, guardrails: Guardrails, tool_name: str, fn, *args, **kwargs) -> Any:
        guardrails.check(tool_name)
        with self.tracer.start_as_current_span(f"tool.{tool_name}") as span:
            span.set_attribute("tool.name", tool_name)
            try:
                result = fn(*args, **kwargs)
                span.set_attribute("tool.status", "ok")
                return result
            except Exception as exc:
                span.set_attribute("tool.status", "error")
                span.record_exception(exc)
                raise

    def tool_spans(self) -> List[str]:
        names = []
        for span in self.exporter.get_finished_spans():
            name = span.attributes.get("tool.name")
            if name:
                names.append(name)
        return names


@dataclass
class ReconciliationResult:
    matched: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    unexpected: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.unexpected


class ExecutionReconciler:
    """Checks that declared actions match the tool spans recorded in telemetry."""

    def __init__(self, tracer: ExecutionTracer) -> None:
        self.tracer = tracer

    def reconcile(self, declared_actions: List[str]) -> ReconciliationResult:
        recorded = self.tracer.tool_spans()
        remaining = list(recorded)
        result = ReconciliationResult()
        for action in declared_actions:
            if action in remaining:
                remaining.remove(action)
                result.matched.append(action)
            else:
                result.missing.append(action)
        result.unexpected = remaining
        return result


# ---------------------------------------------------------------------------
# Reasoning Integrity
# ---------------------------------------------------------------------------

@dataclass
class Evidence:
    tool: str
    key: str
    value: str


class EvidenceStore:
    """Collects tool outputs as atomic facts for later claim checking."""

    def __init__(self) -> None:
        self.items: List[Evidence] = []

    def add(self, tool: str, key: str, value: Any) -> None:
        self.items.append(Evidence(tool=tool, key=key, value=str(value)))

    def add_result(self, tool: str, result: Dict[str, Any]) -> None:
        for key, value in result.items():
            self.add(tool, str(key), value)


class ClaimExtractor:
    """Splits model output into atomic claims, one per sentence."""

    _SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

    def extract(self, text: str) -> List[str]:
        parts = [p.strip() for p in self._SPLIT.split(text or "")]
        return [p for p in parts if p]


@dataclass
class ClaimVerdict:
    claim: str
    status: str  # verified | unsupported | contradicted
    evidence: Optional[Evidence] = None


class ClaimValidator:
    """Matches claims against evidence.

    A claim is verified when an evidence value appears in it and the claim
    does not negate it. It is contradicted when an evidence value appears in
    the claim together with a negation token. Otherwise it is unsupported.
    """

    def __init__(self, store: EvidenceStore) -> None:
        self.store = store

    def validate(self, claim: str) -> ClaimVerdict:
        lowered = f" {claim.lower()} "
        for ev in self.store.items:
            value = ev.value.lower()
            if not value or value not in lowered:
                continue
            if any(tok in lowered for tok in NEGATION_TOKENS):
                return ClaimVerdict(claim, "contradicted", ev)
            return ClaimVerdict(claim, "verified", ev)
        return ClaimVerdict(claim, "unsupported", None)


class ConfidenceLedger:
    """Records every verdict and computes a deterministic reasoning score."""

    def __init__(self) -> None:
        self.entries: List[ClaimVerdict] = []

    def record(self, verdict: ClaimVerdict) -> None:
        self.entries.append(verdict)

    def counts(self) -> Dict[str, int]:
        out = {"total": len(self.entries), "verified": 0, "unsupported": 0, "contradicted": 0}
        for entry in self.entries:
            out[entry.status] += 1
        return out

    def score(self) -> float:
        c = self.counts()
        if c["total"] == 0:
            return 0.0
        penalty = c["contradicted"] * 1.0 + c["unsupported"] * 0.5
        return max(0.0, round(1.0 - penalty / c["total"], 4))


class ReasoningValidator:
    """Runs extraction, validation and scoring inside the reasoning.validation span."""

    def __init__(self, tracer: trace.Tracer, store: EvidenceStore) -> None:
        self.tracer = tracer
        self.store = store
        self.extractor = ClaimExtractor()
        self.validator = ClaimValidator(store)
        self.ledger = ConfidenceLedger()

    def validate_output(self, text: str) -> Dict[str, Any]:
        with self.tracer.start_as_current_span("reasoning.validation") as span:
            for claim in self.extractor.extract(text):
                self.ledger.record(self.validator.validate(claim))
            counts = self.ledger.counts()
            score = self.ledger.score()
            span.set_attribute("claims.total", counts["total"])
            span.set_attribute("claims.verified", counts["verified"])
            span.set_attribute("claims.unsupported", counts["unsupported"])
            span.set_attribute("claims.contradicted", counts["contradicted"])
            span.set_attribute("reasoning.score", score)
        return {"score": score, **counts}


# ---------------------------------------------------------------------------
# Engine facade
# ---------------------------------------------------------------------------

class IntegrityEngine:
    def __init__(self, allowed_tools: List[str], max_calls: int = 50) -> None:
        self.execution = ExecutionTracer()
        self.guardrails = Guardrails(allowed_tools, max_calls)
        self.reconciler = ExecutionReconciler(self.execution)
        self.evidence = EvidenceStore()
        self.reasoning = ReasoningValidator(self.execution.tracer, self.evidence)

    def call_tool(self, tool_name: str, fn, *args, **kwargs) -> Any:
        result = self.execution.run_tool(self.guardrails, tool_name, fn, *args, **kwargs)
        if isinstance(result, dict):
            self.evidence.add_result(tool_name, result)
        return result


def _demo() -> None:
    engine = IntegrityEngine(allowed_tools=["get_price", "get_status"])

    def get_price() -> Dict[str, Any]:
        return {"asset": "ACME", "price": "42.10"}

    def get_status() -> Dict[str, Any]:
        return {"service": "api", "state": "healthy"}

    engine.call_tool("get_price", get_price)
    engine.call_tool("get_status", get_status)

    recon = engine.reconciler.reconcile(["get_price", "get_status", "send_report"])
    print("reconciliation matched:", recon.matched)
    print("reconciliation missing:", recon.missing)
    print("reconciliation unexpected:", recon.unexpected)

    output = (
        "ACME trades at 42.10. The service is healthy. "
        "The price is not 99.00. Volume was high."
    )
    summary = engine.reasoning.validate_output(output)
    print("reasoning summary:", summary)


if __name__ == "__main__":
    _demo()
