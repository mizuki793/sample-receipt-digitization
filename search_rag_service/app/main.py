from fastapi import FastAPI
from routers.search_router import router as search_router
from core.dependencies import lifespan
from core.logging_config import configure_logging

# Configure logging early
configure_logging()

app = FastAPI(
    title="Search RAG Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(search_router)
