import httpx
import logging
import time
import asyncio
from config import settings

logging.basicConfig(level=logging.INFO)

async def check_job_status_with_polling(job_id: str, timeout: int = 60) -> str:
    start_time = time.time()
    receipt_status_url = f"{settings.RECEIPT_URL}/jobs/detail/{job_id}"
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(receipt_status_url, timeout=5.0)
                if response.status_code == 200:
                    status = response.json().get("status") 
                    if status in ["success", "failed", "needs_correction", "processing", "locked"]:
                        return status
            except Exception as e:
                logging.warning(f"ポーリング通信エラー (Job: {job_id}): {e}")
            await asyncio.sleep(2.0)
        return "timeout"

def upload_receipt_api(file) -> dict | None:
    """1枚のファイルをアップロードしてレスポンスを返す"""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = httpx.post(f"{settings.RECEIPT_URL}/upload", files=files, timeout=45.0)
        if response.status_code in [200, 201, 202]:
            return response.json()
    except Exception as e:
        logging.error(f"アップロード通信例外: {file.name} - {e}")
    return None

def fetch_job_detail_api(job_id: str) -> dict | None:
    try:
        response = httpx.get(f"{settings.RECEIPT_URL}/jobs/detail/{job_id}", timeout=10.0)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logging.error(f"詳細データ取得失敗: {e}")
    return None

def lock_job_api(job_id: str) -> int:
    """ジョブのロックを試み、HTTPステータスコードを返す"""
    try:
        response = httpx.post(f"{settings.RECEIPT_URL}/jobs/{job_id}/lock", timeout=5.0)
        return response.status_code
    except Exception as e:
        logging.error(f"ロック通信失敗: {e}")
        return 500

def fix_job_api(job_id: str, corrected_data: dict) -> bool:
    """修正データを送信して確定（兼ロック解除）させる"""
    try:
        response = httpx.post(f"{settings.RECEIPT_URL}/jobs/{job_id}/fix", json=corrected_data, timeout=15.0)
        return response.status_code == 200
    except Exception as e:
        logging.error(f"修正確定通信失敗: {e}")
        return False
