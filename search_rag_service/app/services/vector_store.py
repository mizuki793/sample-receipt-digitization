from abc import ABC, abstractmethod
from typing import Any

class BaseVectorStore(ABC):
    @abstractmethod
    def store_bulk_items(self, job_id: str, store_name: str, items: list[dict[str, Any]]) -> int:
        raise NotImplementedError

    @abstractmethod
    def search_similar_items(self, query_text: str, n_results: int = 3) -> list[dict[str, Any]]:
        raise NotImplementedError

    def close(self) -> None:
        """Optional cleanup hook for connection-backed stores."""
        return None
