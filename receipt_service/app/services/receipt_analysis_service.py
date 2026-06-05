from pathlib import Path
from core.logging_config import logger
import httpx
from fastapi.encoders import jsonable_encoder
from fastapi.concurrency import run_in_threadpool
from core.config import settings
from repositories.job_mongo import MongoJobRepository
from repositories.ocr_few_shot_repository import OcrFewShotRepository
from schemas.receipt import ReceiptAnalysisResponse
from schemas.job import JobStatus
from services.call_llm import call_llm_json
from services.call_ocr import process_ocr_sync
from services.prompt_assembler import ReceiptPromptAssembler
from services.receipt_staging_service import ReceiptStagingService


class ReceiptAnalysisService:
    DEFAULT_LLM_RETRY_COUNT = 5
    DEFAULT_LLM_BACKOFF_SECONDS = 30

    @classmethod
    async def analysis_task(cls, job_id: str, file_path: Path):
        raw_ocr_text = await cls._convert_img_to_raw_text(file_path)
        receipt_prompt = await cls._process_ocr_analysis(raw_ocr_text)
        model_name = settings.LLM_MODEL_NAME

        try:
            result_dict = await cls._call_llm_json(receipt_prompt, model_name)
        except Exception as e:
            await cls._mark_job_failed(job_id, f"AI解析処理が失敗しました: {e}")
            logger.error(f"AI解析処理が失敗しました: {e}")
            return

        validated_data = await cls._validate_and_result(result_dict)
        if not validated_data:
            await cls._mark_job_failed(job_id, "AIの出力がスキーマと一致しませんでした")
            return

        await cls._handle_analysis_result(job_id, raw_ocr_text, validated_data)

    @classmethod
    async def _call_llm_json(cls, prompt: str, ai_model: str) -> dict:
        return await call_llm_json(
            prompt=prompt,
            ai_model=ai_model,
            response_schema=ReceiptAnalysisResponse,
            max_retries=cls.DEFAULT_LLM_RETRY_COUNT,
            backoff_seconds=cls.DEFAULT_LLM_BACKOFF_SECONDS,
        )

    @classmethod
    async def _mark_job_failed(cls, job_id: str, error_message: str):
        await MongoJobRepository.update_job_data(job_id, {
            "status": JobStatus.FAILED.value,
            "result": {"error": error_message},
        })

    @classmethod
    async def _handle_analysis_result(
        cls,
        job_id: str,
        raw_ocr_text: str,
        validated_data: ReceiptAnalysisResponse,
    ):
        try:
            await ReceiptStagingService.stage_unverified_receipt(
                job_id=job_id,
                raw_ocr_text=raw_ocr_text,
                validated_data=validated_data,
            )

            if validated_data.needs_correction:
                await MongoJobRepository.update_job_data(job_id, {
                    "status": JobStatus.NEEDS_CORRECTION.value,
                })
                return

            await cls._handle_verified_data(job_id, raw_ocr_text, validated_data)
        except Exception as e:
            logger.error(f"解析完了後のデータハンドリングに失敗しました: {e}")
            await cls._mark_job_failed(
                job_id,
                f"解析完了後のデータハンドリングに失敗しました: {e}",
            )

    @classmethod
    async def _handle_verified_data(
        cls,
        job_id: str,
        raw_ocr_text: str,
        validated_data: ReceiptAnalysisResponse,
    ):
        await ReceiptStagingService.store_verified_receipt(
            job_id=job_id,
            raw_ocr_text=raw_ocr_text,
            validated_data=validated_data,
        )
        await MongoJobRepository.update_job_data(job_id, {
            "status": JobStatus.SUCCESS.value,
        })
        await cls._send_embeddings(job_id, validated_data)

    @classmethod
    async def _send_embeddings(
        cls,
        job_id: str,
        validated_data: ReceiptAnalysisResponse,
    ):
        async with httpx.AsyncClient() as client:
            payload = {
                "job_id": job_id,
                "store_name": validated_data.store_name,
                "items": validated_data.items,
            }
            await client.post(
                f"{settings.BACKEND_URL}/embeddings",
                json=jsonable_encoder(payload),
            )

    @staticmethod
    async def _validate_and_result(result_dict: dict) -> ReceiptAnalysisResponse | None:
        """
        取得した辞書データをPydanticで型チェックし、金額計算の検証を行ってjob内容を返却する。
        """
        try:
            return ReceiptAnalysisResponse(**result_dict)
        except Exception as e:
            logger.error(f"AIの出力がスキーマと一致しませんでした: {e}")
            return None

    @staticmethod
    async def _convert_img_to_raw_text(img_path: Path) -> str:
        return await run_in_threadpool(process_ocr_sync, img_path)

    @staticmethod
    async def _process_ocr_analysis(raw_ocr_text: str) -> str:
        few_shots = await OcrFewShotRepository.find_similar_shots(raw_ocr_text, limit=2)
        return ReceiptPromptAssembler.build_few_shot_receipt_prompt(raw_ocr_text, few_shots)
