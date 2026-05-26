# BackgroundTasks で動く、重い解析処理やOpenAI連携ロジック
from pathlib import Path
import logging
import aiofiles
import json
from fastapi.concurrency import run_in_threadpool
from app.core.config import settings
from app.repositories.job_mongo import MongoJobRepository
from app.repositories.ocr_few_shot_repository import OcrFewShotRepository
from app.schemas.receipt import ReceiptAnalysisResponse
from app.services.call_llm import call_llm_json
from app.services.call_ocr import process_ocr_sync
from app.services.prompt_assembler import ReceiptPromptAssembler
from app.services.receipt_staging_service import ReceiptStagingService

# todo:バックグラウンドで実行される非同期関数
async def analysis_task(job_id: str, file_path: Path):
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
    except Exception as e:
        await MongoJobRepository.update_job_data(job_id, {
            "status": "failed",
            "result": {"error": f"AI解析処理が失敗しました: {str(e)}"}
        })

        logging.error(f"AI解析処理が失敗しました: {str(e)}")

        return
    validated_data = await _validate_and_result(result_dict)
    if not validated_data:
        await MongoJobRepository.update_job_data(job_id, {
            "status": "failed",
            "result": {"error": "AIの出力がスキーマと一致しませんでした"}
        })  
        return
    try:
        if validated_data.needs_correction:
            await ReceiptStagingService.stage_unverified_receipt(
                job_id=job_id,
                raw_ocr_text=raw_ocr_text,
                validated_data=validated_data
            )
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
    except Exception as e:
        logging.error(f"解析完了後のデータハンドリングに失敗しました: {str(e)}")
        await MongoJobRepository.update_job_data(job_id,{
            "status": "failed",
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

    if status == "success" or status == "processing" or status == "failed":
        # success時はyyyy/mm/ddの場所に配置されているためpathをどこかに記入し取得する必要がある(下記では取得できないが、補正用のデータ取得の範囲では着手しない)
        return job_status_data
    if status == "needs_correction":
        file_path = Path(settings.LOCAL_DATA_SET_BASE_DIR) / "tmp" / f"{job_id}.json"
        if not file_path.exists():
            logging.warning(f"ジョブ {job_id} の補正ファイルが見つかりません: {file_path}")
            return None
        try:
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logging.error(f"ファイル {file_path} の読み込みに失敗しました: {str(e)}")
            return None
    else:
        logging.warning(f"ジョブ {job_id} に未知のステータス '{status}' が見つかりました。")
        return None

async def locked_receipt_status(job_id)-> str | None: 
    logging.info(f"ジョブの編集ロック処理:{job_id}")
    job_status_data = await MongoJobRepository.get_job(job_id)
    
    if job_status_data is None:
        logging.info(f"DBに存在しないジョブです: {job_id}")
        return None
    
    status = job_status_data.get("status")
    
    if status == "success" or status == "needs_correction" or status == "failed":
        # fix:redisでの処理はmongoDBに統一する
        await MongoJobRepository.update_job_data(job_id, {
            "status": "processing"
        })
        return f"locked:{job_id}"
    else:
        return f"lock済みのjob_id:{job_id}"

async def fixed_receipt_data(job_id: str, raw_ocr_text: str, fix_json:str) -> str | None:
    logging.info(f"レシートデータの修正:{job_id}")
    job_status_data = await MongoJobRepository.get_job(job_id)

    if job_status_data is None:
        logging.info(f"DBに存在しないジョブです: {job_id}")
        return f"DBに存在しないジョブです: {job_id}"

    status = job_status_data.get("status")

    if status != "processing":
        return f"処理フラグをされていないjob_idのため編集不可:{job_id}"
    if status == "processing":
        parsed_json = json.loads(fix_json)
        validated_data = await _validate_and_result(parsed_json)
        await ReceiptStagingService.store_verified_receipt(
            job_id=job_id,
            raw_ocr_text=raw_ocr_text,
            validated_data=validated_data
        )
        file_name = f"{job_id}.json"
        await ReceiptStagingService.delete_receipt_file(file_name=file_name, file_path="tmp")
        await MongoJobRepository.update_job_data(job_id, {
            "status": "success"
        })
        return "success"
