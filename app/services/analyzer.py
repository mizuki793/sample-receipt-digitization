# BackgroundTasks で動く、重い解析処理やOpenAI連携ロジック
import asyncio
from pathlib import Path
from app.repositories.job import JobRepository

# todo:バックグラウンドで実行される非同期関数
async def analysis_task(job_id: str, file_path: Path):
    # ① 処理開始ステータスに更新しても良い（お好みで）
    await JobRepository.create_job(job_id, status="PENDING")
    # ② ここで5秒待つ（重い解析処理のモック）
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
    await JobRepository.create_job(job_id, dummy_result)

async def featch_jobid_status(job_id:str):
    status = await JobRepository.get_job(job_id)
    return status
