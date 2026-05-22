from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from typing import List, Literal

SupermarketCategory = Literal[
    "生鮮（肉）",
    "生鮮（魚）",
    "生鮮（野菜・果物）",
    "惣菜・お弁当",
    "日配品（乳製品・豆腐・卵・パンなど）",
    "加工食品（調味料・レトルト・缶詰など）",
    "お菓子",
    "飲料・お酒",
    "日用品・雑貨",
    "その他"
]

class ReceiptItem(BaseModel):
    item_name: str  = Field(description="購入商品名")
    unit_price: int = Field(description="購入商品の単価")
    quantity: int = Field(default=1, description="購入個数(抽出できない場合はnull)")
    category: SupermarketCategory | None = Field(
        description="売場部門における日本の一般的なスーパーにおける商品分類(抽出できない場合はnull)"
    )

class ReceiptAnalysisResponse(BaseModel):
    store_name: str | None = Field(default=None, description="店舗名(抽出できない場合はnull)")
    store_address: str | None = Field(default=None, description="店舗住所(抽出できない場合はnull)")
    transaction_date: datetime | None = Field(default=None, description="レシート発行日(YYYY-MM-DDTHH:MM:SS)")
    items: List[ReceiptItem] = Field(description="商品型のリスト")
    total_amount: int = Field(description="合計の価格")
    tax: int | None = Field(description="税(抽出できない場合はnull）")
    needs_correction: bool = Field(default=False, description="修正フラグ")

    @model_validator(mode="after")
    def validate_amounts(self):
        calculated_total = sum(item.unit_price * item.quantity for item in self.items)
        if calculated_total + (self.tax or 0) != self.total_amount:
            self.needs_correction = True
        return self
