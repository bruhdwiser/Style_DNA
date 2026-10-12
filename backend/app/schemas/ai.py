from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User question or styling request",
    )
    conversation_history: Optional[str] = Field(
        None,
        max_length=4000,
        alias="conversationHistory",
        description="Optional formatted conversation history (capped to 4000 characters)",
    )


class RecommendedProduct(BaseModel):
    id: str = Field(..., description="Verified Supabase catalog UUID")
    name: str = Field(..., description="Product name")
    price: float = Field(..., ge=0, description="Price in INR")
    image_url: Optional[str] = None
    category: Optional[str] = None


class ChatResponse(BaseModel):
    message: str = Field(..., description="Sanitized styling advice with verified product links")
    recommended_products: List[RecommendedProduct] = Field(
        default_factory=list,
        description="Catalog products validated against Supabase database",
    )
    model_used: Optional[str] = Field(
        None,
        description="The AI model that generated the response, or 'deterministic-fallback'",
    )
