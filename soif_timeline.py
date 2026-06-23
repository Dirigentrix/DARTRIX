import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

class SoifTimeline:
    """
    SoifTimeline: An append-only JSONL logger for DARTRIX OS v1.0.
    Persists system events to 'logs/soif_timeline.jsonl' and provides
    methods for event recall and state reconstruction.
    """
    def __init__(self, log_path: str = "logs/soif_timeline.jsonl"):
        self.log_path = log_path
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        directory = os.path.dirname(self.log_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def log_event(self, event: Dict[str, Any]) -> str:
        """
        Generates a unique event ID, records metadata, and appends to the log file.
        Expected keys in event: 'module', 'type', 'napięcie', 'mode', 'details'.
        """
        event_id = str(uuid.uuid4())
        # Use UTC for consistency across DARTRIX systems
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        log_entry = {
            "id": event_id,
            "timestamp": timestamp,
            "module": event.get("module", "unknown"),
            "type": event.get("type", "generic"),
            "napięcie": event.get("napięcie", 0.0),
            "mode": event.get("mode", "default"),
            "details": event.get("details", {}),
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
            
        return event_id

    def recall(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filters logs chronologically.
        Query filters: 'since' (ISO timestamp), 'module', 'type', 'limit'.
        """
        since = query.get("since")
        module_filter = query.get("module")
        type_filter = query.get("type")
        limit = query.get("limit")
        
        results = []
        if not os.path.exists(self.log_path):
            return results

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                if since and entry["timestamp"] < since:
                    continue
                if module_filter and entry["module"] != module_filter:
                    continue
                if type_filter and entry["type"] != type_filter:
                    continue
                
                results.append(entry)
                if limit and len(results) >= limit:
                    break
                    
        return results

    def get_state_at(self, timestamp: str) -> Dict[str, Any]:
        """
        Replays events up to a given timestamp to reconstruct system state.
        State tracks the latest state of each module and global telemetry.
        """
        state = {
            "reconstructed_at": timestamp,
            "modules": {},
            "last_napięcie": 0.0,
            "active_modes": set()
        }
        
        if not os.path.exists(self.log_path):
            return state

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if entry["timestamp"] > timestamp:
                    break
                
                mod = entry["module"]
                state["modules"][mod] = entry["details"]
                state["last_napięcie"] = entry["napięcie"]
                state["active_modes"].add(entry["mode"])

        state["active_modes"] = list(state["active_modes"])
        return state
