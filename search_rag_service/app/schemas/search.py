from typing import List, Optional
from pydantic import BaseModel, Field

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
