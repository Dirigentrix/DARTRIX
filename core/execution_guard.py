"""
DARTRIX — ExecutionGuard Circuit Breaker
Ochrona rdzenia przed kaskadowymi awariami, z integracją z modułem czasu i rezonansu.
Wersja rozbudowana: stany CLOSED / OPEN / HALF_OPEN, próg opóźnienia, metryki, callbacki.
"""

import time
import asyncio
from enum import Enum
from functools import wraps
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, Deque, Dict, List
from threading import Lock


# ─── Stany obwodu ──────────────────────────────────────────────────────────
class CircuitState(Enum):
    CLOSED = "closed"       # Praca normalna — żądania przechodzą
    OPEN = "open"           # Zablokowane — natychmiastowy odrzut
    HALF_OPEN = "half_open" # Próba odzyskania — ograniczona liczba żądań


# ─── Wyjątki ───────────────────────────────────────────────────────────────
class CircuitOpenError(Exception):
    """Podniesiony gdy obwód jest otwarty."""
    def __init__(self, message: str, reopen_at: float):
        super().__init__(message)
        self.reopen_at = reopen_at


class CircuitSlowWarning(Exception):
    """Podniesiony gdy wykonanie przekracza próg opóźnienia."""
    pass


# ─── Konfiguracja i dane ───────────────────────────────────────────────────
@dataclass
class ExecutionMetrics:
    """Zbierane metryki wykonania."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    slow_calls: int = 0
    avg_duration_ms: float = 0.0
    last_duration_ms: float = 0.0
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExecutionConfig:
    """Konfigurowalne parametry strażnika."""
    failure_threshold: int = 5              # Próg błędów do otwarcia
    recovery_timeout: float = 30.0          # Czas chłodzenia [s] przed próbą odzyskania
    half_open_max_tests: int = 2            # Ilość prób w stanie półotwartym
    slow_call_threshold_ms: float = 500.0   # Próg opóźnienia = powolne wykonanie
    window_size: int = 20                   # Rozmiar okna przesuwnego do statystyk
    exclude_exceptions: tuple = ()          # Wyjątki NIE liczone jako awaria
    phase_alignment_enabled: bool = True    # Powiąż z fazą/rezonansem DARTRIX


# ─── Główna klasa ──────────────────────────────────────────────────────────
class ExecutionGuard:
    """
    Strażnik wykonania — wzorzec Circuit Breaker dostosowany do systemów DARTRIX/SIMTRIX.
    
    Cechy:
    • Trzy stany: zamknięty → otwarty → półotwarty → zamknięty
    • Liczy zarówno błędy, jak i przekroczenia opóźnienia
    • Okno przesuwne — zapomina stare błędy w stanie zamkniętym
    • Obsługuje funkcje synchroniczne i asynchroniczne
    • Callbacki przy zmianie stanu
    • Możliwość powiązania z zewnętrznym zegarem/rezonansem systemu
    """

    def __init__(self, name: str = "default", config: Optional[ExecutionConfig] = None):
        self.name = name
        self.config = config or ExecutionConfig()
        
        # Stan
        self._state = CircuitState.CLOSED
        self._failure_count: int = 0
        self._half_open_tests: int = 0
        self._half_open_successes: int = 0
        self._last_failure_time: Optional[float] = None
        self._lock = Lock()  # Bezpieczeństwo w wątkach
        
        # Okno czasowe na czasy wykonania
        self._durations_ms: Deque[float] = deque(maxlen=self.config.window_size)
        
        # Metryki
        self.metrics = ExecutionMetrics()
        
        # Zewnętrzne callbacki
        self.on_open: Optional[Callable[[], None]] = None
        self.on_closed: Optional[Callable[[], None]] = None
        self.on_recovery_test: Optional[Callable[[], None]] = None
        
        # Referencja do zewnętrznego modułu czasu/rezonansu (opcjonalnie)
        self.time_provider: Optional[Callable[[], float]] = None

    # ─── Dostęp do stanu ───────────────────────────────────────────────────
    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_half_open(self) -> bool:
        return self.state == CircuitState.HALF_OPEN

    def _get_time(self) -> float:
        """Pobierz czas — z dostawcy zewnętrznego lub systemowy."""
        if self.time_provider:
            return self.time_provider()
        return time.monotonic()

    # ─── Zarządzanie stanem ─────────────────────────────────────────────────
    def _transition_to(self, new_state: CircuitState) -> None:
        """Przejdź do nowego stanu i wywołaj callback."""
        old_state = self._state
        if old_state == new_state:
            return
        
        self._state = new_state
        self.metrics.state_transitions.append({
            "from": old_state.value,
            "to": new_state.value,
            "at": self._get_time()
        })

        # Reset liczników przy zmianie stanu
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._half_open_tests = 0
            self._half_open_successes = 0
            if self.on_closed:
                self.on_closed()
        elif new_state == CircuitState.OPEN:
            self._last_failure_time = self._get_time()
            if self.on_open:
                self.on_open()
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_tests = 0
            self._half_open_successes = 0
            if self.on_recovery_test:
                self.on_recovery_test()

    def _check_state_transition(self) -> None:
        """Sprawdź czy nadszedł czas na zmianę stanu (z OPEN → HALF_OPEN)."""
        if self._state == CircuitState.OPEN:
            elapsed = self._get_time() - (self._last_failure_time or 0)
            if elapsed >= self.config.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)

    # ─── Główna logika ─────────────────────────────────────────────────────
    def _before_call(self) -> None:
        """Sprawdź stan przed wykonaniem żądania."""
        with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.OPEN:
                reopen_at = (self._last_failure_time or 0) + self.config.recovery_timeout
                raise CircuitOpenError(
                    f"[{self.name}] Obwód otwarty — odrzucenie żądania",
                    reopen_at=reopen_at
                )

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_tests >= self.config.half_open_max_tests:
                    raise CircuitOpenError(
                        f"[{self.name}] Przekroczono limit prób odzyskiwania",
                        reopen_at=0
                    )
                self._half_open_tests += 1

    def _on_success(self, duration_ms: float) -> None:
        """Zarejestruj sukces i ewentualnie zamknij obwód."""
        with self._lock:
            self.metrics.successful_calls += 1
            self._record_duration(duration_ms)

            if duration_ms > self.config.slow_call_threshold_ms:
                self.metrics.slow_calls += 1

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.config.half_open_max_tests:
                    self._transition_to(CircuitState.CLOSED)

            if self._state == CircuitState.CLOSED:
                self._failure_count = 0  # Reset licznika przy sukcesie

    def _on_failure(self, exc: Exception) -> None:
        """Zarejestruj błąd i ewentualnie otwórz obwód."""
        # Pomiń wyjątki z listy wykluczeń
        if isinstance(exc, self.config.exclude_exceptions):
            return

        with self._lock:
            self.metrics.failed_calls += 1

            if self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

            elif self._state == CircuitState.HALF_OPEN:
                # Dowolny błąd w półotwartym → natychmiastowe otwarcie
                self._transition_to(CircuitState.OPEN)

    def _record_duration(self, duration_ms: float) -> None:
        """Zapisz czas wykonania i oblicz średnią."""
        self._durations_ms.append(duration_ms)
        self.metrics.last_duration_ms = duration_ms
        if self._durations_ms:
            self.metrics.avg_duration_ms = sum(self._durations_ms) / len(self._durations_ms)

    # ─── Opakowania wywołań ─────────────────────────────────────────────────
    def __call__(self, func: Callable) -> Callable:
        """Użyj jako dekorator: @guard"""
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return self.call(func, *args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            return await self.call_async(func, *args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Wykonaj funkcję pod ochroną strażnika (synchronicznie)."""
        self.metrics.total_calls += 1
        start = self._get_time()

        self._before_call()
        try:
            result = func(*args, **kwargs)
            duration_ms = (self._get_time() - start) * 1000
            self._on_success(duration_ms)
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Wykonaj funkcję pod ochroną strażnika (asynchronicznie)."""
        self.metrics.total_calls += 1
        start = self._get_time()

        self._before_call()
        try:
            result = await func(*args, **kwargs)
            duration_ms = (self._get_time() - start) * 1000
            self._on_success(duration_ms)
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    # ─── Diagnostyka ───────────────────────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        """Zwróć pełny stan strażnika do raportowania."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "metrics": {
                    "total": self.metrics.total_calls,
                    "successful": self.metrics.successful_calls,
                    "failed": self.metrics.failed_calls,
                    "slow": self.metrics.slow_calls,
                    "avg_duration_ms": round(self.metrics.avg_duration_ms, 2),
                    "last_duration_ms": round(self.metrics.last_duration_ms, 2),
                    "state_transitions": len(self.metrics.state_transitions)
                },
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "half_open_max_tests": self.config.half_open_max_tests,
                    "slow_call_threshold_ms": self.config.slow_call_threshold_ms
                }
            }

    def reset(self) -> None:
        """Ręczny reset — zamknij obwód i wyzeruj liczniki."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._durations_ms.clear()
            self.metrics = ExecutionMetrics()
