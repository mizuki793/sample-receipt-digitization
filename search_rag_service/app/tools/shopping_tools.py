from langchain_core.tools import tool
import httpx
import logging
from services.vector_store import BaseVectorStore


def create_search_past_prices_rag_tool(vector_store: BaseVectorStore):
    @tool
    def search_past_prices_rag(query: str) -> str:
        """
        過去のレシート履歴（ChromaDB）から、商品の過去最安値や店舗ごとの価格情報を検索します。
        """
        logging.info(f"[RAG Tool] ChromaDBへクエリを送信中: '{query}'")

        try:
            results = vector_store.search_similar_items(query_text=query, n_results=3)
            if not results:
                return f"「{query}」に関する過去のレシート履歴（商品名）は見つかりませんでした。"

            context_parts = []
            for i, res in enumerate(results):
                item_name = res["item_name"]
                distance = res["distance"]
                context_parts.append(f"【履歴 {i+1}】 商品名: {item_name} (類似度距離: {distance:.4f})")

            formatted_context = "\n".join(context_parts)
            logging.info(f"[RAG Tool] 検索成功。{len(results)}件の類似商品を検知しました。")
            return f"ChromaDBのベクトル検索で見つかった類似商品履歴:\n\n{formatted_context}"

        except Exception as e:
            logging.error(f"[RAG Tool] 検索中にエラーが発生しました: {e}")
            return f"過去の履歴検索中にシステムエラーが発生しました（詳細: {e}）。"

    return search_past_prices_rag


def create_calculate_duty_day_budget_db_tool():
    @tool
    def calculate_duty_day_budget_db(duty_date: str) -> str:
        """
        指定された当番日（日付）の支出合計や、その日の予算残高をDuckDBから取得します。
        """
        url = f"http://receipt_fastapi_web:8000/v1/expenses/duty-day?date={duty_date}"
        try:
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                return (
                    f"DuckDBからの当番日集計結果:\n"
                    f"対象日（{data['date']}）の買い出し合計金額は {data['total_expense']}円 です。\n"
                    f"当日の目安予算は {data['budget']}円、残り枠は {data['balance']}円 です."
                )
            return f"（API未接続モック）当番日（{duty_date}）の現在の支出合計は2,450円、残り予算は2,550円です（API未接続モック）。"
        except Exception as e:
            logging.error(f"[RAG Tool] 検索中にエラーが発生しました: {e}")
            return f"（通信エラー時バックアップ）当番日（{duty_date}）の現在の支出合計は2,450円、残り予算は2,550円です（通信エラー時バックアップ）。"

    return calculate_duty_day_budget_db
 