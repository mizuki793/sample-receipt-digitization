from langchain_core.tools import tool
import httpx
import logging
from app.services.chromadb_service import ChromaDBService

chroma_service = ChromaDBService()

@tool
def search_past_prices_rag(query: str) -> str:
    """
    過去のレシート履歴（ChromaDB）から、商品の過去最安値や店舗ごとの価格情報を検索します。
    「卵はどこが一番安い？」「過去の牛乳の価格は？」といった、商品の価格調査に関する質問の時に必ず使用してください。
    """
    # 後のステップでChromaDBの検索ロジックと繋ぎ込みます
    logging.info(f"[RAG Tool] ChromaDBへクエリを送信中: '{query}'")
    
    try:
        results = chroma_service.search_similar_items(query_text=query, n_results=3)
        if not results:
            return f"「{query}」に関する過去のレシート履歴（商品名）は見つかりませんでした。"
        
        # 取得した類似アイテム（ドキュメント）と距離（類似度スコア）をテキストに整形
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
    
@tool
def calculate_duty_day_budget_db(duty_date: str) -> str:
    """
    指定された当番日（日付）の支出合計や、その日の予算残高をDuckDBから取得します。
    「今日の当番の予算は足りそう？」「〇月〇日の買い出しでいくら使った？」といった、当番日の金額や計算に関する質問の時に必ず使用してください。
    引数の duty_date は 'YYYY-MM-DD' 形式の文字列にしてください。
    """
    # コンテナ間通信でreceipt_serviceから特定の当番日の集計結果を取得する
    # ※API側のエンドポイントや挙動は後ほど実装を合わせます
    url = f"http://receipt_fastapi_web:8000/v1/expenses/duty-day?date={duty_date}"
    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            return (
                f"DuckDBからの当番日集計結果:\n"
                f"対象日（{data['date']}）の買い出し合計金額は {data['total_expense']}円 です。\n"
                f"当日の目安予算は {data['budget']}円、残り枠は {data['balance']}円 です。"
            )
        else:
            # まだAPIが未実装の期間は、挙動確認のために仮の成功文脈を返してグラフのテストを進められるようにします
            return f"（API未接続モック）当番日（{duty_date}）の現在の支出合計は2,450円、残り予算は2,550円です（API未接続モック）。"
    except Exception as e:
        logging.error(f"[RAG Tool] 検索中にエラーが発生しました: {e}")
        # 通信エラーの場合も、開発中は挙動が見えるようにモック出力を添えます
        return f"（通信エラー時バックアップ）当番日（{duty_date}）の現在の支出合計は2,450円、残り予算は2,550円です（通信エラー時バックアップ）。"
 