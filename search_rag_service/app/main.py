from fastapi import FastAPI
from routers.search_router import router as search_router
from core.dependencies import lifespan

app = FastAPI(
    title="Search RAG Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(search_router)
