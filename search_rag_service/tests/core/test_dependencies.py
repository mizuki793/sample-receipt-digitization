import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException

from core.dependencies import get_agent, get_vector_store, lifespan
from services.vector_store import BaseVectorStore


class DummyVectorStore(BaseVectorStore):
    def store_bulk_items(self, job_id: str, store_name: str, items: list[dict]) -> int:
        return 0

    def search_similar_items(self, query_text: str, n_results: int = 3) -> list[dict]:
        return []


class DummyAgent:
    pass


def test_get_vector_store_raises_when_not_initialized():
    request = SimpleNamespace(app=FastAPI())

    with pytest.raises(HTTPException):
        get_vector_store(request)


def test_get_agent_raises_when_not_initialized():
    request = SimpleNamespace(app=FastAPI())

    with pytest.raises(HTTPException):
        get_agent(request)


def test_lifespan_initializes_state_and_closes(monkeypatch):
    app = FastAPI()
    fake_vector_store = DummyVectorStore()
    fake_agent = DummyAgent()
    closed = {"closed": False}

    def fake_close():
        closed["closed"] = True

    fake_vector_store.close = fake_close

    monkeypatch.setattr("core.dependencies.create_chroma_vector_store", lambda: fake_vector_store)
    monkeypatch.setattr("core.dependencies.ShoppingAgent", lambda vector_store: fake_agent)

    async def run_lifespan():
        async with lifespan(app):
            assert app.state.vector_store is fake_vector_store
            assert app.state.agent is fake_agent

    asyncio.run(run_lifespan())
    assert closed["closed"] is True
