import json
import time
from typing import Dict, Any
from numerology_math import NumerologyProcessor
from sacred_geometry import SacredGeometry
from flint_core import FlintCore
from memory_agent import MemoryAgent
from edge_agent import EdgeAgent


class DartrixEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.version = config.get("version", "1.2.0-flint-tes")

        # Rdzenie systemowe
        self.flint = FlintCore(max_memory_kb=2048)
        self.memory = MemoryAgent(self.flint)
        self.edge = EdgeAgent(self.flint)

        # Moduły obliczeniowe
        self.np = NumerologyProcessor(base=config.get("numerology_base", 9))
        self.sg = SacredGeometry(active=config.get("geometry_active", True))

        # Mapa pierwiastków – fundament fizyczny TES
        self.elements_map = self._load_elements()

    def _load_elements(self) -> Dict[str, Any]:
        """Wczytuje mapę pierwiastków, zabezpieczone przed brakiem pliku."""
        try:
            with open("elements_map.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Nie udało się wczytać mapy pierwiastków: {e}")
            return {"layers": {}}

    def _get_element_by_mode(self, layer_key: str, mode: str) -> Dict[str, Any]:
        """Wybiera pierwiastek bezpośrednio z warstwy zgodnie z trybem systemu."""
        layer = self.elements_map.get("layers", {}).get(layer_key, {})
        if not layer:
            return {"symbol": "Si", "name": "Krzem", "role": "Failsafe"}
        if mode == "economy":
            return layer.get("alternative", layer.get("primary", {}))
        elif mode == "mixed":
            primary = layer.get("primary", {})
            optimized = layer.get("optimized", layer.get("premium", {}))
            return {**primary, "optimized_node": optimized}
        else:
            return layer.get("primary", {})

    def process(self, input_data: Any) -> Dict[str, Any]:
        """
        Główna ścieżka przetwarzania:
        Dane → Optymalizacja → Redukcja numerologiczna → Wzór geometryczny →
        Przypisanie rezonansu fizycznego → Pełny wynik zgodny z TES
        """
        cleaned = self.edge.optimize_input(input_data)

        # Redukcja numerologiczna
        if str(cleaned).strip().isdigit():
            num_input = int(cleaned)
        else:
            num_input = len(str(cleaned))

        value = self.np.reduce_number(num_input)
        pattern = self.sg.get_pattern(value)

        # Mapowanie wartości na warstwę fizyczną
        if value in [1, 5, 9]:
            layer_name = "core_logic"
        elif value in [2, 6]:
            layer_name = "transmission"
        elif value in [3, 7]:
            layer_name = "radio_orbital"
        elif value in [4, 8]:
            layer_name = "power_supply"
        elif value in [11, 22, 33]:
            layer_name = "structural_support"
        else:
            layer_name = "core_logic"

        # Pobranie pierwiastka zgodnie z aktywnym trybem
        mode = self.config.get("elements_mode", "default")
        element_data = self._get_element_by_mode(layer_name, mode)
        element_key = element_data.get("symbol", "Si")

        signature = f"DARTRIX-{self.version}-{value}-{element_key}-{pattern[:3]}"

        # Pełny wynik z wektorem fizycznym
        result = {
            "original": input_data,
            "cleaned": cleaned,
            "value": value,
            "pattern": pattern,
            "element_resonance": element_key,
            "element_info": element_data,
            "layer": layer_name,
            "efficiency_coefficient": element_data.get("efficiency", 100) / 100,
            "signature": signature,
            "ready": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        self.memory.save(f"proc_{int(time.time() * 1000)}", result)
        return result
