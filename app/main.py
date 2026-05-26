from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from app.infrastructure.redis import init_redis_pool, close_redis_pool
from app.infrastructure.duckdb import init_database
from app.infrastructure.mongodb import init_mongo_client, close_mongo_client
from app.routers.receipt_router import router as receipt_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_redis_pool()
    init_mongo_client()
    await run_in_threadpool(init_database)
    #遅延させて返す
    yield
    await close_redis_pool()
    close_mongo_client()

app = FastAPI(lifespan=lifespan)
app.include_router(receipt_router)
