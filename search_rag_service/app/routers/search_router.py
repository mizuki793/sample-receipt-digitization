from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from services.vector_store import BaseVectorStore
from services.agent_service import ShoppingAgent
from core.dependencies import get_agent, get_vector_store
from schemas.search import (
    BulkEmbedRequest,
    ChatStreamRequest,
    QueryResponse,
    SearchQueryRequest,
)

router = APIRouter(prefix="/v1", responses={404: {"description": "Not found"}})

@router.post("/embeddings", status_code=status.HTTP_201_CREATED)
async def create_embeddings_bulk(
    payload: BulkEmbedRequest,
    vector_store: BaseVectorStore = Depends(get_vector_store),
):
    try:
        items_dict_list = [item.model_dump() for item in payload.items]
        total_vectors = vector_store.store_bulk_items(
            job_id=payload.job_id,
            store_name=payload.store_name,
            items=items_dict_list,
        )
        return {
            "status": "success",
            "message": f"Successfully registered {total_vectors} vector variants for job_id '{payload.job_id}'.",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store bulk embeddings: {str(e)}",
        )


@router.post("/search", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def search_items(
    payload: SearchQueryRequest,
    vector_store: BaseVectorStore = Depends(get_vector_store),
):
    try:
        matches = vector_store.search_similar_items(payload.query, payload.n_results)
        return QueryResponse(query=payload.query, matches=matches)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(
    request: ChatStreamRequest,
    agent: ShoppingAgent = Depends(get_agent),
):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    return StreamingResponse(
        agent.stream_agent_response(request.message),
        media_type="text/event-stream",
    )
