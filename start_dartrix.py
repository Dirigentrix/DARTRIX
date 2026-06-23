import time
from soif_persistence import SOIFPersistence
from dartrix_adapters import AdapterRegistry, FileAdapter, NetworkAdapter

def main():
    print("--- DARTRIX OS v1.0 Booting ---")
    
    # Initialize Persistence and Adapters
    persistence = SOIFPersistence()
    registry = AdapterRegistry()
    registry.register(FileAdapter())
    registry.register(NetworkAdapter())

    # Example lifecycle event
    boot_payload = {"status": "operational", "version": "1.0"}
    persistence.log_transition("Kernel", "BOOT", boot_payload)
    registry.broadcast({"component": "Kernel", "action": "BOOT", "payload": boot_payload})

    print("--- DARTRIX OS v1.0 Operational ---")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n--- DARTRIX OS v1.0 Shutting Down ---")

if __name__ == "__main__":
    main()
