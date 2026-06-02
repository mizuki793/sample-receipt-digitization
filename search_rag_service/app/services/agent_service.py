from typing import Dict, TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain.chat_models import init_chat_model
from datetime import datetime
import os

from tools.shopping_tools import (
    search_past_prices_rag,
    calculate_duty_day_budget_db
)

# 1. グラフ全体でメッセージ履歴を保持するための状態（State）定義
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]

class ShoppingAgent:
    def __init__(self):
        # ツール群の登録
        self.tools = [
            search_past_prices_rag, 
            calculate_duty_day_budget_db
        ]

        self.tool_node = ToolNode(self.tools)

        model_name = os.getenv("LANGCHAIN_MODEL_NAME", "gemini-2.5-flash")
        model_provider = os.getenv("LANGCHAIN_MODEL_PROVIDER", "google_genai")

        # Gemini 2.5 Flashの初期化とツールの紐付け
        self.model = init_chat_model(
            model=model_name,
            model_provider=model_provider,
            max_retries=3
        ).bind_tools(self.tools)
        
        # ワークフローグラフの構築
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile()

    def _call_model(self, state: AgentState) -> Dict:
        """ユーザーの入力やツールの結果を見て、次に行うべき行動をLLMに判断させるノード"""
        messages = state["messages"]
        
        # LLMが日付の文脈を理解しやすいように、システムメッセージで現在日時を補正
        current_date_str = datetime.now().strftime("%Y-%m-%d")
        system_prompt = f"現在の注文当日の日付は {current_date_str} です。ユーザーが『今日』と言った場合はこの日付を基準にしてください。"
        
        # 簡易的にメッセージの先頭にシステムプロンプトのコンテキストを付与
        full_messages = [HumanMessage(content=system_prompt)] + list(messages)
        response = self.model.invoke(full_messages)
        return {"messages": [response]}

    def _should_continue(self, state: AgentState) -> str:
        """次にツールを実行すべきか、ユーザーへの最終回答に進むべきかを判定するエッジ"""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        return "end"

    def _create_workflow(self) -> StateGraph:
        graph = StateGraph(AgentState)
        
        # 各ノードの登録
        graph.add_node("agent", self._call_model)
        graph.add_node("tools", self.tool_node)
        
        # 開始地点の設定
        graph.set_entry_point("agent")
        
        # 条件付き分岐（エッジ）の登録
        graph.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )
        # ツール実行後は、再度エージェント（LLM）に戻って結果を確認させる
        graph.add_edge("tools", "agent")
        
        return graph

    async def stream_agent_response(self, user_query: str):
        """FastAPIのStreamingResponseへ流すための非同期ジェネレータ"""
        inputs = {"messages": [HumanMessage(content=user_query)]}
        
        # グラフを実行し、ステップごとの更新イベントをストリーム検知
        async for chunk, metadata in self.app.astream(inputs, stream_mode="messages"):
            if metadata.get("langgraph_node") == "agent" and chunk.content:
                token = chunk.content
                yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"
