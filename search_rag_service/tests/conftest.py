from typing import Any

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from core.dependencies import get_agent, get_vector_store
from main import app
from services.vector_store import BaseVectorStore


class FakeVectorStore(BaseVectorStore):
    def __init__(self):
        self.stored: list[dict[str, Any]] = []

    def store_bulk_items(self, job_id: str, store_name: str, items: list[dict[str, Any]]) -> int:
        self.stored.append({"job_id": job_id, "store_name": store_name, "items": items})
        return sum(1 for item in items if len(item.get("item_name", "")) > 0)

    def search_similar_items(self, query_text: str, n_results: int = 3) -> list[dict[str, Any]]:
        return [
            {"item_name": f"fake-result:{query_text}", "distance": 0.1234}
            for _ in range(n_results)
        ]


class FakeAgent:
    async def stream_agent_response(self, user_query: str):
        yield f"data: fake response for {user_query}\n\n"
        yield "data: [DONE]\n\n"


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def fake_agent() -> FakeAgent:
    return FakeAgent()


@pytest.fixture
def test_client(fake_vector_store: FakeVectorStore, fake_agent: FakeAgent) -> TestClient:
    def override_vector_store(request: Request) -> FakeVectorStore:
        return fake_vector_store

    def override_agent(request: Request) -> FakeAgent:
        return fake_agent

    app.dependency_overrides[get_vector_store] = override_vector_store
    app.dependency_overrides[get_agent] = override_agent

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
