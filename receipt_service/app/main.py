from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from infrastructure.duckdb import init_database
from infrastructure.mongodb import init_mongo_client, close_mongo_client
from routers.receipt_router import router as receipt_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_mongo_client()
    await run_in_threadpool(init_database)
    #遅延させて返す
    yield
    close_mongo_client()

app = FastAPI(
    title="Receipt Service", 
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(receipt_router)
