#!/usr/bin/env python3
"""
CONSTELLATION 5 ENGINE
Profil wykonawczy: Daniel Ratajczyk v1.0
Archetyp: GRACZ (55->1) + DYNAMIT (5)
"""

from typing import Dict

class Constellation5Engine:
    """
    Silnik rezonansu Constellation 5
    Mapuje energię kinetyczną (5) na inicjatywę (1)
    """

    def __init__(self):
        self.gracz_value = 55       # 5+5 = 10 -> 1
        self.dynamit_value = 5
        self.phone_signature = 555  # 512 155503 -> 555 w centrum
        self.father_day = 5         # 23 -> 2+3 = 5
        self.execution_vector = [5, 5, 5, 1]  # 555->1

    def calculate_system_tension(self, emotional_state: float) -> float:
        """
        Oblicza napięcie systemowe na podstawie stanu emocjonalnego.
        emotional_state: 0.0 (spokój) - 1.0 (eksplozja)
        """
        if emotional_state >= 0.8:
            return 1.0   # Tryb DYNAMIT - pełna inicjatywa
        elif emotional_state >= 0.5:
            return 0.7   # Tryb GRACZ - determinacja
        else:
            return 0.3   # Tryb STATE_00 - regeneracja

    def execute_with_constellation_5(self, task: str, urgency: float) -> Dict:
        tension = self.calculate_system_tension(urgency)

        if tension >= 1.0:
            mode = "DYNAMIT"
            action = "immediate_execution"
        elif tension >= 0.7:
            mode = "GRACZ"
            action = "determined_execution"
        else:
            mode = "STATE_00"
            action = "regeneration"

        return {
            "task": task,
            "mode": mode,
            "action": action,
            "tension": tension,
            "constellation": self.execution_vector,
            "status": "EXECUTED"
        }

    def get_profile(self) -> Dict:
        return {
            "name": "Daniel Ratajczyk",
            "archetype": "GRACZ + DYNAMIT",
            "constellation": self.execution_vector,
            "gracz_value": self.gracz_value,
            "dynamit_value": self.dynamit_value,
            "phone_signature": self.phone_signature,
            "father_day": self.father_day,
            "execution_style": "immediate_initiation_with_kinetic_force",
            "leadership_mode": "natural_authority_without_aggression",
            "transformation_capacity": "chaos_to_structure_in_real_time"
        }

if __name__ == "__main__":
    engine = Constellation5Engine()

    result1 = engine.execute_with_constellation_5(
        task="Prepare DARTRIX presentation for Qwen Hackathon",
        urgency=0.9
    )
    print(f"Hackathon mode: {result1['mode']}")  # DYNAMIT

    result2 = engine.execute_with_constellation_5(
        task="Send CV and repository to CNBOP recruiter",
        urgency=0.6
    )
    print(f"CNBOP mode: {result2['mode']}")  # GRACZ

    result3 = engine.execute_with_constellation_5(
        task="Rest and recover",
        urgency=0.2
    )
    print(f"Rest mode: {result3['mode']}")  # STATE_00

    profile = engine.get_profile()
    print(f"\nFull profile: {profile}")
