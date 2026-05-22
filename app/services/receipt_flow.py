## 業務フローのコントロール（手順の統括）などの責務を実行する
## データの具体的な保存・取得コマンド（リポジトリ・インフラの責務）は実施しない
## ex:複数リソースのパイプライン（結合）など

from pathlib import Path
from typing import Any
from fastapi import UploadFile
from app.services.receipt_service import fetch_job_status
from app.repositories.job import JobRepository

UPLOAD_DIR = Path("/tmp/receipt_imgs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def init_receipt_pipeline(file_object: UploadFile, job_id:str) -> str:
    await JobRepository.create_job(job_id, {"status": "PENDING"})
    img_path = await save_for_local_receipt_image(file_object, job_id)
    return img_path

# ファイル保存処理、将来的にクラウドに上げることも踏まえた切り出し
async def save_for_local_receipt_image(file_object: UploadFile, job_id:str) -> str:
    saved_file_path = UPLOAD_DIR / f"{job_id}.jpg"
    content = await file_object.read()
    with open(saved_file_path, "wb") as buffer:
        buffer.write(content)
    return str(saved_file_path)

async def view_receipt_status(job_id: str):
	job_status = await fetch_job_status(job_id)
	return job_status
