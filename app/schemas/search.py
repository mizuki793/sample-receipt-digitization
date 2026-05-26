from pydantic import BaseModel, Field
from typing import List, Optional

class SearchRequest(BaseModel):
    #100文字制限、前後の空白自動削除、空文字禁止
    query: str = Field(
        ..., 
        max_length=100, 
        min_length=1, 
        strip_whitespace=True,
        description="検索する商品名（例：卵）"
    )

class StoreStat(BaseModel):
    store_name: str
    min_price: int
    avg_price: int
    total_count: int

class TimeZoneStat(BaseModel):
    time_zone: str  # 例: "00:00-06:00", "18:00-24:00" など
    count: int

class SearchStatsResponse(BaseModel):
    query: str
    store_stats: List[StoreStat]
    time_zone_stats: List[TimeZoneStat]
