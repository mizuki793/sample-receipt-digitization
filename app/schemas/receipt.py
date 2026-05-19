from datetime import datetime
from pydantic import BaseModel, Field
from typing import List

class ReceiptItem(BaseModel):
    item_name: str  = Field(description="購入商品名")
    unit_price: int = Field(description="購入商品の単価")
    quantity: int = Field(description="購入個数")

class ReceiptAnalysisResponse(BaseModel):
    transaction_date: datetime | None = Field(description="レシート発行日(YYYY-MM-DDTHH:MM:SS)")
    items: List[ReceiptItem] = Field(description="商品型のリスト")
    total_amount: int = Field(description="合計の価格")
    tax: int | None = Field(description="税(抽出できない場合はnull）")