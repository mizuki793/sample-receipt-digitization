import json
from typing import Any, Dict
import redis.asyncio as aioredis
from app.infrastructure import redis as redis_infra
from app.infrastructure.redis import redis_pool, add_to_set, remove_from_set, get_set_members

class ReceiptTmpDataRepository:
    @classmethod
    async def add_to_set_receipt_tmp_data(cls, status ,job_id) -> None:
        """receipt_tmp_dataにidを追加する（SADD）"""
        key = f"receipt:status:{status}"
        # バックグラウンドでもルーターでも安全に動くよう、プールから接続を借りて汎用関数で保存
        async with aioredis.Redis(connection_pool=redis_infra.redis_pool) as client:
            await add_to_set(client, key, job_id)
    
    @classmethod
    async def remove_from_set_receipt_tmp_data(cls, status, job_id) -> None:
        """receipt_tmp_dataからidを削除する（SREM）"""
        key = f"receipt:status:{status}"
        async with aioredis.Redis(connection_pool=redis_infra.redis_pool) as client:
            await remove_from_set(client, key, job_id)

    @classmethod
    async def get_set_members_receipt_tmp_data(cls, status) -> dict | None:
        """receipt_tmp_dataの全要素を取得する（SMEMBERS）"""
        key = f"receipt:status:{status}"
        async with aioredis.Redis(connection_pool=redis_infra.redis_pool) as client:
            result = await get_set_members(client, key)
        return json.loads(result)
