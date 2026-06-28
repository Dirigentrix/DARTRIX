import requests
import time

class DARTRIXBridgeClient:
    def __init__(self, web_app_url):
        self.url = web_app_url

    def read_telemetry(self, sheet_name="REJESTR_ZLECONYCH"):
        try:
            params = {
                "action": "read",
                "sheet": sheet_name
            }
            response = requests.get(self.url, params=params, timeout=10)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def write_log(self, row_data, sheet_name="REJESTR_ZLECONYCH"):
        try:
            payload = {
                "action": "write",
                "sheet": sheet_name,
                "data": row_data
            }
            response = requests.post(self.url, json=payload, timeout=10)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # --- TUTAJ WKLEJ SWÓJ PRYWATNY URL WYGENEROWANY Z APPS SCRIPT ---
    TEST_URL = "https://script.google.com/macros/s/AKfycbz09Kclvqfa7z3uaWq-mr5xEx_CFiDZTdYDL3jv3a9Ylr7LC6J9FqS4WOOiv_PWLBCI/exec"
    # -----------------------------------------------------------------

    if TEST_URL != "WSTAW_TUTAJ_SWÓJ_URL":
        client = DARTRIXBridgeClient(TEST_URL)

        print("[DARTRIX] Test zapisu do arkusza...")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        write_res = client.write_log(
            [timestamp, "PYTHON_CLIENT", "DARTRIX Smart Bridge Connected"]
        )
        print("[DARTRIX] Wynik zapisu:", write_res)

        print("\n[DARTRIX] Test odczytu z arkusza...")
        read_res = client.read_telemetry()
        print("[DARTRIX] Wynik odczytu:", read_res)
    else:
        print("[ALARM] Brak wklejonego URL. Uzyskaj link WebApp i podmień zmienną TEST_URL.")
