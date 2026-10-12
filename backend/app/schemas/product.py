from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, computed_field


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Product display name")
    description: Optional[str] = Field(None, description="Detailed product description")
    price_cents: int = Field(..., ge=0, description="Price in integer cents/paise")
    original_price_cents: Optional[int] = Field(None, ge=0, description="Original price before discount")
    category: str = Field("General", description="Product category")
    image_url: Optional[str] = Field(None, description="Primary product image URL")
    colors: List[str] = Field(default_factory=list, description="Available color variants")
    sizes: List[str] = Field(default_factory=list, description="Available size options")
    is_new: bool = Field(False, description="Whether product is marked as new arrival")
    is_sale: bool = Field(False, description="Whether product is marked on sale")

    # Additive styling attributes for styling engine and recommendations
    audience: Optional[str] = Field("all", description="Target audience: women, men, unisex, all")
    slot: Optional[str] = Field(None, description="Outfit slot: top, bottom, dress, saree, ethnic_set, shoes, bag, outer, jewelry, dupatta")
    subtype: Optional[str] = Field(None, description="Garment or accessory subtype (e.g. kurta, blazer, sneakers)")
    color_tags: List[str] = Field(default_factory=list, description="Normalized hex or color name tags")
    formality: Optional[int] = Field(None, ge=0, le=3, description="Formality level: 0=casual, 1=smart casual, 2=formal, 3=festive/wedding")
    style_tags: List[str] = Field(default_factory=list, description="Style archetype tags (minimal, classic, etc.)")
    occasions: List[str] = Field(default_factory=list, description="Suitable occasions")
    seasons: List[str] = Field(default_factory=list, description="Suitable seasons")
    fit: Optional[str] = Field(None, description="Garment silhouette fit")
    pattern: Optional[str] = Field(None, description="Fabric pattern")
    seed_key: Optional[str] = Field(None, description="Deterministic seed identifier")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price_cents: Optional[int] = Field(None, ge=0)
    original_price_cents: Optional[int] = Field(None, ge=0)
    category: Optional[str] = None
    image_url: Optional[str] = None
    colors: Optional[List[str]] = None
    sizes: Optional[List[str]] = None
    is_new: Optional[bool] = None
    is_sale: Optional[bool] = None
    audience: Optional[str] = None
    slot: Optional[str] = None
    subtype: Optional[str] = None
    color_tags: Optional[List[str]] = None
    formality: Optional[int] = Field(None, ge=0, le=3)
    style_tags: Optional[List[str]] = None
    occasions: Optional[List[str]] = None
    seasons: Optional[List[str]] = None
    fit: Optional[str] = None
    pattern: Optional[str] = None
    seed_key: Optional[str] = None


class ProductResponse(ProductBase):
    id: str = Field(..., description="Consistent Supabase UUID string")
    created_at: Optional[datetime] = None

    # Preserved convenience fields matching existing frontend expectations
    @computed_field
    @property
    def price(self) -> float:
        """Computed price in main currency units (INR)."""
        return round(self.price_cents / 100, 2)

    @computed_field
    @property
    def original_price(self) -> Optional[float]:
        """Computed original price in main currency units (INR)."""
        if self.original_price_cents is not None:
            return round(self.original_price_cents / 100, 2)
        return None

    @computed_field
    @property
    def image(self) -> str:
        """Alias for image_url for UI component compatibility."""
        return self.image_url or "/placeholder.svg"

    @computed_field
    @property
    def dbId(self) -> str:
        """Alias for id ensuring backwards compatibility with any remaining dbId references."""
        return self.id


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    next_offset: int
    has_more: bool

    # Backwards-compatible camelCase aliases for smooth frontend migration
    @computed_field
    @property
    def nextOffset(self) -> int:
        return self.next_offset

    @computed_field
    @property
    def hasMore(self) -> bool:
        return self.has_more
