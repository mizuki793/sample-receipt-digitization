from fastapi import APIRouter, BackgroundTasks, Depends
import uuid
from app.services import init_receipt_pipeline, analysis_task, view_receipt_status
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

@router.get("/receipt/jobs/status/{job_id}")
async def view_status_receipt(job_id: str):
  res = await view_receipt_status(job_id)
  return res

