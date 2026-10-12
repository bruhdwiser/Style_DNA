from .common import ErrorDetail, ErrorResponse, HealthResponse
from .user import AuthenticatedUser, CurrentUserResponse
from .product import ProductBase, ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
from .cart import CartItemProduct, CartItemResponse, CartItemCreate, CartItemUpdate, CartResponse
from .ai import ChatRequest, ChatResponse, RecommendedProduct
from .analytics import (
    TrackEventRequest,
    TrackEventResponse,
    AnalyticsStatsResponse,
    TopPage,
    TopProduct,
    EventTypeCount,
    RecentEvent,
)
from .style_profile import (
    StyleProfileUpdate,
    StyleProfileResponse,
    ConsentGrant,
    ConsentResponse,
    ConsentListResponse,
)

from .wardrobe import (
    UploadUrlRequest,
    UploadUrlResponse,
    FinalizeUploadRequest,
    WardrobeItemUpdate,
    WardrobeItemResponse,
    WardrobeListResponse,
    WardrobeCoverageResponse,
    TagSuggestionResponse,
)

from .outfit import (
    GenerateOutfitsRequest,
    GenerateOutfitsResponse,
    OutfitResponse,
    OutfitSlotItem,
    SavedOutfitsListResponse,
)

from .style_dna import (
    RecordOutfitEventRequest,
    OutfitEventResponse,
    StyleDnaPreferenceItem,
    StyleDnaAffinities,
    StyleDnaResponse,
    ResetStyleDnaResponse,
)

from .gaps import (
    CatalogProductSuggestion,
    GapSuggestionItem,
    GapAnalysisResponse,
)

__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "AuthenticatedUser",
    "CurrentUserResponse",
    "ProductBase",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductListResponse",
    "CartItemProduct",
    "CartItemResponse",
    "CartItemCreate",
    "CartItemUpdate",
    "CartResponse",
    "ChatRequest",
    "ChatResponse",
    "RecommendedProduct",
    "TrackEventRequest",
    "TrackEventResponse",
    "AnalyticsStatsResponse",
    "TopPage",
    "TopProduct",
    "EventTypeCount",
    "RecentEvent",
    "StyleProfileUpdate",
    "StyleProfileResponse",
    "ConsentGrant",
    "ConsentResponse",
    "ConsentListResponse",
    "UploadUrlRequest",
    "UploadUrlResponse",
    "FinalizeUploadRequest",
    "WardrobeItemUpdate",
    "WardrobeItemResponse",
    "WardrobeListResponse",
    "WardrobeCoverageResponse",
    "GenerateOutfitsRequest",
    "GenerateOutfitsResponse",
    "OutfitResponse",
    "OutfitSlotItem",
    "SavedOutfitsListResponse",
    "RecordOutfitEventRequest",
    "OutfitEventResponse",
    "StyleDnaPreferenceItem",
    "StyleDnaAffinities",
    "StyleDnaResponse",
    "ResetStyleDnaResponse",
    "CatalogProductSuggestion",
    "GapSuggestionItem",
    "GapAnalysisResponse",
]
