#!/usr/bin/env python3
# SONIA_AGENT_OVERDRIVE.py
# DARTRIX / NINIA_TEAM / SAE v0.1

import time
import threading
from enum import Enum
from dataclasses import dataclass, field


# ==========================
# 1. Tryby pracy / rezonans
# ==========================

class EngineMode(str, Enum):
    FLOW = "FLOW"
    CHECK = "CHECK"
    PROTECT = "PROTECT"


class Ren12Mode(str, Enum):
    SAFE = "SAFE"
    EDGE = "EDGE"


class K12Gate(str, Enum):
    COUPLED = "COUPLED"
    DECOUPLED = "DECOUPLED"


@dataclass
class HydraState:
    engine_mode: EngineMode = EngineMode.CHECK
    ren12_mode: Ren12Mode = Ren12Mode.SAFE
    k12_gate: K12Gate = K12Gate.COUPLED
    external_noise: float = 0.0
    internal_noise: float = 0.0
    anomaly_score: float = 0.0
    tick_id: int = 0


# ==========================
# 2. Stub HydraCore (do podpięcia)
# ==========================

def hydra_tick(inputs: dict, last_state: HydraState | None) -> HydraState:
    """
    Tu później podłączysz prawdziwy HydraCore.
    Na razie prosta logika: im większy noise/anomaly, tym bardziej PROTECT.
    """
    tick_id = (last_state.tick_id + 1) if last_state else 0

    external_noise = inputs.get("external_noise", 0.0)
    internal_noise = inputs.get("internal_noise", 0.0)
    anomaly_score = inputs.get("anomaly_score", 0.0)

    risk = external_noise * 0.4 + internal_noise * 0.4 + anomaly_score * 0.8

    if risk < 0.3:
        engine = EngineMode.FLOW
    elif risk < 0.6:
        engine = EngineMode.CHECK
    else:
        engine = EngineMode.PROTECT

    ren = Ren12Mode.SAFE if risk < 0.7 else Ren12Mode.EDGE
    gate = K12Gate.COUPLED if risk < 0.5 else K12Gate.DECOUPLED

    return HydraState(
        engine_mode=engine,
        ren12_mode=ren,
        k12_gate=gate,
        external_noise=external_noise,
        internal_noise=internal_noise,
        anomaly_score=anomaly_score,
        tick_id=tick_id,
    )


# ==========================
# 3. NINIA_TEAM governance stub
# ==========================

class NiniaDecision(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"


@dataclass
class NiniaContext:
    last_decision: NiniaDecision = NiniaDecision.ALLOW
    last_reason: str = "init"
    audit_log: list[str] = field(default_factory=list)


class NiniaTeam:
    """
    Warstwa governance: patrzy na stan Hydry + intencje,
    decyduje czy SONIA może wejść w OVERDRIVE, FLOW, itd.
    """

    def __init__(self):
        self.ctx = NiniaContext()

    def evaluate(self, state: HydraState, intent: str) -> NiniaDecision:
        risk = state.anomaly_score + state.external_noise + state.internal_noise

        if "delete" in intent.lower() or "format" in intent.lower():
            decision = NiniaDecision.BLOCK
            reason = "High-risk intent (delete/format)"
        elif risk > 1.2:
            decision = NiniaDecision.WARN
            reason = f"Risk={risk:.2f} → WARN"
        else:
            decision = NiniaDecision.ALLOW
            reason = f"Risk={risk:.2f} → OK"

        self.ctx.last_decision = decision
        self.ctx.last_reason = reason
        self.ctx.audit_log.append(f"[NINIA] {decision} :: {reason} :: intent='{intent}'")
        return decision

    def print_last(self):
        print(f"[NINIA] decision={self.ctx.last_decision} reason={self.ctx.last_reason}")


# ==========================
# 4. SONIA_AGENT_OVERDRIVE
# ==========================

@dataclass
class SoniaInputs:
    external_noise: float = 0.1
    internal_noise: float = 0.2
    anomaly_score: float = 0.0
    intent: str = "idle"


class SoniaAgentOverdrive:
    """
    Główny agent:
    - czyta wejścia (intencje, noise, anomaly),
    - odpala HydraCore,
    - pyta NINIA_TEAM o zgodę,
    - wybiera tryb OVERDRIVE / FLOW / CHECK / PROTECT,
    - loguje decyzje.
    """

    def __init__(self):
        self.last_state: HydraState | None = None
        self.ninia = NiniaTeam()
        self.current_inputs = SoniaInputs()

    # --- wejścia / intencje ---

    def set_intent(self, intent: str):
        self.current_inputs.intent = intent

    def set_noise(self, external: float | None = None, internal: float | None = None):
        if external is not None:
            self.current_inputs.external_noise = external
        if internal is not None:
            self.current_inputs.internal_noise = internal

    def set_anomaly(self, anomaly: float):
        self.current_inputs.anomaly_score = anomaly

    def read_inputs(self) -> dict:
        return {
            "external_noise": self.current_inputs.external_noise,
            "internal_noise": self.current_inputs.internal_noise,
            "anomaly_score": self.current_inputs.anomaly_score,
        }

    # --- główny krok ---

    def tick(self):
        inputs = self.read_inputs()
        state = hydra_tick(inputs, self.last_state)
        self.last_state = state

        resonance = self.compute_resonance(state)
        decision = self.ninia.evaluate(state, self.current_inputs.intent)

        self.decide(resonance, state, decision)

    def compute_resonance(self, state: HydraState) -> float:
        base = 0.0

        if state.engine_mode == EngineMode.FLOW:
            base += 0.6
        elif state.engine_mode == EngineMode.CHECK:
            base += 0.4
        else:  # PROTECT
            base += 0.2

        base += 0.3 if state.ren12_mode == Ren12Mode.SAFE else 0.1
        base += 0.3 if state.k12_gate == K12Gate.COUPLED else 0.1

        return min(1.0, base)

    def decide(self, resonance: float, state: HydraState, ninia_decision: NiniaDecision):
        mode_label = f"{state.engine_mode.value}/{state.ren12_mode.value}/{state.k12_gate.value}"

        if ninia_decision == NiniaDecision.BLOCK:
            print(f"[SONIA] BLOCK by NINIA → intent='{self.current_inputs.intent}'")
            self.ninia.print_last()
            return

        if ninia_decision == NiniaDecision.WARN:
            print(f"[SONIA] WARN by NINIA → ograniczamy OVERDRIVE")
            self.ninia.print_last()

        if resonance > 0.8 and ninia_decision == NiniaDecision.ALLOW:
            print(f"[SONIA] OVERDRIVE ON → resonance={resonance:.2f} mode={mode_label}")
        elif resonance > 0.5:
            print(f"[SONIA] FLOW TASKS → resonance={resonance:.2f} mode={mode_label}")
        elif resonance > 0.3:
            print(f"[SONIA] CHECK / przygotowanie → resonance={resonance:.2f} mode={mode_label}")
        else:
            print(f"[SONIA] PROTECT / porządkowanie → resonance={resonance:.2f} mode={mode_label}")


# ==========================
# 5. Prosty loop CLI
# ==========================

def run_loop():
    agent = SoniaAgentOverdrive()

    def input_thread():
        while True:
            try:
                raw = input("\n[CLI] wpisz intencję (np. 'prepare hackathon pitch'): ")
            except EOFError:
                break

            raw = raw.strip()
            if not raw:
                continue

            if raw.startswith("noise "):
                # np. "noise 0.2 0.4"
                parts = raw.split()
                if len(parts) >= 3:
                    ext = float(parts[1])
                    inn = float(parts[2])
                    agent.set_noise(ext, inn)
                    print(f"[CLI] noise set ext={ext} inn={inn}")
                continue

            if raw.startswith("anomaly "):
                # np. "anomaly 0.7"
                parts = raw.split()
                if len(parts) >= 2:
                    an = float(parts[1])
                    agent.set_anomaly(an)
                    print(f"[CLI] anomaly set={an}")
                continue

            agent.set_intent(raw)
            print(f"[CLI] intent set='{raw}'")

    t = threading.Thread(target=input_thread, daemon=True)
    t.start()

    print("[SONIA_OVERDRIVE] start loop (Ctrl+C aby wyjść)")
    try:
        while True:
            agent.tick()
            time.sleep(0.7)
    except KeyboardInterrupt:
        print("\n[SONIA_OVERDRIVE] stop")


if __name__ == "__main__":
    run_loop()
