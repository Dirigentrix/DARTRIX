from enum import Enum, auto

class Role(Enum):
    FRONTLINE = auto()
    REGULATOR = auto()
    ARCHITEKT = auto()
    OPERATOR = auto()
    STRATEG = auto()
    ANALIZATOR = auto()
    TWORCA = auto()
    STRAZNIK = auto()
    STRAZNIK_2 = auto()  # Nowa rola: Pre-filtracja i klasyfikacja ryzyka


class DanielSanModule:
    def __init__(self, id: int, role: Role, weight: int):
        self.id = id
        self.role = role
        self.weight = weight
        self.state = {}
        self.active = True

    def can_handle(self, event_type: str) -> bool:
        # Zaktualizowana tablica routingu zgodnie z wytycznymi audytu
        routing_table = {
            "COMM": [Role.FRONTLINE],
            "BODY": [Role.REGULATOR],
            "SYSTEM": [Role.ARCHITEKT, Role.OPERATOR],  # Separacja obowiązków zachowana w logice handle
            "DECISION": [Role.STRATEG],
            "DATA": [Role.ANALIZATOR],
            "CREATIVE": [Role.TWORCA],
            "SECURITY": [Role.STRAZNIK, Role.STRAZNIK_2],  # Obie warstwy bezpieczeństwa aktywne
        }
        return self.role in routing_table.get(event_type, [])

    def handle_event(self, event: dict) -> dict:
        if not self.active:
            return {"module": self.id, "status": "inactive"}
            
        response = {
            "module": self.id,
            "role": self.role.name,
            "event": event,
            "status": "processed",
            "weight": self.weight
        }

        # Specjalizacja ról 3 i 4 po migracji walidacji pipeline'ów
        if self.role == Role.ARCHITEKT:
            response["action"] = "Zaprojektowano i zoptymalizowano struktury systemu."
        elif self.role == Role.OPERATOR:
            response["action"] = "Przejęto i zatwierdzono walidację pipeline'u wykonawczego."
        elif self.role == Role.STRAZNIK_2:
            response["action"] = "Dokonano wstępnej klasyfikacji ryzyka oraz typu zdarzenia."

        return response


# Inicjalizacja zaktualizowanego klastra (KROK 1, 2, 3 wdrożony)
cluster = [
    DanielSanModule(1, Role.FRONTLINE, 5),
    DanielSanModule(2, Role.REGULATOR, 4),
    DanielSanModule(3, Role.ARCHITEKT, 4),   # Odciążony z walidacji pipeline'ów
    DanielSanModule(4, Role.OPERATOR, 3),    # Przejął walidację struktur od ID: 3
    DanielSanModule(5, Role.STRATEG, 5),
    DanielSanModule(6, Role.ANALIZATOR, 4),
    DanielSanModule(7, Role.TWORCA, 4),       # PODNIESIONO PRIORYTET: W:3 ──► W:4
    DanielSanModule(8, Role.STRAZNIK, 5),
    DanielSanModule(9, Role.STRAZNIK_2, 5),  # DODANO: Nowy moduł bezpieczeństwa
]


def route_event(event: dict) -> list:
    responses = []
    
    # KROK: Symulacja działania pre-filtra STRAZNIK_2 przed dopuszczeniem do komunikacji
    if event["type"] == "COMM":
        straznik_2 = next((m for m in cluster if m.role == Role.STRAZNIK_2), None)
        if straznik_2 and straznik_2.active:
            responses.append(straznik_2.handle_event(event))
            print(f"[PRE-FILTER] Moduł 9 (STRAZNIK_2) obniżył obciążenie modułu FRONTLINE.")

    for module in cluster:
        if module.role != Role.STRAZNIK_2 and module.can_handle(event["type"]):
            responses.append(module.handle_event(event))
            
    return sorted(responses, key=lambda r: r["weight"], reverse=True)


if __name__ == "__main__":
    print("[KARTRIX] Uruchamianie testów integracyjnych wdrożenia...")
    
    # Testowy strumień dla migracji ról SYSTEM
    test_event_system = {"type": "SYSTEM", "payload": "Walidacja i kompilacja nowego pipeline OPS"}
    out_system = route_event(test_event_system)
    
    for r in out_system:
        print(f"-> Rola: {r['role']} | Akcja: {r.get('action', 'Przetworzono standardowo')}")
