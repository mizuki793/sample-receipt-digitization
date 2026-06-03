# from typing import Any

# from app.services.vector_store import BaseVectorStore

# class FakeVectorStore(BaseVectorStore):
#     def __init__(self):
#         self.stored = []

#     def store_bulk_items(self, job_id: str, store_name: str, items: list[dict[str, Any]]) -> int:
#         self.stored.append({"job_id": job_id, "store_name": store_name, "items": items})
#         return sum(1 for item in items if len(item.get("item_name", "")) > 0)

#     def search_similar_items(self, query_text: str, n_results: int = 3) -> list[dict[str, Any]]:
#         return [{"item_name": f"fake-result:{query_text}", "distance": 0.1234} for _ in range(n_results)]
