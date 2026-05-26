from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
import uuid
import logging
from app.services import init_receipt_pipeline, analysis_task, view_receipt_status, view_job_ids_by_status, lock_receipt_job, fix_receipt_job_data
from app.services.receipt_search import ReceiptSearchService
from app.core.validate import ImageValidator
from app.schemas.receipt import ReceiptFixRequest
from app.schemas.job import JobStatus
from app.schemas.search import SearchRequest, SearchStatsResponse

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
    try:
        res = await lock_receipt_job(job_id)
        if res == None:
            raise HTTPException(
                status_code=404,
                detail=f"指定されたジョブID '{job_id}' のデータが見つかりませんでした。"
            )
        if "message" in res and "ロックに失敗しました" in res["message"]:
            raise HTTPException(
                status_code=409,
                detail=res["message"]
            )        
        return res
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logging.error(f"ジョブのロック処理に失敗しました: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="ジョブのロック処理中に予期せぬエラーが発生しました。"
        )

@router.post("/receipt/jobs/{job_id}/fix")
async def update_job_detail(job_id: str, request_body: ReceiptFixRequest): 
    try:
        res = await fix_receipt_job_data(job_id, request_body.raw_ocr_text, request_body.fixed_data)
        if res is None:
            raise HTTPException(
                status_code=404,
                detail=f"指定されたジョブID '{job_id}' のデータが見つかりませんでした。"
            )
        if "message" in res and "編集不可" in res["message"]:
            raise HTTPException(
                status_code=400,
                detail=res["message"]
            )
        return res
    except Exception as e:
        logging.error(f"ジョブデータの修正に失敗しました: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="ジョブデータの修正中に予期せぬエラーが発生しました。"
        )

@router.post("receipts/search")
async def search_receipt_stats(payload: SearchRequest):
    try:
        stats = await ReceiptSearchService.search_item_stats(payload.query)
        return stats
    except Exception as e:
        # 予期せぬエラーのハンドリング
        raise HTTPException(
            status_code=500,
            detail="統計情報の集計中に予期せぬエラーが発生しました。"
        )
