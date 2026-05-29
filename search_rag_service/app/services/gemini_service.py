import os
from typing import AsyncGenerator
from google import genai

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        # クライアントの初期化をインスタンス生成時に一元管理します
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    async def generate_chat_stream(self, prompt: str) ->  AsyncGenerator[str, None]:
        """
        Geminiからテキストストリーミングを取得し、
        SSE（Server-Sent Events）プロトコルに適した形式に整形して yield するジェネレータ
        """
        if not self.client:
            yield "data: Error: GEMINI_API_KEY is not set in environment variables.\n\n"
            return

        try:
            model_name = os.getenv("LANGCHAIN_MODEL_NAME", "gemini-2.5-flash")

            # クライアントの .aio（AsyncIOの略）を経由して呼び出すことで、完全な非同期ストリームになる
            response_stream = await self.client.aio.models.generate_content_stream(
                model=model_name,
                contents=prompt
            )

            async for chunk in response_stream:
                if chunk.text:
                    # SSEフォーマットに整形してフロントエンドへ流します
                    yield f"data: {chunk.text}\n\n"

        except Exception as e:
            # 途中で通信が切断された場合なども、安全にエラーログを乗せてストリームを閉じます
            yield f"data: Error occurred during streaming: {str(e)}\n\n"
