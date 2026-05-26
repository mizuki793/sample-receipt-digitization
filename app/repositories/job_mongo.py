from typing import Any, Dict
from datetime import datetime, timezone
from fastapi.concurrency import run_in_threadpool
from app.infrastructure import mongodb as mongo_infra

class MongoJobRepository:
    
    @classmethod
    async def create_job(cls, job_id: str, status: str) -> None:
        """新しいジョブを初期ステータスで作成（MongoDB永続層）"""
        payload = {
            "job_id": job_id,
            "status": status,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        def _execute():
            db = mongo_infra.mongo_client["receipt_db"]
            collection = db["jobs"]
            collection.update_one({"job_id": job_id}, {"$set": payload}, upsert=True)
            
        await run_in_threadpool(_execute)
    
    @classmethod
    async def update_job_data(cls, job_id: str, data: Dict[str, Any]) -> None:
        """指定されたjob_idのジョブデータを更新（MongoDB永続層）"""
        payload = {**data}
        payload["updated_at"] = datetime.now(timezone.utc)
        
        def _execute():
            db = mongo_infra.mongo_client["receipt_db"]
            collection = db["jobs"]
            collection.update_one({"job_id": job_id}, {"$set": payload}, upsert=True)
            
        await run_in_threadpool(_execute)

    @classmethod
    async def get_job(cls, job_id: str) -> dict | None:
        """指定されたjob_idのジョブデータを取得（MongoDB永続層）"""
        def _execute():
            db = mongo_infra.mongo_client["receipt_db"]
            collection = db["jobs"]
            return collection.find_one({"job_id": job_id})
            
        raw_result = await run_in_threadpool(_execute)
            
        if not raw_result:
            return None
            
        if "_id" in raw_result:
            del raw_result["_id"]
            
        return raw_result