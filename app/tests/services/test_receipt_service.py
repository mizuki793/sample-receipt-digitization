import pytest
import os
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock
from app.schemas.receipt import ReceiptItem
from app.services.receipt_service import analysis_task

# 初期設定
os.environ["GEMINI_API_KEY"] = "dummy"
class FlexibleDict(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(f"'FlexibleDict' object has no attribute '{name}'")

@pytest.mark.asyncio
async def test_analysis_task_success(mocker):
    """
    LLMが正常なJSONを返却した場合に、タスクがSUCCESSで完了することを確認するテスト
    """
    #  1. LLMから返ってくる理想の擬似データを定義
    llm_raw_response_dict = {
        "store_name": "コンビニA 夢の島店",
        "store_address": "東京都江東区夢の島2-1-2",
        "transaction_date": "2026-05-20T00:00:00",
        "total_amount": 400,
        "tax": 32,
        "items": [
            {"item_name": "卵", "unit_price": 150, "quantity": 1, "category":"日配品（乳製品・豆腐・卵・パンなど）"},
            {"item_name": "牛乳", "unit_price": 250, "quantity": 1,"category":"日配品（乳製品・豆腐・卵・パンなど）" }
        ]
    }
    expected_final_output = {
        "store_name": "コンビニA 夢の島店",
        "store_address": "東京都江東区夢の島2-1-2",
        "transaction_date": "2026-05-20T00:00:00",
        "total_amount": 400,
        "tax": 32,
        "items": [
            {"item_name": "卵", "unit_price": 150, "quantity": 1, "category":"日配品（乳製品・豆腐・卵・パンなど）"},
            {"item_name": "牛乳", "unit_price": 250, "quantity": 1, "category":"日配品（乳製品・豆腐・卵・パンなど）"}
        ]      
    }
    #  2. call_llm_json 関数を外側から奪い取り、偽の非同期関数(AsyncMock)に差し替える
    # アプリケーションコード側を汚さずに、通信部分だけを完全にコントロールします
    mock_response = mocker.MagicMock()
    mock_response.choices = [
        mocker.MagicMock(message=mocker.MagicMock(content=json.dumps(llm_raw_response_dict)))
    ]

    mock_acompletion = mocker.patch(
        "app.services.call_llm.acompletion",
        new_callable=AsyncMock,
        return_value=mock_response
    )

    #  3. データベースへの保存処理(JobRepository)も、実際のDBに書き込まないようにモック化
    mock_update_job = mocker.patch(
        "app.repositories.job.JobRepository.update_job_data",
        new_callable=AsyncMock
    )

    # --- テストの実行 ---
    job_id = "123"
    dummy_path = Path("/tmp/dummy.jpg")
    
    await analysis_task(job_id=job_id, file_path=dummy_path)

    # --- 検証 (Assert) ---
    
    # 検証A: call_llm_jsonがちゃんと1回呼び出されたか確認
    mock_acompletion.assert_called_once()
    
    # 検証B: JobRepository.update_job_data が最後に 'SUCCESS' ステータスで呼ばれたか確認
    # 卵150 + 牛乳250 = 400 なので、金額バリデーションを通過して SUCCESS になるはず
    mock_update_job.assert_any_call(job_id, {"status": "PROCESSING"})
    mock_update_job.assert_any_call(job_id, {
        "status": "SUCCESS",
        "result": expected_final_output
    })

@pytest.mark.asyncio
async def test_analysis_task_failed_due_to_amount_mismatch(mocker):
    """
    LLMが返した商品の合計金額と、total_amountが一致しない場合に
    タスクが正しく 'FAILED' 状態に遷移することを確認するテスト
    """
    raw_items = [
        {"item_name":"卵", "unit_price":150, "quantity":1},
        {"item_name":"牛乳", "unit_price":250, "quantity":1}
    ]

    #  合計は 400 円のはずなのに、total_amount が 500 円になっている不整合データ
    bad_llm_output = {
        "store_name": "コンビニA 夢の島店",
        "total_amount": 500,  #不整合
        "items": [FlexibleDict(item) for item in raw_items]
    }
    mock_response = mocker.MagicMock()
    mock_response.choices = [
        mocker.MagicMock(message=mocker.MagicMock(content=json.dumps(bad_llm_output)))
    ]
    mocker.patch("app.services.call_llm.acompletion", new_callable=AsyncMock, return_value=bad_llm_output)
    mock_update_job = mocker.patch("app.repositories.job.JobRepository.update_job_data", new_callable=AsyncMock)

    # 実行
    await analysis_task("456", Path("/tmp/dummy.jpg"))

    # 検証: costValidatorによって弾かれ、ステータスが 'FAILED' になっていること
    # かつ、result.error にエラーメッセージが含まれていること
    last_call_args = mock_update_job.call_args_list[-1][0][1]
    assert last_call_args["status"] == "FAILED"
    assert "error" in last_call_args["result"]