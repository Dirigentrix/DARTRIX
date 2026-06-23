import json
from typing import List, Dict, Any
from soif_persistence import SOIFPersistence

class ReplayEngine:
    """
    Deterministic Replay Engine v1.1.
    Allows for the exact reconstruction of state transitions from logs.
    """
    def __init__(self, persistence: SOIFPersistence):
        self.persistence = persistence

    def replay_sequence(self, component: str = None):
        history = self.persistence.get_history(component)
        print(f"--- Replaying {len(history)} transitions ---")
        for entry in history:
            print(f"[{entry['timestamp']}] {entry['component']} -> {entry['action']}: {entry['payload']}")

    def export_trace(self, filename: str):
        history = self.persistence.get_history()
        with open(filename, 'w') as f:
            json.dump(history, f, indent=4)
        print(f"Trace exported to {filename}")

if __name__ == "__main__":
    # Self-test if run directly
    db = SOIFPersistence("replay_test.db")
    engine = ReplayEngine(db)
    engine.replay_sequence()
