from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
import uuid
import logging
from app.services import init_receipt_pipeline, analysis_task, view_receipt_status, view_job_ids_by_status
from app.core.validate import ImageValidator

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

# status="processing", "needs_correction", "failed", "success"
@router.get("/receipt/jobs/{status}")
async def get_job_ids_by_status(status: str):
    try:
        job_ids: list[str] = await view_job_ids_by_status(status)
        return job_ids
    except Exception as e:
        logging.error(f"RedisからのID取得に失敗しました: {str(e)}")
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
            detail="ファイルが存在しない、もしくは読み込み失敗"
        )
    return res
