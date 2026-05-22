import json
from datetime import datetime
import logging
from app.services.storage.factory import get_storage_client

class ReceiptFeedbackService:
    @staticmethod
    async def save_human_correction(
        job_id: str, 
        raw_ocr_text: str, 
        corrected_data: dict
    ) -> str:
        """
        人間が手動修正した実績を、現在のストレージ設定に合わせてHive形式で永続化する。
        """
        now = datetime.now()
        
        # 1. 共通のHiveパーティション文字列を生成 (year=YYYY/month=MM/day=DD)
        partition_key = f"year={now.strftime('%Y')}/month={now.strftime('%m')}/day={now.strftime('%d')}"
        file_name = f"{job_id}.json"
        
        # 2. 蓄積用共通ペイロードの作成
        archive_payload = {
            "job_id": job_id,
            "raw_ocr_text": raw_ocr_text,
            "corrected_json": json.dumps(corrected_data, ensure_ascii=False),
            "updated_at": now.isoformat()
        }
        
        # 3. 設定に応じたストレージクライアントを取得して保存
        storage_client = get_storage_client()
        try:
            saved_location = await storage_client.put_object(
                partition_key=partition_key,
                file_name=file_name,
                data=archive_payload
            )
            logging.info(f"フィードバックデータを保存しました。保存先: {saved_location}")
            return saved_location
            
        except Exception as e:
            logging.error(f"フィードバックデータの保存に失敗しました (job_id: {job_id}): {str(e)}")
            raise e
