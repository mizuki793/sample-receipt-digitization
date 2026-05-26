from typing import List, Literal
import redis.asyncio as aioredis
from app.infrastructure import redis as redis_infra
from app.infrastructure.redis import add_to_set, remove_from_set, get_set_members

ReceiptStatus = Literal["processing", "needs_correction", "failed"]
class ReceiptTmpDataRepository:
    @classmethod
    async def add_job_id_to_status_set(cls, status:ReceiptStatus, job_id) -> None:
        """指定ステータスのセットにjob_idを追加する（SADD）"""
        key = f"receipt:status:{status}"
        # バックグラウンドでもルーターでも安全に動くよう、プールから接続を借りて汎用関数で保存
        async with aioredis.Redis(connection_pool=redis_infra.redis_pool) as client:
            await add_to_set(client, key, job_id)
    
    @classmethod
    async def remove_job_id_from_status_set(cls, status:ReceiptStatus, job_id) -> None:
        """指定ステータスのセットからjob_idを削除する（SREM）"""
        key = f"receipt:status:{status}"
        async with aioredis.Redis(connection_pool=redis_infra.redis_pool) as client:
            await remove_from_set(client, key, job_id)

    @classmethod
    async def get_job_ids_by_status(cls, status:ReceiptStatus) -> List[str]:
        """指定ステータスのセットの全job_idを取得する（SMEMBERS）"""
        key = f"receipt:status:{status}"
        async with aioredis.Redis(connection_pool=redis_infra.redis_pool) as client:
            result = await get_set_members(client, key)
        return result
