# BackgroundTasks で動く、重い解析処理やOpenAI連携ロジック
from pathlib import Path
import logging
from app.config import settings
from app.repositories.job import JobRepository
from app.core.validate import costValidator
from app.services.prompts import create_receipt_prompt
from app.schemas.receipt import ReceiptAnalysisResponse
from app.services.call_llm import call_llm_json

# todo:バックグラウンドで実行される非同期関数
async def analysis_task(job_id: str, file_path: Path):
    await JobRepository.update_job_data(job_id, {"status": "PROCESSING"})
    
    MODEL_NAME = settings.LLM_MODEL_NAME
    # ここで10秒待つ（重い解析処理のモック）
    mock_ocr_text = """
    東京都江東区夢の島2-1-2
    コンビニA 夢の島店
    領収書
    2O26年05月20日
    卵    l5O 円
    牛乳   25O 円
    ----------------
    合計   4OO 円
    """

    prompt = create_receipt_prompt(mock_ocr_text)
    try:
        result_dict = await call_llm_json(prompt, MODEL_NAME)
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
        job_result = { 
            "status": "FAILED",
            "result": {"error": f"AIの出力がスキーマと一致しませんでした: {str(e)}"}            
        }
        return job_result
    
    is_valid, error_reason = costValidator.verify_receipt_total(
        items = validated_data.items,
        total_amount = validated_data.total_amount
    )

    if not is_valid:
        job_result = {
            "status": "FAILED",
            "result": {"error": error_reason}
        }
        return job_result
    else:
        job_result = {
            "status": "SUCCESS",
            "result": validated_data.model_dump(mode="json")
        }
        return job_result

async def fetch_job_status(job_id:str):
    status = await JobRepository.get_job(job_id)
    return status
