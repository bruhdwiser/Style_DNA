from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field


class TrackEventRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_type: str = Field(
        ...,
        alias="eventType",
        min_length=1,
        max_length=64,
        description="Type of analytics event, e.g. page_view, product_view, search",
    )
    event_data: Dict[str, Any] = Field(
        default_factory=dict,
        alias="eventData",
        description="Payload details (page URL, product ID, search query, etc.)",
    )
    session_id: str = Field(
        ...,
        alias="sessionId",
        min_length=1,
        max_length=128,
        description="Client session identifier",
    )


class TrackEventResponse(BaseModel):
    success: bool = True
    event_id: Optional[str] = None


class TopPage(BaseModel):
    page: str
    count: int


class TopProduct(BaseModel):
    product_id: str
    name: Optional[str] = None
    count: int


class EventTypeCount(BaseModel):
    event_type: str
    count: int


class RecentEvent(BaseModel):
    id: str
    event_type: str
    event_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    user_id: Optional[str] = None


class AnalyticsStatsResponse(BaseModel):
    total_events: int
    total_sessions: int
    total_page_views: int
    total_product_views: int
    total_searches: int
    top_pages: List[TopPage] = Field(default_factory=list)
    top_products: List[TopProduct] = Field(default_factory=list)
    recent_events: List[RecentEvent] = Field(default_factory=list)
    events_by_type: List[EventTypeCount] = Field(default_factory=list)

    # CamelCase computed fields for existing admin UI compatibility
    @computed_field
    @property
    def totalEvents(self) -> int:
        return self.total_events

    @computed_field
    @property
    def totalSessions(self) -> int:
        return self.total_sessions

    @computed_field
    @property
    def totalPageViews(self) -> int:
        return self.total_page_views

    @computed_field
    @property
    def totalProductViews(self) -> int:
        return self.total_product_views

    @computed_field
    @property
    def totalSearches(self) -> int:
        return self.total_searches

    @computed_field
    @property
    def topPages(self) -> List[TopPage]:
        return self.top_pages

    @computed_field
    @property
    def topProducts(self) -> List[TopProduct]:
        return self.top_products

    @computed_field
    @property
    def recentEvents(self) -> List[RecentEvent]:
        return self.recent_events

    @computed_field
    @property
    def eventsByType(self) -> List[EventTypeCount]:
        return self.events_by_type
