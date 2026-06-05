import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from schemas.receipt import ReceiptAnalysisResponse, ReceiptItem
from schemas.job import JobStatus
from services.receipt_service import (
    analysis_task,
    _validate_and_result,
    _convert_img_to_raw_text,
    _process_ocr_analysis,
    fetch_job_status
)


@pytest.mark.asyncio
async def test_validate_and_result_success():
    """Pydantic validation should succeed with valid receipt data."""
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
                "category": "日配品（乳製品・豆腐・卵・パンなど）"
            }
        ],
        "needs_correction": False
    }

    result = await _validate_and_result(result_dict)

    assert result is not None
    assert isinstance(result, ReceiptAnalysisResponse)
    assert result.store_name == "テスト店舗"
    assert result.total_amount == 300


@pytest.mark.asyncio
async def test_validate_and_result_invalid_data():
    """Validation should return None for invalid data."""
    result_dict = {
        "store_name": "テスト店舗",
        # Missing required fields
    }

    result = await _validate_and_result(result_dict)

    assert result is None


@pytest.mark.asyncio
async def test_convert_img_to_raw_text():
    """Image conversion should call OCR processing."""
    img_path = Path("/tmp/test.jpg")
    
    with patch("services.receipt_service.run_in_threadpool") as mock_run:
        mock_run.return_value = "テキスト情報"

        result = await _convert_img_to_raw_text(img_path)

        assert result == "テキスト情報"
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_process_ocr_analysis():
    """OCR analysis should fetch few-shots and assemble prompt."""
    raw_text = "テスト画像の文字"
    
    with patch("services.receipt_service.OcrFewShotRepository.find_similar_shots", new_callable=AsyncMock) as mock_shots, \
         patch("services.receipt_service.ReceiptPromptAssembler.build_few_shot_receipt_prompt") as mock_prompt:
        
        mock_shots.return_value = [{"example": "data"}]
        mock_prompt.return_value = "プロンプト"

        result = await _process_ocr_analysis(raw_text)

        assert result == "プロンプト"
        mock_shots.assert_called_once_with(raw_text, limit=2)


@pytest.mark.asyncio
async def test_fetch_job_status_processing():
    """Fetch processing job status from MongoDB."""
    job_id = "test-job-123"
    
    with patch("services.receipt_service.MongoJobRepository.get_job", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "_id": "test-id",
            "status": "processing",
            "created_at": "2026-05-20T12:00:00"
        }

        result = await fetch_job_status(job_id)

        assert result is not None
        assert result["status"] == "processing"
        mock_get.assert_called_once_with(job_id)


@pytest.mark.asyncio
async def test_fetch_job_status_not_found():
    """Return None when job not found."""
    job_id = "nonexistent-job"
    
    with patch("services.receipt_service.MongoJobRepository.get_job", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        result = await fetch_job_status(job_id)

        assert result is None


@pytest.mark.asyncio
async def test_analysis_task_success():
    """Analysis task should process image and update job status."""
    job_id = "test-job"
    file_path = Path("/tmp/test.jpg")
    
    with patch("services.receipt_service._convert_img_to_raw_text", new_callable=AsyncMock) as mock_convert, \
         patch("services.receipt_service._process_ocr_analysis", new_callable=AsyncMock) as mock_ocr, \
         patch("services.receipt_service.call_llm_json", new_callable=AsyncMock) as mock_llm, \
         patch("services.receipt_service.ReceiptStagingService.stage_unverified_receipt", new_callable=AsyncMock) as mock_stage, \
         patch("services.receipt_service.ReceiptStagingService.store_verified_receipt", new_callable=AsyncMock) as mock_store, \
         patch("services.receipt_service.MongoJobRepository.update_job_data", new_callable=AsyncMock) as mock_update:
        
        mock_convert.return_value = "raw ocr text"
        mock_ocr.return_value = "assembled prompt"
        
        result_dict = {
            "store_name": "テスト店舗",
            "store_address": "東京都渋谷区",
            "transaction_date": "2026-05-20T12:00:00",
            "total_amount": 1000,
            "tax": 80,
            "items": [],
            "needs_correction": False
        }
        mock_llm.return_value = result_dict

        await analysis_task(job_id, file_path)

        # Verify staging and storage called
        mock_stage.assert_called_once()
        mock_store.assert_called_once()
        # Verify final status update to SUCCESS
        calls = mock_update.call_args_list
        final_call = calls[-1]
        assert final_call[0][1]["status"] == JobStatus.SUCCESS.value

# os.environ["GEMINI_API_KEY"] = "dummy"
# class FlexibleDict(dict):
#     def __getattr__(self, name):
#         if name in self:
#             return self[name]
#         raise AttributeError(f"'FlexibleDict' object has no attribute '{name}'")

# @pytest.mark.asyncio
# async def test_analysis_task_success(mocker):
#     """
#     LLMが正常なJSONを返却した場合に、タスクがSUCCESSで完了することを確認するテスト
#     """
#     #  1. LLMから返ってくる理想の擬似データを定義
#     llm_raw_response_dict = {
#         "store_name": "コンビニA 夢の島店",
#         "store_address": "東京都江東区夢の島2-1-2",
#         "transaction_date": "2026-05-20T00:00:00",
#         "total_amount": 400,
#         "tax": 32,
#         "items": [
#             {"item_name": "卵", "unit_price": 150, "quantity": 1, "category":"日配品（乳製品・豆腐・卵・パンなど）"},
#             {"item_name": "牛乳", "unit_price": 250, "quantity": 1,"category":"日配品（乳製品・豆腐・卵・パンなど）" }
#         ]
#     }
#     expected_final_output = {
#         "store_name": "コンビニA 夢の島店",
#         "store_address": "東京都江東区夢の島2-1-2",
#         "transaction_date": "2026-05-20T00:00:00",
#         "total_amount": 400,
#         "tax": 32,
#         "items": [
#             {"item_name": "卵", "unit_price": 150, "quantity": 1, "category":"日配品（乳製品・豆腐・卵・パンなど）"},
#             {"item_name": "牛乳", "unit_price": 250, "quantity": 1, "category":"日配品（乳製品・豆腐・卵・パンなど）"}
#         ]      
#     }
#     #  2. call_llm_json 関数を外側から奪い取り、偽の非同期関数(AsyncMock)に差し替える
#     # アプリケーションコード側を汚さずに、通信部分だけを完全にコントロールします
#     mock_response = mocker.MagicMock()
#     mock_response.choices = [
#         mocker.MagicMock(message=mocker.MagicMock(content=json.dumps(llm_raw_response_dict)))
#     ]

#     mock_acompletion = mocker.patch(
#         "services.call_llm.acompletion",
#         new_callable=AsyncMock,
#         return_value=mock_response
#     )

#     #  3. データベースへの保存処理(JobRepository)も、実際のDBに書き込まないようにモック化
#     mock_update_job = mocker.patch(
#         "repositories.job.JobRepository.update_job_data",
#         new_callable=AsyncMock
#     )

#     # --- テストの実行 ---
#     job_id = "123"
#     dummy_path = Path("/tmp/dummy.jpg")
    
#     await analysis_task(job_id=job_id, file_path=dummy_path)

#     # --- 検証 (Assert) ---
    
#     # 検証A: call_llm_jsonがちゃんと1回呼び出されたか確認
#     mock_acompletion.assert_called_once()
    
#     # 検証B: JobRepository.update_job_data が最後に 'SUCCESS' ステータスで呼ばれたか確認
#     # 卵150 + 牛乳250 = 400 なので、金額バリデーションを通過して SUCCESS になるはず
#     mock_update_job.assert_any_call(job_id, {"status": "PROCESSING"})
#     mock_update_job.assert_any_call(job_id, {
#         "status": "SUCCESS",
#         "result": expected_final_output
#     })

# @pytest.mark.asyncio
# async def test_analysis_task_failed_due_to_amount_mismatch(mocker):
#     """
#     LLMが返した商品の合計金額と、total_amountが一致しない場合に
#     タスクが正しく 'FAILED' 状態に遷移することを確認するテスト
#     """
#     raw_items = [
#         {"item_name":"卵", "unit_price":150, "quantity":1},
#         {"item_name":"牛乳", "unit_price":250, "quantity":1}
#     ]

#     #  合計は 400 円のはずなのに、total_amount が 500 円になっている不整合データ
#     bad_llm_output = {
#         "store_name": "コンビニA 夢の島店",
#         "total_amount": 500,  #不整合
#         "items": [FlexibleDict(item) for item in raw_items]
#     }
#     mock_response = mocker.MagicMock()
#     mock_response.choices = [
#         mocker.MagicMock(message=mocker.MagicMock(content=json.dumps(bad_llm_output)))
#     ]
#     mocker.patch("services.call_llm.acompletion", new_callable=AsyncMock, return_value=bad_llm_output)
#     mock_update_job = mocker.patch("repositories.job.JobRepository.update_job_data", new_callable=AsyncMock)

#     # 実行
#     await analysis_task("456", Path("/tmp/dummy.jpg"))

#     # 検証: costValidatorによって弾かれ、ステータスが 'FAILED' になっていること
#     # かつ、result.error にエラーメッセージが含まれていること
#     last_call_args = mock_update_job.call_args_list[-1][0][1]
#     assert last_call_args["status"] == "FAILED"
#     assert "error" in last_call_args["result"]