## 業務フローのコントロール（手順の統括）などの責務を実行する
## データの具体的な保存・取得コマンド（リポジトリ・インフラの責務）は実施しない
## ex:複数リソースのパイプライン（結合）など

from pathlib import Path
import os
from typing import Any
from fastapi import UploadFile
from app.services.receipt_service import fetch_job_status
from app.repositories.job_redis import JobRepository
from app.repositories.receipt_tmp_data import ReceiptTmpDataRepository
from app.core.config import settings
from app.services.storage.factory import get_storage_client

async def init_receipt_pipeline(file_object: UploadFile, job_id:str) -> str:
    await JobRepository.create_job(job_id, {"status": "PENDING"})
    img_path = await _save_raw_receipt_image(file_object, job_id)
    return img_path

async def _save_raw_receipt_image(file_object: UploadFile, job_id:str) -> str:
    storage_client = get_storage_client()
    _, extension = os.path.splitext(file_object.filename)
    file_bytes = await file_object.read()
    if not extension:
        extension = ".jpg"
    saved_file_path = await storage_client.put_object_file(
         partition_key = "receipt_images",
         file_name=f"{job_id}{extension}",
         data=file_bytes
    )
    return str(saved_file_path)

async def view_receipt_status(job_id: str):
    job_status = await fetch_job_status(job_id)
    return job_status

async def view_job_ids_by_status(status: str) -> list[str]:
    list = await ReceiptTmpDataRepository.get_job_ids_by_status(status)
    return list
