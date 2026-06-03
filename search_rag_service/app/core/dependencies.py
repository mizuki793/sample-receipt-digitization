from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from services.chromadb_service import create_chroma_vector_store
from services.vector_store import BaseVectorStore
from services.agent_service import ShoppingAgent


def get_vector_store(request: Request) -> BaseVectorStore:
    vector_store = getattr(request.app.state, "vector_store", None)
    if vector_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vector store is not initialized",
        )
    return vector_store


def get_agent(request: Request) -> ShoppingAgent:
    agent = getattr(request.app.state, "agent", None)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent is not initialized",
        )
    return agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.vector_store = create_chroma_vector_store()
    app.state.agent = ShoppingAgent(vector_store=app.state.vector_store)
    yield
    app.state.vector_store.close()
