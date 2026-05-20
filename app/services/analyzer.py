# BackgroundTasks で動く、重い解析処理やOpenAI連携ロジック
import asyncio
from pathlib import Path
from app.repositories.job import JobRepository
from app.core.validate import costValidator

# todo:バックグラウンドで実行される非同期関数
async def analysis_task(job_id: str, file_path: Path):
    await JobRepository.update_job_data(job_id, {"status": "PROCESSING"})
    # ここで10秒待つ（重い解析処理のモック）
    await asyncio.sleep(10)

    # ③ 本来はここで「file_path」の画像を読み込んでOpenAIに投げる
    # 現段階では単にRedisのステータスをSUCCESS（ダミーJSON付き）に更新するだけでOK！
    dummy_result = {
        "store_name": "スーパーA",
        "total_amount": 1000,
        "items": [
            {"item_name": "卵", "unit_price": 150},
            {"item_name": "牛乳", "unit_price": 250}
        ]
    }

    is_valid, error_reason = costValidator.verify_receipt_total(
        items = dummy_result["items"], 
        total_amount =  dummy_result["total_amount"]
    )
    print(f"is_valid:{is_valid}")
    if not is_valid:
        failed_payload = {
            "status": "FAILED",
            "result": {"error": error_reason}
        }
        await JobRepository.update_job_data(job_id, failed_payload)
        return 
    
    success_payload = {
        "status": "SUCCESS",
        "result": dummy_result
    }
    await JobRepository.update_job_data(job_id, success_payload) 

async def fetch_job_status(job_id:str):
    status = await JobRepository.get_job(job_id)
    return status
