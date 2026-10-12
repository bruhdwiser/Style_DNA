from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field


class CartItemProduct(BaseModel):
    id: str = Field(..., description="Consistent product UUID")
    name: str = Field(...)
    price_cents: int = Field(..., ge=0)
    original_price_cents: Optional[int] = None
    image_url: Optional[str] = None
    category: Optional[str] = "General"

    @computed_field
    @property
    def price(self) -> float:
        return round(self.price_cents / 100, 2)

    @computed_field
    @property
    def image(self) -> str:
        return self.image_url or "/placeholder.svg"


class CartItemResponse(BaseModel):
    id: str = Field(..., description="Cart item UUID")
    product_id: str = Field(..., description="Product UUID")
    quantity: int = Field(..., ge=1)
    selected_color: Optional[str] = None
    selected_size: Optional[str] = None
    product: Optional[CartItemProduct] = None
    created_at: Optional[datetime] = None


class CartItemCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: str = Field(
        ...,
        validation_alias=Field.validation_alias if hasattr(Field, "validation_alias") else "productId",
        description="UUID of the authentic catalog product to add",
    )
    quantity: int = Field(1, ge=1, le=99, description="Quantity to add (1-99)")
    selected_color: Optional[str] = Field(None, alias="selectedColor")
    selected_size: Optional[str] = Field(None, alias="selectedSize")


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1, le=99, description="New quantity for this item")


class CartResponse(BaseModel):
    items: List[CartItemResponse]
    total_cents: int = Field(..., ge=0)
    total: float = Field(..., ge=0)
    item_count: int = Field(..., ge=0)
