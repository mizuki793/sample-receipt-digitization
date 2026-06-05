import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path
from schemas.receipt import ReceiptAnalysisResponse
from schemas.job import JobStatus
from services.receipt_analysis_service import ReceiptAnalysisService


@pytest.mark.asyncio
async def test_validate_and_result_success():
    result_dict = {
        "store_name": "テスト店舗",
        "store_address": "東京都渋谷区",
        "transaction_date": "2026-05-20T12:00:00",
        "total_amount": 300,
        "tax": 24,
        "items": [
            {
                "item_name": "卵",
                "unit_price": 150,
                "quantity": 2,
                "category": "日配品（乳製品・豆腐・卵・パンなど）",
            }
        ],
        "needs_correction": False,
    }

    result = await ReceiptAnalysisService._validate_and_result(result_dict)

    assert result is not None
    assert isinstance(result, ReceiptAnalysisResponse)
    assert result.store_name == "テスト店舗"
    assert result.total_amount == 300


@pytest.mark.asyncio
async def test_validate_and_result_invalid_data():
    result_dict = {"store_name": "テスト店舗"}

    result = await ReceiptAnalysisService._validate_and_result(result_dict)

    assert result is None


@pytest.mark.asyncio
async def test_validate_and_result_sets_needs_correction_when_amount_mismatch():
    result_dict = {
        "store_name": "テスト店舗",
        "store_address": "東京都渋谷区",
        "transaction_date": "2026-05-20T12:00:00",
        "total_amount": 300,
        "tax": 0,
        "items": [
            {"item_name": "卵", "unit_price": 150, "quantity": 1, "category": "日配品（乳製品・豆腐・卵・パンなど）"},
            {"item_name": "牛乳", "unit_price": 100, "quantity": 1, "category": "飲料・お酒"}
        ],
        "needs_correction": False,
    }

    result = await ReceiptAnalysisService._validate_and_result(result_dict)

    assert result is not None
    assert result.needs_correction is True


@pytest.mark.asyncio
async def test_convert_img_to_raw_text():
    img_path = Path("/tmp/test.jpg")

    with patch("services.receipt_analysis_service.run_in_threadpool") as mock_run:
        mock_run.return_value = "テキスト情報"

        result = await ReceiptAnalysisService._convert_img_to_raw_text(img_path)

        assert result == "テキスト情報"
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_process_ocr_analysis():
    raw_text = "テスト画像の文字"

    with patch("services.receipt_analysis_service.OcrFewShotRepository.find_similar_shots", new_callable=AsyncMock) as mock_shots, \
         patch("services.receipt_analysis_service.ReceiptPromptAssembler.build_few_shot_receipt_prompt") as mock_prompt:
        mock_shots.return_value = [{"example": "data"}]
        mock_prompt.return_value = "プロンプト"

        result = await ReceiptAnalysisService._process_ocr_analysis(raw_text)

        assert result == "プロンプト"
        mock_shots.assert_called_once_with(raw_text, limit=2)


@pytest.mark.asyncio
async def test_analysis_task_success():
    job_id = "test-job"
    file_path = Path("/tmp/test.jpg")

    with patch("services.receipt_analysis_service.ReceiptAnalysisService._convert_img_to_raw_text", new_callable=AsyncMock) as mock_convert, \
         patch("services.receipt_analysis_service.ReceiptAnalysisService._process_ocr_analysis", new_callable=AsyncMock) as mock_ocr, \
         patch("services.receipt_analysis_service.call_llm_json", new_callable=AsyncMock) as mock_llm, \
         patch("services.receipt_analysis_service.ReceiptStagingService.stage_unverified_receipt", new_callable=AsyncMock) as mock_stage, \
         patch("services.receipt_analysis_service.ReceiptStagingService.store_verified_receipt", new_callable=AsyncMock) as mock_store, \
         patch("services.receipt_analysis_service.MongoJobRepository.update_job_data", new_callable=AsyncMock) as mock_update:
        mock_convert.return_value = "raw ocr text"
        mock_ocr.return_value = "assembled prompt"
        mock_llm.return_value = {
            "store_name": "テスト店舗",
            "store_address": "東京都渋谷区",
            "transaction_date": "2026-05-20T12:00:00",
            "total_amount": 1000,
            "tax": 80,
            "items": [
                {"item_name": "卵", "unit_price": 920, "quantity": 1, "category": "日配品（乳製品・豆腐・卵・パンなど）"}
            ],
            "needs_correction": False,
        }

        await ReceiptAnalysisService.analysis_task(job_id, file_path)

        mock_stage.assert_called_once()
        mock_store.assert_called_once()
        final_call = mock_update.call_args_list[-1]
        assert final_call[0][1]["status"] == JobStatus.SUCCESS.value


@pytest.mark.asyncio
async def test_analysis_task_failure_updates_job_to_failed():
    job_id = "failed-job"
    file_path = Path("/tmp/test.jpg")

    with patch("services.receipt_analysis_service.ReceiptAnalysisService._convert_img_to_raw_text", new_callable=AsyncMock) as mock_convert, \
         patch("services.receipt_analysis_service.ReceiptAnalysisService._process_ocr_analysis", new_callable=AsyncMock) as mock_ocr, \
         patch("services.receipt_analysis_service.call_llm_json", new_callable=AsyncMock) as mock_llm, \
         patch("services.receipt_analysis_service.MongoJobRepository.update_job_data", new_callable=AsyncMock) as mock_update:
        mock_convert.return_value = "raw ocr text"
        mock_ocr.return_value = "assembled prompt"
        mock_llm.side_effect = Exception("LLM unavailable")

        await ReceiptAnalysisService.analysis_task(job_id, file_path)

        mock_update.assert_called_once()
        call_args = mock_update.call_args[0][1]
        assert call_args["status"] == JobStatus.FAILED.value
        assert "AI解析処理が失敗しました" in call_args["result"]["error"]


@pytest.mark.asyncio
async def test_analysis_task_needs_correction_updates_needs_correction():
    job_id = "correction-job"
    file_path = Path("/tmp/test.jpg")

    with patch("services.receipt_analysis_service.ReceiptAnalysisService._convert_img_to_raw_text", new_callable=AsyncMock) as mock_convert, \
         patch("services.receipt_analysis_service.ReceiptAnalysisService._process_ocr_analysis", new_callable=AsyncMock) as mock_ocr, \
         patch("services.receipt_analysis_service.call_llm_json", new_callable=AsyncMock) as mock_llm, \
         patch("services.receipt_analysis_service.ReceiptStagingService.stage_unverified_receipt", new_callable=AsyncMock) as mock_stage, \
         patch("services.receipt_analysis_service.ReceiptStagingService.store_verified_receipt", new_callable=AsyncMock) as mock_store, \
         patch("services.receipt_analysis_service.MongoJobRepository.update_job_data", new_callable=AsyncMock) as mock_update:
        mock_convert.return_value = "raw ocr text"
        mock_ocr.return_value = "assembled prompt"
        mock_llm.return_value = {
            "store_name": "テスト店舗",
            "store_address": "東京都渋谷区",
            "transaction_date": "2026-05-20T12:00:00",
            "total_amount": 300,
            "tax": 0,
            "items": [
                {"item_name": "卵", "unit_price": 150, "quantity": 1, "category": "日配品（乳製品・豆腐・卵・パンなど）"},
                {"item_name": "牛乳", "unit_price": 100, "quantity": 1, "category": "飲料・お酒"}
            ],
        }

        await ReceiptAnalysisService.analysis_task(job_id, file_path)

        mock_stage.assert_called_once()
        mock_store.assert_not_called()
        assert mock_update.call_args_list[-1][0][1]["status"] == JobStatus.NEEDS_CORRECTION.value
