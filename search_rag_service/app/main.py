from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.chromadb_service import ChromaDBService
from app.services.gemini_service import GeminiService

app = FastAPI(title="Search RAG Service", version="1.0.0")

# TODO:クラスのインスタンス化、可読性を高くしたい
chroma_service = ChromaDBService()
gemini_service = GeminiService()

# TODO:スキーマーに切り分けが必要　- このサービスは一旦動くことを優先させる
# --- リクエスト/レスポンススキーマ ---
class EmbedRequest(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=100)
    job_id: str

class SearchQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100)
    n_results: Optional[int] = 3

class MatchedItem(BaseModel):
    item_name: str
    distance: float

class QueryResponse(BaseModel):
    query: str
    matches: List[MatchedItem]

class ChatStreamRequest(BaseModel):
    message: str

# --- エンドポイント ---
# TODO:routerに切り分けるべき
@app.post("/v1/embeddings", status_code=status.HTTP_201_CREATED)
async def create_embedding(payload: EmbedRequest):
    """レシート解析完了時に呼ばれるバックヤード処理：商品名をベクトル化してVector DBへ保存"""
    try:
        chroma_service.store_item(payload.item_name, payload.job_id)
        return {"status": "success", "message": f"Item '{payload.item_name}' stored successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store embedding: {str(e)}")

@app.post("/v1/search", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def search_items(payload: SearchQueryRequest):
    """ユーザー検索時にメインアプリから呼ばれる内部API：表記揺れを吸収した類似商品を特定"""
    try:
        matches = chroma_service.search_similar_items(payload.query, payload.n_results)
        return QueryResponse(query=payload.query, matches=matches)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/v1/chat/stream")
async def chat_stream_endpoint(request: ChatStreamRequest):
    """
    ユーザーからのメッセージを受け取り、
    Geminiのテキスト応答をリアルタイムにストリーミング配信するエンドポイント
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # StreamingResponseにジェネレータを渡し、メディアタイプを text/event-stream に指定します
    return StreamingResponse(
        gemini_service.generate_chat_stream(request.message),
        media_type="text/event-stream"
    )
