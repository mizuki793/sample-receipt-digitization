import sys
from unittest.mock import MagicMock
dummy_module = MagicMock()
sys.modules['langchain_community.chat_models.vertexai'] = dummy_module
import os
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import Faithfulness, ContextPrecision
from ragas.llms import LangchainLLMWrapper
from langchain_google_genai import ChatGoogleGenerativeAI

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'search_rag_service'))

def main():
    print("=== Ragas 評価スクリプト（インポートバグ回避版） ===")

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("LANGCHAIN_MODEL_NAME", "gemini-2.5-flash")
    if not api_key:
        print("Error: GEMINI_API_KEY が必要です。")
        return

    # 1. 純粋な LangChain の Chat モデルを作る
    chat_model = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key
    )

    # 2. ここがポイント：Ragas専用のラッパーでカプセル化する
    # これにより、Ragas内部でのVertexAIなどの不要なコミュニティモジュールの誤インポートを防止します
    evaluator_llm = LangchainLLMWrapper(chat_model)

    # 卵と牛乳のテストデータセット (モック)
    mock_data = {
        "question": [
            "タマゴはどこが安い？",
            "Eggの最安値を教えて",
            "ミルクの過去の価格は？",
            "低脂肪の最安値店舗はどこ？"
        ],
        "contexts": [
            ["2026-05-20 Aスーパー: 卵 10個入 198円"],
            ["2026-05-22 Bストア: 特売卵 1パック 210円"],
            ["2026-05-18 Cマーケット: 成分無調整牛乳 1L 220円"],
            ["2026-05-25 Aスーパー: 低脂肪牛乳 1L 150円"]
        ],
        "answer": [
            "過去の最安値はAスーパーの198円です。",
            "検索した結果、最安値はBストアの210円になります。",
            "Cマーケットで220円で販売されていた記録があります。",
            "低脂肪牛乳の最安値はAスーパーの150円です。"
        ],
        "ground_truth": [
            "Aスーパーの198円",
            "Aスーパーの198円",
            "Cマーケットの220円",
            "Aスーパーの150円"
        ]
    }

    df = pd.DataFrame(mock_data)
    dataset = Dataset.from_pandas(df)

    print("Geminiによる品質評価を実行中...")
    
    # 3. 💡 明示的に llm= にラッパーされたオブジェクトを渡す
    result = evaluate(
        dataset=dataset,
        metrics=[
            Faithfulness(),
            ContextPrecision()
        ],
        llm=evaluator_llm
    )

    # ex:
    # 'faithfulness（忠実性）': 0.2500, 
    # 'context_precision（コンテキストの正確性）': 0.7500

    print("\n=== 評価結果 ===")
    print(result)

if __name__ == "__main__":
    main()