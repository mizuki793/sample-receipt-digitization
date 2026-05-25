import os
import redis.asyncio as aioredis
from app.core.config import settings
import logging
from app.schemas.receipt import ReceiptTmpStorageData, ReceiptAnalysisResponse,ReceiptStorageData
from app.services.storage.factory import get_storage_client
from datetime import datetime

# 適切なストレージ領域へ安全かつクリーンな状態で書き出す（シリアライズして保存する）クラス
class ReceiptStagingService:
    @staticmethod
    async def stage_unverified_receipt(
        job_id: str, 
        raw_ocr_text: str, 
        validated_data: ReceiptAnalysisResponse
    ) -> str:
        
        """
        金額不整合などで手動補正が必要なデータを、アプリ内ストレージ（ファイル）に保存し、
        Redisのneeds_correctionインデックスセットにIDを追加する。
        """
        storage_client = get_storage_client()

        storage_data = ReceiptTmpStorageData(
            job_id=job_id,
            raw_ocr_text=raw_ocr_text,
            analysis_result=validated_data
        )

        cleaned_dict = storage_data.model_dump(mode="json", by_alias=True)

        saved_location = await storage_client.put_object(
            partition_key="tmp",
            file_name=f"{job_id}.json",
            data=cleaned_dict
        )
        return saved_location

    @staticmethod
    async def store_verified_receipt(
        job_id: str,
        raw_ocr_text: str, 
        validated_data: ReceiptAnalysisResponse
    ) -> str:
        """
        検証・補正が完了した成功データを、将来のDuckDBパースや
        Few-Shot検索に備えてHive形式のパーティション構造で永続化保存する。
        出力構造: /app/data/archive/year=YYYY/month=MM/day=DD/{job_id}.json
        """
        storage_client = get_storage_client()
        now = datetime.now()
        
        storage_data = ReceiptStorageData(
            job_id=job_id,
            raw_ocr_text=raw_ocr_text,
            corrected_json=ReceiptAnalysisResponse,
            updated_at=now.isoformat()
        )

        cleaned_dict = storage_data.model_dump(mode="json", by_alias=True)

        transaction_date = validated_data.transaction_date
        partition_key =  f"archive/{transaction_date.strftime('%Y')}/{transaction_date.strftime('%m')}/{transaction_date.strftime('%d')}"
        file_name = f"{job_id}.json"

        try:
            saved_location = await storage_client.put_object(
                partition_key=partition_key,
                file_name=file_name,
                data=cleaned_dict
            )
            logging.info(f"フィードバックデータを保存しました。保存先: {saved_location}")
            return saved_location
        
        except Exception as e:
            logging.error(f"フィードバックデータの保存に失敗しました (job_id: {job_id}): {str(e)}")
            raise e