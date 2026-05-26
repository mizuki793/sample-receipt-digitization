import redis.asyncio as aioredis
import json
from typing import Any,AsyncGenerator
from app.core.config import settings

REDIS_URL = settings.REDIS_URL
redis_pool: aioredis.ConnectionPool | None = None

def init_redis_pool():
    global redis_pool
    redis_pool = aioredis.ConnectionPool.from_url(
        REDIS_URL, max_connections=10
    )

async def close_redis_pool():
    if redis_pool:
        await redis_pool.disconnect()

async def get_redis_client() -> AsyncGenerator[aioredis.Redis, None]:
    if not redis_pool:
        raise RuntimeError("Redis pool is not initialized")
    
    # プールからリクエストごとのクライアントを生成
    client = aioredis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        # リクエスト終了時に自動で接続を閉じる（プールには戻る）
        await client.aclose()


async def set_value(client: aioredis.Redis, key: str, value: Any, expire_sec: int | None = None) -> None:
    serialized_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
    if expire_sec:
        await client.set(key, serialized_value, ex=expire_sec)
    else:
        await client.set(key, serialized_value)

async def get_value(client: aioredis.Redis, key: str) -> str | None:
    return await client.get(key)

async def add_to_set(client: aioredis.Redis, key: str, value: str) -> int:
    """指定したSetに値を追加する（SADD）"""
    return await client.sadd(key, value)

async def remove_from_set(client: aioredis.Redis, key: str, value: str) -> int:
    """指定したSetから値を削除する（SREM）"""
    return await client.srem(key, value)

async def get_set_members(client: aioredis.Redis, key: str) -> list[str]:
    """指定したSetの全要素を取得する（SMEMBERS）"""
    return await client.smembers(key)
