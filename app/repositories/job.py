# app/repositories/job.py
import json
import redis.asyncio as aioredis
from app.infrastructure import redis as redis_infra
from app.infrastructure.redis import redis_pool, set_value, get_value

class JobRepository:    
    @classmethod
    async def create_job(cls, job_id: str, status: str) -> None:
        """新しいジョブを初期ステータスで作成"""
        key = job_id
        payload = {"status": status}
        # バックグラウンドでもルーターでも安全に動くよう、プールから接続を借りて汎用関数で保存
        async with aioredis.Redis(connection_pool=redis_infra.redis_pool) as client:
            await set_value(client, key, payload, expire_sec=3600)
    @classmethod
    async def update_job_data(cls, job_id: str, data: Dict[str, Any]) -> None:
        """指定されたjob_idのジョブデータを更新（上書き）"""
        key = job_id
        async with aioredis.Redis(connection_pool=redis_infra.redis_pool) as client:
            await set_value(client, key, data, expire_sec=3600)

    @classmethod
    async def get_job(cls, job_id: str) -> dict | None:
        """指定されたjob_idのジョブデータを取得"""
        async with aioredis.Redis(connection_pool=redis_infra.redis_pool) as client:
            raw_result = await get_value(client, job_id)
        if not raw_result:
            return None
        return json.loads(raw_result)
