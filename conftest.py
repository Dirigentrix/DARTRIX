"""
DARTRIX — Konfiguracja testów
Automatycznie dodaje korzeń projektu do sys.path, zapewnia spójne importy.
"""

import sys
from pathlib import Path

# Ścieżka do korzenia projektu (poziom wyżej niż tests/)
PROJECT_ROOT = Path(__file__).resolve().parent


def pytest_configure():
    """Uruchamiane raz przed wszystkimi testami — ustaw ścieżkę."""
    root_str = str(PROJECT_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
        print(f"✅ Dodano do sys.path: {PROJECT_ROOT}")


# Wspólne fixture'y dostępne we wszystkich testach
pytest_plugins = []
