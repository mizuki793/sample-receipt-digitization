from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from services.chromadb_service import ChromaDBService
from services.agent_service import ShoppingAgent

app = FastAPI(title="Search RAG Service", version="1.0.0")
agent = ShoppingAgent()

chroma_service = ChromaDBService()

# TODO:スキーマーに切り分けが必要　- このサービスは一旦動くことを優先させる
# --- リクエスト/レスポンススキーマ ---
class DiscoveredItem(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=100)
    unit_price: int = Field(..., ge=0)
    category: Optional[str] = None
    tags: Optional[List[str]] = None

class BulkEmbedRequest(BaseModel):
    job_id: str
    store_name: str
    items: List[DiscoveredItem] = Field(..., min_items=1)

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
async def create_embeddings_bulk(payload: BulkEmbedRequest):
    """
    手動修正の確定時に呼ばれるバックヤード処理：
    1つのjob_idに紐づく複数の商品を、多角化したベクトルデータとして一括保存
    """
    try:
        items_dict_list = [item.model_dump() for item in payload.items]
        
        total_vectors = chroma_service.store_bulk_items(
            job_id=payload.job_id,
            store_name=payload.store_name,
            items=items_dict_list
        )
        return {
            "status": "success",
            "message": f"Successfully registered {total_vectors} vector variants for job_id '{payload.job_id}'."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to store bulk embeddings: {str(e)}"
        )

@app.post("/v1/search", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def search_items(payload: SearchQueryRequest):
    """ユーザー検索時にメインアプリから呼ばれる内部API：表記揺れを吸収した類似商品を特定"""
    try:
        matches = chroma_service.search_similar_items(payload.query, payload.n_results)
        return QueryResponse(query=payload.query, matches=matches)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/v1/chat/stream")
async def chat_stream(request: ChatStreamRequest):
    """
    ユーザーからのメッセージを受け取り、
    Geminiのテキスト応答をリアルタイムにストリーミング配信するエンドポイント
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # StreamingResponseにジェネレータを渡し、メディアタイプを text/event-stream に指定します
    return StreamingResponse(
        agent.stream_agent_response(request.message),
        media_type="text/event-stream"
    )
