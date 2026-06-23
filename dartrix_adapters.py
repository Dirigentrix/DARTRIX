from typing import Any, Dict, List
import abc

class DartrixAdapter(abc.ABC):
    """Base adapter class for DARTRIX component integration."""
    @abc.abstractmethod
    def sync(self, data: Dict[str, Any]) -> bool:
        pass

class FileAdapter(DartrixAdapter):
    def sync(self, data: Dict[str, Any]) -> bool:
        print(f"[FileAdapter] Syncing data: {data}")
        return True

class NetworkAdapter(DartrixAdapter):
    def sync(self, data: Dict[str, Any]) -> bool:
        print(f"[NetworkAdapter] Broadcasting state change: {data.get('action')}")
        return True

class AdapterRegistry:
    def __init__(self):
        self._adapters: List[DartrixAdapter] = []

    def register(self, adapter: DartrixAdapter):
        self._adapters.append(adapter)

    def broadcast(self, data: Dict[str, Any]):
        for adapter in self._adapters:
            adapter.sync(data)
