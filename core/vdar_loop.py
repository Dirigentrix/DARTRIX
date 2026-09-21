"""
vDAR — Główna pętla wykonania z ExecutionGuard
Strażnik chroni rdzeń przed kaskadowymi awariami i dryfem fazy.
"""

import asyncio
from typing import Dict, Any
from core.execution_guard import ExecutionGuard, ExecutionConfig, CircuitOpenError


class VDARLoop:
    """Pętla główna systemu DARTRIX z wbudowanym strażnikiem wykonania."""

    def __init__(self, cycle_rate_hz: float = 60.0):
        self.cycle_rate_hz = cycle_rate_hz
        self.cycle_interval = 1.0 / cycle_rate_hz
        self.guard = ExecutionGuard(
            name="vdar_main_loop",
            config=ExecutionConfig(
                failure_threshold=5,
                recovery_timeout=2.0,
                half_open_max_tests=2,
                slow_call_threshold_ms=16.0,
                window_size=30,
            ),
        )
        self.guard.on_open = self._on_guard_open
        self.guard.on_closed = self._on_guard_closed
        self.guard.on_recovery_test = self._on_recovery_test
        self.cycle_count: int = 0
        self.is_running: bool = False
        self.last_cycle_time: float = 0.0

    def _on_guard_open(self) -> None:
        print("⚠️ OBWÓD OTWARTY — vDAR zatrzymany dla ochrony systemu")

    def _on_guard_closed(self) -> None:
        print("✅ vDAR — Sprawność odzyskana, wznowienie normalnej pracy")

    def _on_recovery_test(self) -> None:
        print("🔍 vDAR — Próba odzyskania sprawności...")

    async def _cycle(self) -> Dict[str, Any]:
        self.cycle_count += 1
        return {"cycle": self.cycle_count, "hz": self.cycle_rate_hz, "state": "active"}

    async def _guarded_cycle(self) -> Dict[str, Any]:
        return await self.guard.call_async(self._cycle)

    async def run(self):
        self.is_running = True
        print(f"🚀 vDAR uruchomiony — cel {self.cycle_rate_hz} Hz")
        while self.is_running:
            try:
                result = await self._guarded_cycle()
                self.last_cycle_time = result["cycle"]
            except CircuitOpenError:
                await asyncio.sleep(0.1)
                continue
            except Exception as exc:
                print(f"❌ Błąd cyklu #{self.cycle_count}: {exc}")
                await asyncio.sleep(0.5)
                continue
            await asyncio.sleep(self.cycle_interval)

    def get_status(self) -> Dict[str, Any]:
        return {
            "loop": {
                "running": self.is_running,
                "cycle": self.cycle_count,
                "target_hz": self.cycle_rate_hz,
                "interval_s": self.cycle_interval,
            },
            "guard": self.guard.get_status(),
        }

    def stop(self):
        self.is_running = False
        print("🛑 vDAR zatrzymany")


if __name__ == "__main__":
    loop = VDARLoop(cycle_rate_hz=60.0)

    async def monitor():
        while loop.is_running:
            await asyncio.sleep(5)
            status = loop.get_status()
            print(
                f"📊 Stan: {status['guard']['state']} | "
                f"Cykle: {status['loop']['cycle']} | "
                f"Średni czas: {status['guard']['metrics']['avg_duration_ms']:.2f} ms"
            )

    async def main():
        await asyncio.gather(loop.run(), monitor(), return_exceptions=True)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        loop.stop()
