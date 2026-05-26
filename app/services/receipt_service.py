# BackgroundTasks で動く、重い解析処理やOpenAI連携ロジック
from pathlib import Path
import logging
import os
import aiofiles
import json
from fastapi.concurrency import run_in_threadpool
from app.core.config import settings
from app.repositories.job_redis import JobRepository
from app.repositories.job_mongo import MongoJobRepository
from app.repositories.receipt_tmp_data import ReceiptTmpDataRepository
from app.repositories.ocr_few_shot_repository import OcrFewShotRepository
from app.schemas.receipt import ReceiptAnalysisResponse
from app.services.call_llm import call_llm_json
from app.services.call_ocr import process_ocr_sync
from app.services.prompt_assembler import ReceiptPromptAssembler
from app.services.receipt_staging_service import ReceiptStagingService

# todo:バックグラウンドで実行される非同期関数
async def analysis_task(job_id: str, file_path: Path):
    await JobRepository.update_job_data(job_id, {"status": "PROCESSING"})
    await ReceiptTmpDataRepository.add_job_id_to_status_set("processing",job_id)
    await MongoJobRepository.update_job_data(job_id,{"status":"processing"})
    print(file_path)
    raw_ocr_text = await _convert_img_to_raw_text(file_path)
    receipt_prompt = await _process_ocr_analysis(raw_ocr_text)
    MODEL_NAME = settings.LLM_MODEL_NAME

    try:
        result_dict = await call_llm_json(
            prompt=receipt_prompt,
            ai_model=MODEL_NAME, 
            response_schema=ReceiptAnalysisResponse,
            backoff_seconds=10
        )
        print(result_dict)
    except Exception as e:
        await ReceiptTmpDataRepository.add_job_id_to_status_set("failed",job_id)

        await MongoJobRepository.update_job_data(job_id, {
            "status": "failed",
            "result": {"error": f"AI解析処理が失敗しました: {str(e)}"}
        })

        logging.error(f"AI解析処理が失敗しました: {str(e)}")
        
        await JobRepository.update_job_data(job_id, {
            "status": "FAILED",
            "result": {"error": f"AI解析処理が失敗しました: {str(e)}"}
        })


        return
    validated_data = await _validate_and_result(result_dict)
    if not validated_data:
        await ReceiptTmpDataRepository.add_job_id_to_status_set("failed", job_id)
        
        await MongoJobRepository.update_job_data(job_id, {
            "status": "failed",
            "result": {"error": "AIの出力がスキーマと一致しませんでした"}
        })

        await JobRepository.update_job_data(job_id, {
            "status": "FAILED",
            "result": {"error": "AIの出力がスキーマと一致しませんでした"}
        })
        
        return
    serialized_result_dict = validated_data.model_dump(mode="json")
    try:
        if validated_data.needs_correction:
            await ReceiptStagingService.stage_unverified_receipt(
                job_id=job_id,
                raw_ocr_text=raw_ocr_text,
                validated_data=validated_data
            )
            await ReceiptTmpDataRepository.add_job_id_to_status_set("needs_correction",job_id)
            await MongoJobRepository.update_job_data(job_id, {
                "status": "needs_correction"
            })
        else:
            await ReceiptStagingService.store_verified_receipt(
                job_id=job_id,
                raw_ocr_text=raw_ocr_text,
                validated_data=validated_data
            )
            await MongoJobRepository.update_job_data(job_id, {
                "status": "success"
            })
        await JobRepository.update_job_data(job_id, {
            "status": "SUCCESS",
            "result": serialized_result_dict
        })
    except Exception as e:
        logging.error(f"解析完了後のデータハンドリングに失敗しました: {str(e)}")
        await JobRepository.update_job_data(job_id,{
            "status": "FAILED",
            "result": {"error": f"解析完了後のデータハンドリングに失敗しました: {str(e)}"}
        })
        await MongoJobRepository.update_job_data(job_id,{
            "status": "failed",
            "result": {"error": f"解析完了後のデータハンドリングに失敗しました: {str(e)}"}
        })
    finally:
        await ReceiptTmpDataRepository.remove_job_id_from_status_set("processing",job_id)


async def _validate_and_result(result_dict: dict)-> ReceiptAnalysisResponse | None:
    """
    取得した辞書データをPydanticで型チェックし、金額計算の検証を行ってjob内容を返却する。
    """
    try:
        return ReceiptAnalysisResponse(**result_dict)
    except Exception as e:
        logging.error(f"AIの出力がスキーマと一致しませんでした: {str(e)}")
        return None
 
#画像の編集、画像の文字列読み込み
async def _convert_img_to_raw_text(img_path) -> str:
    text = await run_in_threadpool(process_ocr_sync, img_path)
    print(text)
    return text

async def _process_ocr_analysis(raw_ocr_text) -> str:
    few_shots = await OcrFewShotRepository.find_similar_shots(raw_ocr_text, limit=2)
    dynamic_prompt = ReceiptPromptAssembler.build_few_shot_receipt_prompt(raw_ocr_text, few_shots)
    return dynamic_prompt

async def fetch_job_status(job_id:str):
    job_status_data = await MongoJobRepository.get_job(job_id)
    print(f"job_status_data->{job_status_data}")
    if job_status_data == None:
        return None
    status = job_status_data.get("status")
    if status == "processing":
        logging.info("ファイルの処理中です")
        return None
    if status == "needs_correction":
        file_path = os.path.join(f"{settings.LOCAL_DATA_SET_BASE_DIR}/tmp", f"{job_id}.json") 
        if not os.path.exists(file_path):
            logging.warning(f"ファイルが見つかりません: {file_path}")
            return None
        try:
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logging.error(f"ファイル {file_path} の読み込みに失敗しました: {str(e)}")
            return None
    if status == "failed":
        logging.info("errorのためファイルなし")
        return None
    else:
        logging.info("DBに存在しないjob")
        return None