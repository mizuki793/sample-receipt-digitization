from langchain_core.tools import tool
import httpx

@tool
def search_past_prices_rag(query: str) -> str:
    """
    過去のレシート履歴（ChromaDB）から、商品の過去最安値や店舗ごとの価格情報を検索します。
    「卵はどこが一番安い？」「過去の牛乳の価格は？」といった、商品の価格調査に関する質問の時に必ず使用してください。
    """
    # 後のステップでChromaDBの検索ロジックと繋ぎ込みます
    return "ChromaDBの結果: 過去の最安値は〇〇スーパーの198円です。"

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
            return f"当番日（{duty_date}）の現在の支出合計は2,450円、残り予算は2,550円です（API未接続モック）。"
    except Exception as e:
        # 通信エラーの場合も、開発中は挙動が見えるようにモック出力を添えます
        return f"当番日（{duty_date}）の現在の支出合計は2,450円、残り予算は2,550円です（通信エラー時バックアップ）。"
 