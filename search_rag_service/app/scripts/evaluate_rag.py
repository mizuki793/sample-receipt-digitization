import os
import sys
from unittest.mock import MagicMock
dummy_module = MagicMock()
sys.modules['langchain_community.chat_models.vertexai'] = dummy_module
import asyncio
import logging
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import Faithfulness, ContextPrecision
from ragas.llms import LangchainLLMWrapper
from langchain_google_genai import ChatGoogleGenerativeAI

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

if backend_root not in sys.path:
    sys.path.append(backend_root)

# パスが通った後に、同じコンテナ内の本物のサービス群をインポートします
try:
    from app.services.chromadb_service import ChromaDBService
    from app.services.agent_service import ShoppingAgent
    agent = ShoppingAgent()
    chroma_service = ChromaDBService()
except ImportError as e:
    logging.error(f" インポートに失敗しました。現在の sys.path: {sys.path}")
    raise e


async def get_rag_response_and_contexts_async(question: str):
    """
    本物のLangGraphエージェントを実行し、AIの最終回答と
    ツール（ChromaDB）が走った際の生コンテキストを抽出して返す関数
    """
    if agent is None:
        return {"answer": "Agentが見つかりません", "contexts": []}
    full_answer = ""
    
    try:
        async for chunk in agent.stream_agent_response(question):
            if chunk is None:
                continue
            if isinstance(chunk, str):
                full_answer += chunk
            elif hasattr(chunk, "content"):
                full_answer += str(chunk.content)
            elif isinstance(chunk, dict):
                if "ops" in chunk: # astream_log 形式
                    for op in chunk["ops"]:
                        if "value" in op and isinstance(op["value"], dict) and "content" in op["value"]:
                            full_answer += str(op["value"]["content"])
                elif "content" in chunk:
                    full_answer += str(chunk["content"])
            else:
                full_answer += str(chunk)
    
    except Exception as e:
        logging.error(f" ┗ [Warning] ストリームパース中に例外を検知: {e}")
    final_answer = full_answer if full_answer.strip() else "有効な文字列ストリームを回収できませんでした。"

    extracted_contexts = []

    try:
        matches = chroma_service.search_similar_items(query_text=question, n_results=3)
        for m in matches:
            extracted_contexts.append(f"商品名: {m['item_name']} (距離: {m['distance']:.4f})")

    except Exception as e:
        logging.error(f" ┗ [Warning] ChromaDBからの直接コンテキスト回収に失敗: {e}")
    
    if not extracted_contexts:
        extracted_contexts = ["ChromaDBに該当する過去の価格履歴データが存在しません"]
    
    return {
        "answer": final_answer,
        "contexts": extracted_contexts
    }

def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("=== Ragas 評価スクリプト（インポートバグ回避版） ===")

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("LANGCHAIN_MODEL_NAME", "gemini-2.5-flash")
    if not api_key:
        logging.error("Error: GEMINI_API_KEY が必要です。")
        return

    # テスト用の表記揺れデータセット
    test_cases = [
        {"question": "タマゴはどこが安い？", "ground_truth": "Aスーパーの198円"},
        {"question": "Eggの最安値を教えて", "ground_truth": "Aスーパーの198円"},
        {"question": "ミルクの過去の価格は？", "ground_truth": "Cマーケットの220円"},
        {"question": "低脂肪の最安値店舗はどこ？", "ground_truth": "Aスーパーの150円"}
    ]
    questions = []
    contexts = []
    answers = []
    ground_truths = []
    
    logging.info("本物のLangGraphを駆動させて回答と検索文脈を収集中...")
    loop = asyncio.get_event_loop()

    for case in test_cases:
        q = case["question"] 
        gt = case["ground_truth"]
        logging.info(f"\n⚡ エージェント実行中: '{q}'")
        rag_res = loop.run_until_complete (get_rag_response_and_contexts_async(q))

        ai_reply = str(rag_res.get('answer', ''))
        print(f" ┗ AI回答: {rag_res['answer'][:30]}...")
        print(f" ┗ 取得文脈数: {len(rag_res['contexts'])}件")

        questions.append(q)
        ground_truths.append(gt)
        answers.append(rag_res["answer"])
        contexts.append(rag_res["contexts"])

    # Ragas用のDatasetにパッキング
    evaluation_data = {
        "question": questions,
        "contexts": contexts,
        "answer": answers,
        "ground_truth": ground_truths
    }
    df = pd.DataFrame(evaluation_data)
    dataset = Dataset.from_pandas(df)

    # 評価エンジン（Gemini）の初期化と実行
    chat_model = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key
    )
    evaluator_llm = LangchainLLMWrapper(chat_model)

    logging.info("Geminiによる定量評価（Ragas）を開始...")
    
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
    print("\n" + "="*40)
    print("RAGパイプラインの評価結果")
    print("="*40)
    print(result)

    result_df = result.to_pandas()
    print("\n=== クエリごとの詳細スコア ===")
    
    available_columns = result_df.columns.tolist()
    target_columns = ["user_input", "question", "response", "answer", "faithfulness", "context_precision"]
    display_columns = [col for col in target_columns if col in available_columns]
    
    print(result_df[display_columns])

if __name__ == "__main__":
    main()