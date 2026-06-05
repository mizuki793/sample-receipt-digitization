from core.logging_config import logger
import json
from pathlib import Path
from bson import ObjectId
import aiofiles
import httpx
from fastapi.encoders import jsonable_encoder
from core.config import settings
from repositories.job_mongo import MongoJobRepository
from schemas.job import JobStatus
from schemas.receipt import ReceiptAnalysisResponse
from services.receipt_staging_service import ReceiptStagingService


class ReceiptJobService:
    @classmethod
    async def fetch_job_status(cls, job_id: str) -> dict | None:
        job_status_data = await MongoJobRepository.get_job(job_id)

        if job_status_data is None:
            logger.info(f"DBに存在しないジョブです: {job_id}")
            return None

        status = job_status_data.get("status")
        logger.debug(f"Job {job_id} status: {status}")

        if status == JobStatus.PROCESSING.value:
            return cls._clean_job_status_data(job_status_data)

        if status in [
            JobStatus.SUCCESS.value,
            JobStatus.NEEDS_CORRECTION.value,
            JobStatus.FAILED.value,
            JobStatus.LOCKED.value,
        ]:
            return await cls._load_result_file(job_id, status)

        logger.warning(f"ジョブ {job_id} に未知のステータス '{status}' が見つかりました。")
        return job_status_data

    @classmethod
    def _clean_job_status_data(cls, job_status_data: dict) -> dict:
        cleaned_data = {}
        for key, value in job_status_data.items():
            if isinstance(value, ObjectId):
                cleaned_data[key] = str(value)
            else:
                cleaned_data[key] = value
        return cleaned_data

    @classmethod
    async def _load_result_file(cls, job_id: str, status: str) -> dict | None:
        file_path = Path(settings.LOCAL_DATA_SET_BASE_DIR) / "tmp" / f"{job_id}.json"
        if not file_path.exists():
            logger.warning(f"ジョブ {job_id} の補正ファイルが見つかりません: {file_path}")
            return None

        try:
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                if isinstance(data, dict):
                    data["status"] = status
                return data
        except Exception as e:
            logger.error(f"ファイル {file_path} の読み込みに失敗しました: {str(e)}")
            return None

    @classmethod
    async def lock_receipt_job(cls, job_id: str) -> str | None:
        logger.info(f"ジョブの編集ロック処理:{job_id}")
        job_status_data = await MongoJobRepository.get_job(job_id)

        if job_status_data is None:
            logger.info(f"DBに存在しないジョブです: {job_id}")
            return None

        status = job_status_data.get("status")

        if status == JobStatus.LOCKED.value:
            return {
                "job_id": job_id,
                "status": JobStatus.LOCKED.value,
                "message": "このジョブは既にロックされています。",
            }

        if status in [
            JobStatus.SUCCESS.value,
            JobStatus.NEEDS_CORRECTION.value,
            JobStatus.FAILED.value,
        ]:
            updated = await MongoJobRepository.update_job_status_atomically(
                job_id,
                JobStatus(status),
                JobStatus.LOCKED,
            )
            if updated:
                return {
                    "job_id": job_id,
                    "status": JobStatus.LOCKED.value,
                    "message": "ジョブが正常にロックされました。",
                }
            logger.warning(f"ジョブ {job_id} のロック中に競合が発生しました。現在のステータス: {status}")
            raise ValueError("ジョブのロックに失敗しました。競合が発生した可能性があります。")

        logger.warning(f"ジョブ {job_id} に予期しないステータス '{status}' が見つかりました。")
        raise ValueError(f"無効なジョブステータス: {status}")

    @classmethod
    async def fix_receipt_job_data(
        cls,
        job_id: str,
        raw_ocr_text: str,
        fixed_data: ReceiptAnalysisResponse,
    ) -> str | None:
        logger.info(f"レシートデータの修正:{job_id}")
        job_status_data = await MongoJobRepository.get_job(job_id)

        if job_status_data is None:
            logger.info(f"DBに存在しないジョブです: {job_id}")
            return None

        status = job_status_data.get("status")
        if status != JobStatus.LOCKED.value:
            return {
                "job_id": job_id,
                "status": status,
                "message": f"処理フラグがされていないjob_idのため編集不可: {job_id}",
            }

        await ReceiptStagingService.store_verified_receipt(
            job_id=job_id,
            raw_ocr_text=raw_ocr_text,
            validated_data=fixed_data,
        )

        await MongoJobRepository.update_job_data(job_id, {
            "status": JobStatus.SUCCESS.value
        })

        async with httpx.AsyncClient() as client:
            payload = {
                "job_id": job_id,
                "store_name": fixed_data.store_name,
                "items": fixed_data.items,
            }
            await client.post(
                f"{settings.BACKEND_URL}/embeddings",
                json=jsonable_encoder(payload),
            )

        return {
            "job_id": job_id,
            "status": JobStatus.SUCCESS.value,
            "message": "レシートデータが正常に修正されました。",
        }
