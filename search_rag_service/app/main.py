from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.chromadb_service import ChromaDBService

app = FastAPI(title="Search RAG Service", version="1.0.0")
chroma_service = ChromaDBService()

# TODO:スキーマーに切り分けが必要
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
