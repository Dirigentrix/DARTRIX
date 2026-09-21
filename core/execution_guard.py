from dataclasses import dataclass, field
from enum import Enum, auto
import time

class GuardStatus(Enum):
    CLEAR = auto()
    HALT_STEP_LIMIT = auto()
    HALT_OUT_OF_BOUNDS = auto()
    HALT_RATE_LIMIT = auto()

@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    status: GuardStatus
    step: int
    target: str
    timestamp: float

@dataclass(frozen=True)
class ExecutionGuard:
    allowed_domains: tuple[str, ...] = field(default_factory=tuple)
    max_steps: int = 10
    step_budget: int = 100

    def inspect(self, current_step: int, target: str) -> GuardResult:
        now = time.time()
        
        if current_step >= self.max_steps:
            return GuardResult(
                allowed=False,
                status=GuardStatus.HALT_STEP_LIMIT,
                step=current_step,
                target=target,
                timestamp=now
            )
            
        if self.allowed_domains and not any(target.endswith(domain) for domain in self.allowed_domains):
            return GuardResult(
                allowed=False,
                status=GuardStatus.HALT_OUT_OF_BOUNDS,
                step=current_step,
                target=target,
                timestamp=now
            )
            
        return GuardResult(
            allowed=True,
            status=GuardStatus.CLEAR,
            step=current_step,
            target=target,
            timestamp=now
        )