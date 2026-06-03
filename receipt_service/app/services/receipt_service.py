# BackgroundTasks で動く、重い解析処理やOpenAI連携ロジック
from pathlib import Path
from bson import ObjectId
import logging
import aiofiles
import json
import httpx
from fastapi.encoders import jsonable_encoder
from fastapi.concurrency import run_in_threadpool
from core.config import settings
from repositories.job_mongo import MongoJobRepository
from repositories.ocr_few_shot_repository import OcrFewShotRepository
from schemas.receipt import ReceiptAnalysisResponse
from services.call_llm import call_llm_json
from services.call_ocr import process_ocr_sync
from services.prompt_assembler import ReceiptPromptAssembler
from services.receipt_staging_service import ReceiptStagingService
from schemas.job import JobStatus

# todo:バックグラウンドで実行される非同期関数
async def analysis_task(job_id: str, file_path: Path):
    raw_ocr_text = await _convert_img_to_raw_text(file_path)
    receipt_prompt = await _process_ocr_analysis(raw_ocr_text)
    MODEL_NAME = settings.LLM_MODEL_NAME

    try:
        # result_dict = await call_llm_json(
        #     prompt=receipt_prompt,
        #     ai_model=MODEL_NAME, 
        #     response_schema=ReceiptAnalysisResponse,
        #     max_retries=5,
        #     backoff_seconds=30
        # )
        # AIで解釈する必要がない疎通の場合は下記のコメントアウトを外し、実行する
        result_dict = {
            "store_name": "セブン-イレフブン 夢の島店",
            "store_address": "東京都江東区夢の島2-1-2",
            "transaction_date": "2026-05-20T12:11:00",
            "total_amount": 432,
            "tax": 32,
            "items": [
                {"item_name": "卵", "unit_price": 150, "quantity": 1, "category":"日配品（乳製品・豆腐・卵・パンなど）"},
                {"item_name": "牛乳", "unit_price": 250, "quantity": 1,"category":"日配品（乳製品・豆腐・卵・パンなど）" }
            ]
        }
    except Exception as e:
        await MongoJobRepository.update_job_data(job_id, {
            "status": JobStatus.FAILED.value, 
            "result": {"error": f"AI解析処理が失敗しました: {str(e)}"}
        })
        logging.error(f"AI解析処理が失敗しました: {str(e)}")
        return
    
    validated_data = await _validate_and_result(result_dict)
    if not validated_data:
        await MongoJobRepository.update_job_data(job_id, {
            "status": JobStatus.FAILED.value, 
            "result": {"error": "AIの出力がスキーマと一致しませんでした"}
        })  
        return
    try:
        await ReceiptStagingService.stage_unverified_receipt(
            job_id=job_id,
            raw_ocr_text=raw_ocr_text,
            validated_data=validated_data
        )

        if validated_data.needs_correction:
            await MongoJobRepository.update_job_data(job_id, {
                "status": JobStatus.NEEDS_CORRECTION.value
            })
        else:
            await ReceiptStagingService.store_verified_receipt(
                job_id=job_id,
                raw_ocr_text=raw_ocr_text,
                validated_data=validated_data
            )
            await MongoJobRepository.update_job_data(job_id, {
                "status": JobStatus.SUCCESS.value
            })
            async with httpx.AsyncClient() as client:
                payload = {
                    "job_id": job_id,
                    "store_name": validated_data.store_name,
                    "items": validated_data.items
                }
                await client.post(
                    f"{settings.BACKEND_URL}/embeddings",
                    json = jsonable_encoder(payload)
                )
    except Exception as e:
        logging.error(f"解析完了後のデータハンドリングに失敗しました: {str(e)}")
        await MongoJobRepository.update_job_data(job_id,{
            "status": JobStatus.FAILED.value, 
            "result": {"error": f"解析完了後のデータハンドリングに失敗しました: {str(e)}"}
        })


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
    return text

async def _process_ocr_analysis(raw_ocr_text) -> str:
    few_shots = await OcrFewShotRepository.find_similar_shots(raw_ocr_text, limit=2)
    dynamic_prompt = ReceiptPromptAssembler.build_few_shot_receipt_prompt(raw_ocr_text, few_shots)
    return dynamic_prompt

async def fetch_job_status(job_id:str)-> dict | None: 
    job_status_data = await MongoJobRepository.get_job(job_id)
    
    if job_status_data is None:
        logging.info(f"DBに存在しないジョブです: {job_id}")
        return None
    
    status = job_status_data.get("status")
    logging.debug(f"Job {job_id} status: {status}")
    if status == "processing":
        cleaned_data = {}
        for key, value in job_status_data.items():
            if isinstance(value, ObjectId):
                cleaned_data[key] = str(value)
            else:
                cleaned_data[key] = value
        print(f"cleaned_data:{cleaned_data}")
        return cleaned_data
    elif status in ["success", "needs_correction", "failed","locked"]:
        file_path = Path(settings.LOCAL_DATA_SET_BASE_DIR) / "tmp" / f"{job_id}.json"
        if not file_path.exists():
            logging.warning(f"ジョブ {job_id} の補正ファイルが見つかりません: {file_path}")
            return None
        try:
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                if isinstance(data, dict):
                    data["status"] = status
                return data
        except Exception as e:
            logging.error(f"ファイル {file_path} の読み込みに失敗しました: {str(e)}")
            return None
    else:
        logging.warning(f"ジョブ {job_id} に未知のステータス '{status}' が見つかりました。")
        return job_status_data

async def lock_receipt_job(job_id)-> str | None: 
    logging.info(f"ジョブの編集ロック処理:{job_id}")
    job_status_data = await MongoJobRepository.get_job(job_id)
    
    if job_status_data is None:
        logging.info(f"DBに存在しないジョブです: {job_id}")
        return None
    
    status = job_status_data.get("status")
    
    if status == JobStatus.LOCKED.value:
        return {
            "job_id": job_id, 
            "status": JobStatus.LOCKED.value, 
            "message": "このジョブは既にロックされています。"
        }
    elif status in [JobStatus.SUCCESS.value, JobStatus.NEEDS_CORRECTION.value, JobStatus.FAILED.value]:
        updated = await MongoJobRepository.update_job_status_atomically(
            job_id, 
            JobStatus(status),
            JobStatus.LOCKED
        )
        if updated:
            return {
                "job_id": job_id,
                "status": JobStatus.LOCKED.value,
                "message": "ジョブが正常にロックされました。"
            }
        else:
            # 更新に失敗した場合、別のプロセスが既に状態を変更した可能性がある
            logging.warning(f"ジョブ {job_id} のロック中に競合が発生しました。現在のステータス: {status}")
            # クライアントにはエラーを返す
            raise ValueError("ジョブのロックに失敗しました。競合が発生した可能性があります。")
    else:
        logging.warning(f"ジョブ {job_id} に予期しないステータス '{status}' が見つかりました。")
        raise ValueError(f"無効なジョブステータス: {status}")

async def fix_receipt_job_data(job_id: str, raw_ocr_text: str, fixed_data: ReceiptAnalysisResponse)-> str | None:
    logging.info(f"レシートデータの修正:{job_id}")
    job_status_data = await MongoJobRepository.get_job(job_id)

    if job_status_data is None:
        logging.info(f"DBに存在しないジョブです: {job_id}")
        return None 

    status = job_status_data.get("status")

    if status != JobStatus.LOCKED.value:
        return {
            "job_id": job_id,
            "status": status, 
            "message": f"処理フラグがされていないjob_idのため編集不可: {job_id}"
        }

    await ReceiptStagingService.store_verified_receipt(
        job_id=job_id,
        raw_ocr_text=raw_ocr_text,
        validated_data=fixed_data
    )

    # file_name = f"{job_id}.json"
    # await ReceiptStagingService.delete_receipt_file(file_name=file_name, file_path="tmp")
    await MongoJobRepository.update_job_data(job_id, {
        "status": JobStatus.SUCCESS.value
    })

    async with httpx.AsyncClient() as client:
        payload = {
            "job_id": job_id,
            "store_name": fixed_data.store_name,
            "items": fixed_data.items
        }
        await client.post(
            f"{settings.BACKEND_URL}/embeddings",
            json = jsonable_encoder(payload)
        )
    
    return {
        "job_id": job_id,
        "status": JobStatus.SUCCESS.value,
        "message": "レシートデータが正常に修正されました。"
    }
