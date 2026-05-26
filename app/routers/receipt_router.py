from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
import uuid
import logging
from app.services import init_receipt_pipeline, analysis_task, view_receipt_status, view_job_ids_by_status, lock_receipt_job, fix_receipt_job_data
from app.core.validate import ImageValidator
from app.schemas.receipt import ReceiptFixRequest
from app.schemas.job import JobStatus

router = APIRouter(
    prefix="/api/v1",
    responses={404: {"description": "Not found"}}
)

@router.get("/health")
def read_root():
    return{"status": "ok"}

@router.post("/receipt/upload", status_code=202)
async def analyses_receipts(
    background_tasks: BackgroundTasks,
    validated_data: ImageValidator = Depends()
):
    job_id = str(uuid.uuid4())
    saved_file_path = await init_receipt_pipeline(validated_data.file, job_id)
    background_tasks.add_task(analysis_task, job_id, saved_file_path)
    return { "job_id": job_id }

@router.get("/receipt/jobs/{status}")
async def get_job_ids_by_status(status: JobStatus):
    try:
        job_ids: list[str] = await view_job_ids_by_status(status)
        return job_ids
    except Exception as e:
        logging.error(f"ID取得に失敗しました: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="インデックスの取得に失敗しました"
        )

@router.get("/receipt/jobs/detail/{job_id}")
async def get_job_detail(job_id: str):
    res = await view_receipt_status(job_id)
    if res == None:
        raise HTTPException(
            status_code=404,
            detail=f"指定されたジョブID '{job_id}' のデータが見つかりませんでした。"
        )
    return res

@router.post("/receipt/jobs/{job_id}/lock")
async def lock_job_status(job_id: str):
    res = await lock_receipt_job(job_id)
    if res == None:
        raise HTTPException(
            status_code=404,
            detail=f"指定されたジョブID '{job_id}' のデータが見つかりませんでした。"
        )
    return res

@router.post("/receipt/jobs/{job_id}/fix")
async def update_job_detail(job_id: str, request_body: ReceiptFixRequest): 
    res = await fix_receipt_job_data(job_id, request_body.raw_ocr_text, request_body.fixed_data)
    return res
