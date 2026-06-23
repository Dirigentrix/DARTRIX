import os
import json
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime

class SOIFPersistence:
    """
    Stabilized Operational Integration Flow (SOIF) Persistence Layer.
    Handles the deterministic storage and retrieval of state transitions.
    """
    def __init__(self, db_path: str = "dartrix_soif.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS state_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    component TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    checksum TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    state_data TEXT NOT NULL
                )
            ''')

    def log_transition(self, component: str, action: str, payload: Dict[str, Any]):
        payload_json = json.dumps(payload)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO state_log (component, action, payload) VALUES (?, ?, ?)",
                (component, action, payload_json)
            )

    def get_history(self, component: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT timestamp, component, action, payload FROM state_log"
        params = []
        if component:
            query += " WHERE component = ?"
            params.append(component)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return [
                {"timestamp": row[0], "component": row[1], "action": row[2], "payload": json.loads(row[3])}
                for row in cursor.fetchall()
            ]

    def save_snapshot(self, state: Dict[str, Any]):
        state_json = json.dumps(state)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO snapshots (state_data) VALUES (?)", (state_json,))

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT state_data FROM snapshots ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return json.loads(row[0]) if row else None
