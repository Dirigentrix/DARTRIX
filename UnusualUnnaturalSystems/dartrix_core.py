import os
import time
import json
from bridge_client import DARTRIXBridgeClient
from haccp_layer import HACCPLayer

class DARTRIXStateMachine:
    def __init__(self):
        self.state = "INITIALIZING"
        self.history = []

    def transition(self, new_state):
        print(f"[DARTRIX] State Transition: {self.state} -> {new_state}")
        self.history.append({"from": self.state, "to": new_state, "time": time.time()})
        self.state = new_state

class DARTRIXCore:
    def __init__(self, bridge_url, gemini_key=None):
        self.bridge = DARTRIXBridgeClient(bridge_url)
        self.haccp = HACCPLayer()
        self.sm = DARTRIXStateMachine()
        self.gemini_key = gemini_key
        
    def gemini_extract_data(self, document_content):
        """
        Modular placeholder for Gemini AI document extraction.
        In a real scenario, this would use the GEMINI_API_KEY to call the API.
        """
        if not self.gemini_key:
            return {"status": "error", "message": "Gemini API key not configured"}
        
        print("[DARTRIX] AI Analyzing document with Gemini...")
        # Placeholder logic
        return {"extracted_temp": 4.2, "point_id": "refrigerator_temp"}

    def dartrix_cycle(self):
        """Main execution cycle for DARTRIX."""
        self.sm.transition("READY")
        
        try:
            while True:
                self.sm.transition("POLLING")
                # Read from Google Sheets via Bridge
                telemetry = self.bridge.read_telemetry()
                print(f"[DARTRIX] Telemetry data: {telemetry}")
                
                # Mock analysis step
                self.sm.transition("ANALYZING")
                test_point = "refrigerator_temp"
                test_val = 4.5
                
                is_safe, msg = self.haccp.validate_reading(test_point, test_val)
                print(f"[DARTRIX] HACCP Check: {msg}")
                
                # Write log back to sheet
                self.sm.transition("LOGGING")
                log_entry = [time.strftime("%Y-%m-%d %H:%M:%S"), "CORE_CYCLE", f"HACCP: {msg}"]
                self.bridge.write_log(log_entry)
                
                self.sm.transition("IDLE")
                print("[DARTRIX] Cycle complete. Sleeping for 60 seconds...")
                time.sleep(60)
                
        except KeyboardInterrupt:
            self.sm.transition("SHUTDOWN")
            print("[DARTRIX] System stopped by user.")

if __name__ == "__main__":
    # Load configuration
    BRIDGE_URL = "https://script.google.com/macros/s/AKfycbz09Kclvqfa7z3uaWq-mr5xEx_CFiDZTdYDL3jv3a9Ylr7LC6J9FqS4WOOiv_PWLBCI/exec"
    GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
    
    # In practice, you might load from .env here using a library like python-dotenv
    # Since we can't install libraries, we assume the environment is pre-set.
    
    core = DARTRIXCore(BRIDGE_URL, GEMINI_KEY)
    core.dartrix_cycle()
