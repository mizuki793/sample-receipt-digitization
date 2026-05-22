# BackgroundTasks で動く、重い解析処理やOpenAI連携ロジック

from pathlib import Path
import logging
from fastapi.concurrency import run_in_threadpool
from app.config import settings
from app.repositories.job import JobRepository
from app.services.prompts import create_receipt_prompt
from app.schemas.receipt import ReceiptAnalysisResponse
from app.services.call_llm import call_llm_json
from app.services.call_ocr import process_ocr_sync


# todo:バックグラウンドで実行される非同期関数
async def analysis_task(job_id: str, file_path: Path):
    await JobRepository.update_job_data(job_id, {"status": "PROCESSING"})
    print(file_path)
    ocr_text = await _convert_img_to_raw_text(file_path)
    print(ocr_text)
    MODEL_NAME = settings.LLM_MODEL_NAME

    receipt_prompt = create_receipt_prompt(ocr_text)
    try:
        result_dict = await call_llm_json(
            prompt=receipt_prompt,
            ai_model=MODEL_NAME, 
            response_schema=ReceiptAnalysisResponse,
            backoff_seconds=10
        )
        print(result_dict)
    except Exception as e:
        logging.error(f"AI解析処理が失敗しました: {str(e)}")
        await JobRepository.update_job_data(job_id, {
            "status": "FAILED",
            "result": {"error": f"AI解析処理が失敗しました: {str(e)}"}
        })
        return
    job_result_status = await _validate_and_result(result_dict)

    await JobRepository.update_job_data(job_id, job_result_status) 

async def _validate_and_result(result_dict: dict) -> dict:
    """
    取得した辞書データをPydanticで型チェックし、金額計算の検証を行ってjob内容を返却する。
    """
    try:
        validated_data = ReceiptAnalysisResponse(**result_dict)
    except Exception as e:
        logging.error(f"AIの出力がスキーマと一致しませんでした: {str(e)}")
        return { 
            "status": "FAILED",
            "result": {"error": f"AIの出力がスキーマと一致しませんでした: {str(e)}"}            
        }
    
    return {
        "status": "SUCCESS",
        "result": validated_data.model_dump(mode="json")
    }
 
#画像の編集、画像の文字列読み込み
async def _convert_img_to_raw_text(img_path) -> str:
    text = await run_in_threadpool(process_ocr_sync, img_path)
    print(text)
    return text

async def fetch_job_status(job_id:str):
    status = await JobRepository.get_job(job_id)
    return status