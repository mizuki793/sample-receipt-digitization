# BackgroundTasks で動く、重い解析処理やOpenAI連携ロジック
import asyncio
from pathlib import Path
from app.repositories.job import JobRepository

# todo:バックグラウンドで実行される非同期関数
async def analysis_task(job_id: str, file_path: Path):
    await JobRepository.update_job_data(job_id, {"status": "PROCESSING"})
    # ここで30秒待つ（重い解析処理のモック）
    await asyncio.sleep(30)

    # ③ 本来はここで「file_path」の画像を読み込んでOpenAIに投げる
    # 現段階では単にRedisのステータスをSUCCESS（ダミーJSON付き）に更新するだけでOK！
    dummy_result = {
        "status": "SUCCESS",
        "result": {
            "store_name": "スーパーA",
            "items": [{"name": "卵", "price": 150}]
        }
    }
    await JobRepository.update_job_data(job_id, dummy_result) 

async def fetch_job_status(job_id:str):
    status = await JobRepository.get_job(job_id)
    return status
