from unittest.mock import patch

from services.vector_store import BaseVectorStore
from tools.shopping_tools import (
    create_calculate_duty_day_budget_db_tool,
    create_search_past_prices_rag_tool,
)


class FakeVectorStore(BaseVectorStore):
    def __init__(self, results):
        self._results = results

    def store_bulk_items(self, job_id: str, store_name: str, items: list[dict]) -> int:
        raise NotImplementedError

    def search_similar_items(self, query_text: str, n_results: int = 3) -> list[dict]:
        return self._results


def test_search_past_prices_rag_tool_formats_results():
    tool = create_search_past_prices_rag_tool(
        FakeVectorStore(
            [
                {"item_name": "牛乳", "distance": 0.1234},
                {"item_name": "パン", "distance": 0.2345},
            ]
        )
    )

    output = tool.run("牛乳")
    assert "ChromaDBのベクトル検索で見つかった類似商品履歴" in output
    assert "商品名: 牛乳" in output
    assert "商品名: パン" in output


def test_calculate_duty_day_budget_db_tool_handles_http_error(monkeypatch):
    def fake_get(url, timeout):
        raise RuntimeError("network failure")

    monkeypatch.setattr("tools.shopping_tools.httpx.get", fake_get)

    tool = create_calculate_duty_day_budget_db_tool()
    output = tool.run("2026-01-01")

    assert "通信エラー時バックアップ" in output
