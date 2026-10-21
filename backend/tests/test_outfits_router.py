"""Unit and integration tests for outfit generation router, catalog completion, and persistence."""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import pytest

from app.core.exceptions import AppException
from app.schemas.outfit import (
    GenerateOutfitsRequest,
    GenerateOutfitsResponse,
    SaveOutfitRequest,
    UpdateOutfitTagsRequest,
    APPROVED_OUTFIT_TAGS,
    validate_and_normalize_tags,
)
from app.schemas.style_dna import RecordOutfitEventRequest
from app.schemas.user import AuthenticatedUser
from app.routers.outfits import (
    generate_outfit_recommendations,
    list_saved_outfits,
    save_outfit,
    update_outfit_tags,
    unsave_outfit,
    record_outfit_event,
    _persist_outfit_and_items,
)


class MockQuery:
    def __init__(self, data=None, fail_insert=False, fail_update=False):
        self._data = [dict(d) for d in data] if data is not None else []
        self.fail_insert = fail_insert
        self.fail_update = fail_update
        self.inserted: list[dict] = []
        self.deleted_ids: list[str] = []
        self._filter_eq: dict = {}
        self._contains_filters: dict = {}
        self._delete_mode = False
        self._update_data = None

    def select(self, *args, **kwargs):
        return self

    def order(self, field, desc=False):
        return self

    def eq(self, field, value):
        self._filter_eq[field] = value
        if field == "id" and self._delete_mode:
            self.deleted_ids.append(value)
        return self

    def in_(self, field, values):
        if field == "audience" and self._data:
            self._data = [d for d in self._data if d.get("audience") in values]
        elif self._data:
            self._data = [d for d in self._data if d.get(field) in values]
        return self

    def contains(self, field, values):
        self._contains_filters[field] = values
        return self

    def limit(self, *args, **kwargs):
        return self

    def update(self, fields: dict):
        self._update_data = fields
        return self

    def execute(self):
        if self._delete_mode:
            remaining = []
            deleted = []
            for row in self._data:
                match = all(row.get(k) == v for k, v in self._filter_eq.items())
                if match:
                    deleted.append(dict(row))
                else:
                    remaining.append(row)
            self._data = remaining
            self.inserted = [
                r for r in self.inserted
                if not all(r.get(k) == v for k, v in self._filter_eq.items())
            ]
            self._delete_mode = False
            return SimpleNamespace(data=deleted)

        if self._update_data is not None:
            if self.fail_update:
                raise RuntimeError("Simulated database update failure")
            updated_rows = []
            for row in self._data:
                match = all(row.get(k) == v for k, v in self._filter_eq.items())
                if match:
                    row.update(self._update_data)
                    updated_rows.append(dict(row))
            if not updated_rows and not self._filter_eq:
                updated_rows = [dict(self._update_data)]
            self._update_data = None
            return SimpleNamespace(data=updated_rows)

        filtered = self._data
        if self._filter_eq:
            filtered = [
                row for row in filtered
                if all(row.get(k) == v for k, v in self._filter_eq.items())
            ]
        if self._contains_filters:
            for field, vals in self._contains_filters.items():
                filtered = [
                    row for row in filtered
                    if all(v in row.get(field, []) for v in vals)
                ]
        return SimpleNamespace(data=[dict(r) for r in filtered])

    def insert(self, rows):
        if self.fail_insert:
            raise RuntimeError("Simulated database insert failure")
        row_list = rows if isinstance(rows, list) else [rows]
        self.inserted.extend(row_list)
        for r in row_list:
            self._data.append(dict(r))
        return self

    def delete(self):
        self._delete_mode = True
        return self


class MockRpcQuery:
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error

    def execute(self):
        if self.error:
            raise self.error
        return SimpleNamespace(data=self.data)


class MockSupabaseClient:
    def __init__(
        self,
        wardrobe_items=None,
        products=None,
        style_profiles=None,
        outfit_events=None,
        outfits=None,
        outfit_items=None,
        fail_items_insert=False,
        fail_events_insert=False,
        fail_outfits_update=False,
        fail_rpc=False,
        enable_save_rpc=True,
    ):
        self.fail_rpc = fail_rpc
        self.enable_save_rpc = enable_save_rpc
        self.tables = {
            "wardrobe_items": MockQuery(wardrobe_items or []),
            "products": MockQuery(products or []),
            "style_profiles": MockQuery(style_profiles or []),
            "outfit_events": MockQuery(outfit_events or [], fail_insert=fail_events_insert),
            "outfits": MockQuery(outfits or [], fail_update=fail_outfits_update),
            "outfit_items": MockQuery(outfit_items or [], fail_insert=fail_items_insert),
        }

    def from_(self, table_name: str):
        return self.tables.get(table_name, MockQuery([]))

    def rpc(self, func_name: str, params: dict):
        if self.fail_rpc:
            return MockRpcQuery(error=RuntimeError("Simulated RPC function failure"))

        if func_name == "save_outfit_with_items":
            p_outfit = params.get("p_outfit") or {}
            p_items = params.get("p_items") or []

            # Simulate PostgreSQL transactional behavior:
            # If outfit_items insertion fails, the entire transaction aborts.
            # Neither the outfit row nor any item rows are committed.
            if self.tables["outfit_items"].fail_insert:
                return MockRpcQuery(error=RuntimeError("Simulated item insert failure in transaction"))

            # Atomically persist both
            self.tables["outfits"]._data.append(dict(p_outfit))
            if p_items:
                self.tables["outfit_items"]._data.extend([dict(it) for it in p_items])

            return MockRpcQuery(data=p_outfit.get("id"))

        if func_name == "save_outfit_with_event":
            if not self.enable_save_rpc:
                raise RuntimeError("Could not find the function public.save_outfit_with_event")

            p_outfit_id = str(params.get("p_outfit_id"))
            p_tags = params.get("p_tags") or []
            p_event_metadata = params.get("p_event_metadata") or {}

            # Outfit must exist
            outfit = next((o for o in self.tables["outfits"]._data if str(o.get("id")) == p_outfit_id), None)
            if not outfit:
                return MockRpcQuery(error=RuntimeError("OUTFIT_NOT_FOUND"))

            # If event insert fails inside transaction, both abort
            if self.tables["outfit_events"].fail_insert:
                return MockRpcQuery(error=RuntimeError("Simulated event insert failure in transaction"))

            # If outfit update fails inside transaction, both abort
            if self.tables["outfits"].fail_update:
                return MockRpcQuery(error=RuntimeError("Simulated outfit update failure in transaction"))

            outfit["is_saved"] = True
            outfit["tags"] = p_tags

            existing = any(
                str(e.get("outfit_id")) == p_outfit_id and e.get("event_type") == "save"
                for e in self.tables["outfit_events"]._data
            )
            created_event = False
            if not existing:
                ev_row = {
                    "id": str(uuid4()),
                    "outfit_id": p_outfit_id,
                    "event_type": "save",
                    "metadata": p_event_metadata,
                }
                self.tables["outfit_events"].inserted.append(ev_row)
                self.tables["outfit_events"]._data.append(ev_row)
                created_event = True

            return MockRpcQuery(data={"success": True, "outfit_id": p_outfit_id, "is_saved": True, "tags": p_tags, "event_created": created_event})

        raise RuntimeError(f"Unknown RPC function in mock: {func_name}")


@pytest.fixture
def test_user():
    return AuthenticatedUser(
        id="00000000-0000-0000-0000-000000000001",
        email="user@example.com",
        role="authenticated",
    )


def test_generate_request_schema_defaults():
    """Verify Phase 2 defaults: catalog completion allowed by default; shuffle defaults to False."""
    req = GenerateOutfitsRequest()
    assert req.wardrobe_only is False, "Catalog completion must be enabled by default"
    assert req.allow_one_new_item is None, "Legacy parameter must be None by default"
    assert req.is_shuffle is False, "Shuffle must default to False"


@pytest.mark.anyio
async def test_wardrobe_only_opt_out_strictly_dominates(test_user):
    """Verify that wardrobe_only=True is a strict opt-out and prevents catalog completion."""
    # Wardrobe with tops and bottoms, but missing shoes
    wardrobe = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "sub_category": "t-shirt",
            "primary_color": "#000000",
            "color_tags": ["#000000"],
            "fit": "regular",
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "user_id": test_user.id,
            "category": "bottom",
            "slot": "bottom",
            "sub_category": "jeans",
            "primary_color": "#1E3A8A",
            "color_tags": ["#1E3A8A"],
            "fit": "straight",
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
            "is_available": True,
        },
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        # User explicitly chooses "Use only my rack" (wardrobe_only=True)
        req = GenerateOutfitsRequest(
            wardrobe_only=True,
            allow_one_new_item=True,  # Even if legacy True was passed, wardrobe_only dominates
            occasion="casual",
            season="all_season",
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert res.status == "missing_required_slots"
        assert "shoes" in res.missing_slots
        assert len(res.outfits) == 0


@pytest.mark.anyio
async def test_audience_filter_strictly_unisex_or_all(test_user):
    """Verify that catalog queries strictly enforce audience in ('unisex', 'all') without inferring audience."""
    # Wardrobe missing shoes
    wardrobe = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "primary_color": "#000000",
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "user_id": test_user.id,
            "category": "bottom",
            "slot": "bottom",
            "primary_color": "#1E3A8A",
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
            "is_available": True,
        },
    ]

    # Catalog contains women-only, men-only, and unisex shoes
    catalog = [
        {
            "id": "aaaaaaa1-0000-0000-0000-000000000000",
            "name": "Women Stiletto",
            "category": "shoes",
            "slot": "shoes",
            "audience": "women",
            "price_cents": 299900,
            "color_tags": ["#000000"],
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
        },
        {
            "id": "aaaaaaa2-0000-0000-0000-000000000000",
            "name": "Men Oxford",
            "category": "shoes",
            "slot": "shoes",
            "audience": "men",
            "price_cents": 299900,
            "color_tags": ["#000000"],
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
        },
        {
            "id": "aaaaaaa3-0000-0000-0000-000000000000",
            "name": "Unisex Classic Sneaker",
            "category": "shoes",
            "slot": "shoes",
            "audience": "unisex",
            "price_cents": 199900,
            "color_tags": ["#000000"],
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
        },
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        # Default request (wardrobe_only=False) allows catalog completion
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            occasion="casual",
            season="all_season",
            limit=2,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) > 0
        for outfit in res.outfits:
            assert not outfit.wardrobe_only
            # Assert only the unisex sneaker was used
            assert outfit.unlocked_by_product_id == "aaaaaaa3-0000-0000-0000-000000000000"
            for it in outfit.items:
                if it.source_type == "catalog":
                    assert it.product_id == "aaaaaaa3-0000-0000-0000-000000000000"
                    assert it.name == "Unisex Classic Sneaker"


@pytest.mark.anyio
async def test_mixed_look_contains_at_least_one_wardrobe_and_exactly_one_catalog_item(test_user):
    """Verify that each mixed look strictly adheres to: >= 1 wardrobe item, == 1 catalog item."""
    wardrobe = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "primary_color": "#000000",
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "user_id": test_user.id,
            "category": "bottom",
            "slot": "bottom",
            "primary_color": "#1E3A8A",
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
            "is_available": True,
        },
    ]

    catalog = [
        {
            "id": "bbbbbbb1-0000-0000-0000-000000000000",
            "name": "Everyday Sneaker",
            "category": "shoes",
            "slot": "shoes",
            "audience": "all",
            "price_cents": 199900,
            "color_tags": ["#000000"],
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
        }
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(wardrobe_only=False, occasion="casual", limit=1)
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 1
        mixed_outfit = res.outfits[0]
        assert mixed_outfit.wardrobe_only is False

        wardrobe_items_in_look = [it for it in mixed_outfit.items if it.source_type == "wardrobe"]
        catalog_items_in_look = [it for it in mixed_outfit.items if it.source_type == "catalog"]

        assert len(wardrobe_items_in_look) >= 1, "Must contain at least 1 wardrobe item"
        assert len(catalog_items_in_look) == 1, "Must contain exactly 1 catalog item"


@pytest.mark.anyio
async def test_shortfall_pipeline_and_below_threshold_quality_warning(test_user):
    """Verify that shortfall is filled first with catalog, and remaining with below-threshold looks with warning."""
    # Complete wardrobe: 1 high-compatibility combination and 1 clashing/low-compatibility combination
    wardrobe = [
        # Top 1: black classic (matches bottom 1)
        {
            "id": "top-high-1",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "primary_color": "#000000",
            "style_tags": ["classic"],
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        # Bottom 1: navy classic
        {
            "id": "bottom-1",
            "user_id": test_user.id,
            "category": "bottom",
            "slot": "bottom",
            "primary_color": "#1E3A8A",
            "style_tags": ["classic"],
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        # Shoes 1: white classic
        {
            "id": "shoes-1",
            "user_id": test_user.id,
            "category": "shoes",
            "slot": "shoes",
            "primary_color": "#FFFFFF",
            "style_tags": ["classic"],
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
            "is_available": True,
        },
    ]

    # No catalog items
    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=[])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        # Set high min_quality_threshold (e.g. 0.95) so the outfit is classified below-threshold
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            min_quality_threshold=0.95,
            occasion="casual",
            limit=2,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 1
        look = res.outfits[0]
        # Must be flagged as below threshold
        assert look.is_below_threshold is True
        assert look.quality_warning is not None
        assert "below your preferred quality threshold" in look.quality_warning
        # Response level quality warning
        assert res.quality_warning is not None
        assert res.status == "partial_results"


@pytest.mark.anyio
async def test_persistence_item_insert_failure_rolls_back_outfit_row(test_user):
    """Verify that if item insertion fails inside the transactional RPC, zero rows remain in outfits."""
    wardrobe = [
        {
            "id": "top-1",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "primary_color": "#000000",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "bottom-1",
            "user_id": test_user.id,
            "category": "bottom",
            "slot": "bottom",
            "primary_color": "#1E3A8A",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "shoes-1",
            "user_id": test_user.id,
            "category": "shoes",
            "slot": "shoes",
            "primary_color": "#FFFFFF",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
    ]

    # Configure mock client to fail on outfit_items insert
    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, fail_items_insert=True)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(wardrobe_only=True, occasion="casual", limit=1)

        # Persistence failure should raise AppException rather than returning broken outfit IDs
        from app.core.exceptions import AppException
        with pytest.raises(AppException) as exc_info:
            _ = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert exc_info.value.code == "OUTFIT_PERSISTENCE_ERROR"
        # Under atomic RPC, failure inside the transaction rolls back both tables; zero orphan outfits remain
        assert len(mock_client.tables["outfits"]._data) == 0
        assert len(mock_client.tables["outfit_items"]._data) == 0


@pytest.mark.anyio
async def test_persistence_rpc_success(test_user):
    """Verify that save_outfit_with_items atomically persists both outfit and outfit_items rows."""
    wardrobe = [
        {"id": "top-1", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#000000", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "bottom-1", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#1E3A8A", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "shoes-1", "user_id": test_user.id, "category": "shoes", "slot": "shoes", "primary_color": "#FFFFFF", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
    ]
    mock_client = MockSupabaseClient(wardrobe_items=wardrobe)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(wardrobe_only=True, occasion="casual", limit=1)
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 1
        # Check both tables received rows atomically
        assert len(mock_client.tables["outfits"]._data) == 1
        assert len(mock_client.tables["outfit_items"]._data) >= 2


@pytest.mark.anyio
async def test_persistence_rpc_failure_refuses_non_atomic_fallback_and_leaves_no_orphans(test_user):
    """Verify that when the RPC is unavailable or fails, non-atomic fallback is refused and zero rows are left behind."""
    wardrobe = [
        {"id": "top-1", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#000000", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "bottom-1", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#1E3A8A", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "shoes-1", "user_id": test_user.id, "category": "shoes", "slot": "shoes", "primary_color": "#FFFFFF", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
    ]
    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, fail_rpc=True)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(wardrobe_only=True, occasion="casual", limit=1)
        with pytest.raises(AppException) as exc_info:
            await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert exc_info.value.code == "OUTFIT_PERSISTENCE_ERROR"
        # Refusal of non-atomic fallback guarantees zero orphaned outfit rows
        assert len(mock_client.tables["outfits"]._data) == 0
        assert len(mock_client.tables["outfit_items"]._data) == 0


def test_failed_persistence_is_not_returned_as_valid_outfit():
    """Verify _persist_outfit_and_items returns False on RPC failure and does not return broken IDs."""
    client_failing = MockSupabaseClient(fail_rpc=True)
    outfit_row = {"id": "test-outfit-id", "user_id": "test-user-id"}
    item_rows = [{"outfit_id": "test-outfit-id", "slot": "top"}]

    persisted = _persist_outfit_and_items(client_failing, outfit_row, item_rows)
    assert persisted is False
    assert len(client_failing.tables["outfits"]._data) == 0

    client_ok = MockSupabaseClient()
    persisted_ok = _persist_outfit_and_items(client_ok, outfit_row, item_rows)
    assert persisted_ok is True
    assert len(client_ok.tables["outfits"]._data) == 1
    assert len(client_ok.tables["outfit_items"]._data) == 1


@pytest.mark.anyio
async def test_save_outfit_defaults_to_try_later(test_user):
    """Verify that saving an outfit without tags defaults to ['Try Later'] and logs a Style DNA event."""
    outfit_row = {
        "id": "outfit-101",
        "user_id": test_user.id,
        "occasion": "casual",
        "vibe": "classic",
        "skeleton": "top_bottom",
        "is_saved": False,
        "tags": [],
    }
    mock_client = MockSupabaseClient(outfits=[outfit_row], outfit_events=[])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        res = await save_outfit("outfit-101", body=None, token="dummy-token", user=test_user)

        assert res.success is True
        assert res.is_saved is True
        assert res.tags == ["Try Later"]

        # Check outfit row was updated
        updated_outfit = mock_client.tables["outfits"]._data[0]
        assert updated_outfit["is_saved"] is True
        assert updated_outfit["tags"] == ["Try Later"]

        # Check Style DNA outfit_events row was recorded
        events = mock_client.tables["outfit_events"].inserted
        assert len(events) == 1
        assert events[0]["event_type"] == "save"
        assert events[0]["outfit_id"] == "outfit-101"
        assert events[0]["metadata"]["tags"] == ["Try Later"]


@pytest.mark.anyio
async def test_save_outfit_normalizes_approved_tags(test_user):
    """Verify that custom tags are normalized to canonical title-case approved tags."""
    outfit_row = {
        "id": "outfit-102",
        "user_id": test_user.id,
        "occasion": "work",
        "vibe": "minimal",
        "skeleton": "top_bottom",
        "is_saved": False,
        "tags": [],
    }
    mock_client = MockSupabaseClient(outfits=[outfit_row], outfit_events=[])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = SaveOutfitRequest(tags=["work", "DATE NIGHT"])
        res = await save_outfit("outfit-102", body=req, token="dummy-token", user=test_user)

        assert res.success is True
        assert res.tags == ["Work", "Date Night"]

        updated_outfit = mock_client.tables["outfits"]._data[0]
        assert updated_outfit["tags"] == ["Work", "Date Night"]


@pytest.mark.anyio
async def test_save_outfit_idempotent_no_duplicate_style_dna(test_user):
    """Verify that repeated save calls or tag adjustments on already-saved looks do not inflate Style DNA."""
    outfit_row = {
        "id": "outfit-103",
        "user_id": test_user.id,
        "occasion": "casual",
        "skeleton": "top_bottom",
        "is_saved": True,  # Already saved
        "tags": ["Work"],
    }
    existing_event = {
        "id": "event-prev-1",
        "user_id": test_user.id,
        "outfit_id": "outfit-103",
        "event_type": "save",
    }
    mock_client = MockSupabaseClient(outfits=[outfit_row], outfit_events=[existing_event])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        # Save again with additional tag
        req = SaveOutfitRequest(tags=["Work", "Vacation"])
        res = await save_outfit("outfit-103", body=req, token="dummy-token", user=test_user)

        assert res.success is True
        assert res.tags == ["Work", "Vacation"]

        # No new event should be inserted into outfit_events
        new_events = mock_client.tables["outfit_events"].inserted
        assert len(new_events) == 0, "No duplicate Style DNA events should be inserted on re-save"


@pytest.mark.anyio
async def test_update_outfit_tags_on_saved_look(test_user):
    """Verify PUT /{outfit_id}/tags updates tags on an already-saved look."""
    outfit_row = {
        "id": "outfit-104",
        "user_id": test_user.id,
        "occasion": "party",
        "skeleton": "top_bottom",
        "is_saved": True,
        "tags": ["Try Later"],
    }
    mock_client = MockSupabaseClient(outfits=[outfit_row])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = UpdateOutfitTagsRequest(tags=["Wedding"])
        res = await update_outfit_tags("outfit-104", body=req, token="dummy-token", user=test_user)

        assert res["success"] is True
        assert res["tags"] == ["Wedding"]

        updated_outfit = mock_client.tables["outfits"]._data[0]
        assert updated_outfit["tags"] == ["Wedding"]


@pytest.mark.anyio
async def test_list_saved_outfits_tag_filtering(test_user):
    """Verify list_saved_outfits filters by tag and computes available_tags."""
    outfits = [
        {
            "id": "outfit-work-1",
            "user_id": test_user.id,
            "occasion": "work",
            "is_saved": True,
            "tags": ["Work"],
            "score": 0.85,
        },
        {
            "id": "outfit-vacation-1",
            "user_id": test_user.id,
            "occasion": "casual",
            "is_saved": True,
            "tags": ["Vacation", "Date Night"],
            "score": 0.90,
        },
    ]
    mock_client = MockSupabaseClient(outfits=outfits)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        # 1. Fetch all saved looks (no tag filter)
        res_all = await list_saved_outfits(tag=None, token="dummy-token", user=test_user)
        assert res_all.total == 2
        assert sorted(res_all.available_tags) == ["Date Night", "Vacation", "Work"]

        # 2. Filter by "Work"
        res_work = await list_saved_outfits(tag="Work", token="dummy-token", user=test_user)
        assert res_work.total == 1
        assert res_work.outfits[0].id == "outfit-work-1"

        # 3. Filter by "Date Night"
        res_date = await list_saved_outfits(tag="Date Night", token="dummy-token", user=test_user)
        assert res_date.total == 1
        assert res_date.outfits[0].id == "outfit-vacation-1"


@pytest.mark.anyio
async def test_unsave_outfit_clears_saved_and_tags(test_user):
    """Verify unsave_outfit sets is_saved to False and resets tags to empty list."""
    outfit_row = {
        "id": "outfit-105",
        "user_id": test_user.id,
        "is_saved": True,
        "tags": ["Work"],
    }
    mock_client = MockSupabaseClient(outfits=[outfit_row])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        res = await unsave_outfit("outfit-105", token="dummy-token", user=test_user)
        assert res["success"] is True

        updated_outfit = mock_client.tables["outfits"]._data[0]
        assert updated_outfit["is_saved"] is False
        assert updated_outfit["tags"] == []


@pytest.mark.anyio
async def test_outfit_dislike_event_clears_saved_status_and_tags(test_user):
    """Verify that 'Not For Me' (dislike event) clears saved state and tags while recording event."""
    outfit_row = {
        "id": "outfit-106",
        "user_id": test_user.id,
        "occasion": "casual",
        "is_saved": True,
        "tags": ["Work"],
    }
    mock_client = MockSupabaseClient(outfits=[outfit_row], outfit_events=[])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = RecordOutfitEventRequest(event_type="dislike")
        res = await record_outfit_event("outfit-106", body=req, token="dummy-token", user=test_user)

        assert res.event_type == "dislike"

        # Check outfit row updated to is_saved=False and tags=[]
        updated_outfit = mock_client.tables["outfits"]._data[0]
        assert updated_outfit["is_saved"] is False
        assert updated_outfit["tags"] == []

        # Check event recorded in outfit_events
        assert len(mock_client.tables["outfit_events"].inserted) == 1


@pytest.mark.anyio
async def test_generate_outfits_response_includes_core_signature(test_user):
    """Verify that every generated outfit response includes a stable core_signature."""
    wardrobe = [
        {
            "id": "top-101",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "primary_color": "#000000",
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "btm-102",
            "user_id": test_user.id,
            "category": "bottom",
            "slot": "bottom",
            "primary_color": "#1E3A8A",
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "shoe-103",
            "user_id": test_user.id,
            "category": "shoes",
            "slot": "shoes",
            "primary_color": "#FFFFFF",
            "formality": 1,
            "occasions": ["casual", "all_season"],
            "seasons": ["all_season"],
            "is_available": True,
        },
    ]
    mock_client = MockSupabaseClient(wardrobe_items=wardrobe)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=True,
            occasion="casual",
            season="all_season",
            limit=2,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)
        assert len(res.outfits) > 0
        for outfit in res.outfits:
            assert hasattr(outfit, "core_signature")
            assert isinstance(outfit.core_signature, list)
            assert len(outfit.core_signature) > 0
            # Confirm sorted (slot, id) pairs
            slots_in_sig = [slot for slot, it_id in outfit.core_signature]
            assert "top" in slots_in_sig
            assert "bottom" in slots_in_sig
            # Peripheral shoes must not be in core signature
            assert "shoes" not in slots_in_sig


@pytest.mark.anyio
async def test_shuffle_excludes_matching_signatures_when_alternatives_exist(test_user):
    """Verify that shuffle request with exclude_core_signatures excludes them when alternatives exist."""
    wardrobe = [
        # Core 1: top-1 + btm-1
        {
            "id": "top-1",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "primary_color": "#000000",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        # Core 2: top-2 + btm-1
        {
            "id": "top-2",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "primary_color": "#FFFFFF",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "btm-1",
            "user_id": test_user.id,
            "category": "bottom",
            "slot": "bottom",
            "primary_color": "#1E3A8A",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "shoe-1",
            "user_id": test_user.id,
            "category": "shoes",
            "slot": "shoes",
            "primary_color": "#333333",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
    ]
    mock_client = MockSupabaseClient(wardrobe_items=wardrobe)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        # Initial request: get 1 outfit
        req_initial = GenerateOutfitsRequest(
            wardrobe_only=True,
            occasion="casual",
            season="all_season",
            limit=1,
            is_shuffle=False,
        )
        res_initial = await generate_outfit_recommendations(req_initial, token="dummy-token", user=test_user)
        assert len(res_initial.outfits) == 1
        initial_sig = res_initial.outfits[0].core_signature
        assert len(initial_sig) > 0

        # Shuffle request: pass initial signature to exclude
        req_shuffle = GenerateOutfitsRequest(
            wardrobe_only=True,
            occasion="casual",
            season="all_season",
            limit=1,
            is_shuffle=True,
            exclude_core_signatures=[initial_sig],
        )
        res_shuffle = await generate_outfit_recommendations(req_shuffle, token="dummy-token", user=test_user)
        assert len(res_shuffle.outfits) == 1
        shuffle_sig = res_shuffle.outfits[0].core_signature
        # Shuffled signature must NOT match the excluded signature
        assert shuffle_sig != initial_sig


@pytest.mark.anyio
async def test_shuffle_exhaustion_returns_truthful_partial_result(test_user):
    """Verify that when all valid combinations are excluded on shuffle, truthful status and message are returned without repeating excluded looks."""
    wardrobe = [
        {
            "id": "top-1",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "primary_color": "#000000",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "btm-1",
            "user_id": test_user.id,
            "category": "bottom",
            "slot": "bottom",
            "primary_color": "#1E3A8A",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "shoe-1",
            "user_id": test_user.id,
            "category": "shoes",
            "slot": "shoes",
            "primary_color": "#333333",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
    ]
    mock_client = MockSupabaseClient(wardrobe_items=wardrobe)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        # Exclude the only core
        req = GenerateOutfitsRequest(
            wardrobe_only=True,
            occasion="casual",
            season="all_season",
            limit=3,
            is_shuffle=True,
            exclude_core_signatures=[[("bottom", "btm-1"), ("top", "top-1")]],
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)
        # Must return empty outfits list, NOT silently repeating the excluded outfit
        assert len(res.outfits) == 0
        assert res.status == "no_matching_combinations"
        assert "All valid looks have been shown" in (res.message or "")


def test_tag_validation_canonicalization_and_whitespace():
    """Verify that validate_and_normalize_tags canonicalizes case and collapses irregular whitespace."""
    raw = ["  date   night  ", "work", "WEDDING", " vacation ", "TRY   LATER"]
    result = validate_and_normalize_tags(raw)
    assert result == ["Date Night", "Work", "Wedding", "Vacation", "Try Later"]


def test_tag_validation_deduplicates_identical_canonical_tags():
    """Verify that duplicate tags under case/whitespace variations are deduplicated preserving order."""
    raw = ["Work", "work", "  WORK  ", "Date Night", "date night"]
    result = validate_and_normalize_tags(raw)
    assert result == ["Work", "Date Night"]


def test_tag_validation_rejects_unsupported_tag():
    """Verify that any tag outside the approved list raises AppException with status 422 and code INVALID_TAG."""
    with pytest.raises(AppException) as exc_info:
        validate_and_normalize_tags(["Gym"])
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "INVALID_TAG"
    assert "Unsupported tag 'Gym'" in exc_info.value.message


def test_tag_validation_rejects_empty_tag_string():
    """Verify that an empty or whitespace-only tag string raises AppException with status 422."""
    with pytest.raises(AppException) as exc_info:
        validate_and_normalize_tags(["Work", "   "])
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "INVALID_TAG"


@pytest.mark.anyio
async def test_save_outfit_rejects_unsupported_tags(test_user):
    """Verify that save_outfit rejects unsupported tags with 422 INVALID_TAG."""
    outfit_row = {
        "id": "outfit-tag-val-1",
        "user_id": test_user.id,
        "occasion": "casual",
        "is_saved": False,
        "tags": [],
    }
    mock_client = MockSupabaseClient(outfits=[outfit_row])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = SaveOutfitRequest(tags=["Clubbing"])
        with pytest.raises(AppException) as exc_info:
            await save_outfit("outfit-tag-val-1", body=req, token="dummy-token", user=test_user)
        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "INVALID_TAG"
        assert "Unsupported tag 'Clubbing'" in exc_info.value.message


@pytest.mark.anyio
async def test_update_outfit_tags_rejects_unsupported_tags(test_user):
    """Verify that update_outfit_tags rejects unsupported tags with 422 INVALID_TAG."""
    outfit_row = {
        "id": "outfit-tag-val-2",
        "user_id": test_user.id,
        "occasion": "casual",
        "is_saved": True,
        "tags": ["Work"],
    }
    mock_client = MockSupabaseClient(outfits=[outfit_row])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = UpdateOutfitTagsRequest(tags=["Party"])
        with pytest.raises(AppException) as exc_info:
            await update_outfit_tags("outfit-tag-val-2", body=req, token="dummy-token", user=test_user)
        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "INVALID_TAG"
        assert "Unsupported tag 'Party'" in exc_info.value.message


@pytest.mark.anyio
async def test_update_outfit_tags_empty_list_does_not_restore_default(test_user):
    """Verify that updating tags with empty list [] clears tags and does NOT restore ['Try Later']."""
    outfit_row = {
        "id": "outfit-tag-val-3",
        "user_id": test_user.id,
        "occasion": "work",
        "is_saved": True,
        "tags": ["Work", "Date Night"],
    }
    mock_client = MockSupabaseClient(outfits=[outfit_row])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = UpdateOutfitTagsRequest(tags=[])
        res = await update_outfit_tags("outfit-tag-val-3", body=req, token="dummy-token", user=test_user)
        assert res["success"] is True
        assert res["tags"] == []

        updated_row = mock_client.tables["outfits"]._data[0]
        assert updated_row["tags"] == []


@pytest.mark.anyio
async def test_list_saved_outfits_canonicalizes_filter_tag(test_user):
    """Verify that list_saved_outfits canonicalizes filter tag so case/whitespace variations match stored looks."""
    outfits = [
        {
            "id": "outfit-match-1",
            "user_id": test_user.id,
            "occasion": "work",
            "is_saved": True,
            "tags": ["Work"],
            "score": 0.85,
        },
    ]
    mock_client = MockSupabaseClient(outfits=outfits)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        # Query with lowercase and irregular whitespace
        res = await list_saved_outfits(tag="  work  ", token="dummy-token", user=test_user)
        assert res.total == 1
        assert res.outfits[0].id == "outfit-match-1"


@pytest.mark.anyio
async def test_list_saved_outfits_rejects_unsupported_tag_filter(test_user):
    """Verify that list_saved_outfits rejects unsupported tag filters with 422 INVALID_TAG."""
    mock_client = MockSupabaseClient(outfits=[])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        with pytest.raises(AppException) as exc_info:
            await list_saved_outfits(tag="Festival", token="dummy-token", user=test_user)
        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "INVALID_TAG"
        assert "Unsupported tag filter 'Festival'" in exc_info.value.message


@pytest.mark.anyio
async def test_list_saved_outfits_rejects_empty_tag_filter(test_user):
    """Verify that list_saved_outfits rejects empty whitespace tag filter with 422 INVALID_TAG."""
    mock_client = MockSupabaseClient(outfits=[])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        with pytest.raises(AppException) as exc_info:
            await list_saved_outfits(tag="   ", token="dummy-token", user=test_user)
        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "INVALID_TAG"


@pytest.mark.anyio
async def test_save_outfit_event_write_failure_leaves_outfit_unsaved(test_user):
    """Verify Option A fail-closed consistency: if outfit_events insert fails,

    save_outfit raises 500 SAVE_EVENT_ERROR and outfits.is_saved remains False.
    """
    outfit_row = {
        "id": "outfit-fail-event-1",
        "user_id": test_user.id,
        "occasion": "casual",
        "vibe": "minimal",
        "skeleton": "top_bottom",
        "is_saved": False,
        "tags": [],
    }
    # fail_events_insert = True simulates database write failure on outfit_events
    mock_client = MockSupabaseClient(
        outfits=[outfit_row],
        outfit_events=[],
        fail_events_insert=True,
    )

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        with pytest.raises(AppException) as exc_info:
            await save_outfit("outfit-fail-event-1", body=None, token="dummy-token", user=test_user)

        assert exc_info.value.status_code == 500
        assert exc_info.value.code in ("SAVE_ERROR", "SAVE_EVENT_ERROR")
        assert any(term in exc_info.value.message for term in ("Unable to save outfit", "Outfit was not saved"))

        # Verify outfit row was NOT marked as saved
        unmodified_outfit = mock_client.tables["outfits"]._data[0]
        assert unmodified_outfit["is_saved"] is False
        assert unmodified_outfit["tags"] == []

        # Verify no event row was left inserted
        assert len(mock_client.tables["outfit_events"].inserted) == 0


@pytest.mark.anyio
async def test_save_outfit_mixed_look_metadata_covers_catalog_and_wardrobe(test_user):
    """Verify that event metadata includes actual catalog styling attributes without fabricating wardrobe fields."""
    outfit_row = {
        "id": "outfit-mixed-meta-1",
        "user_id": test_user.id,
        "occasion": "work",
        "vibe": "classic",
        "skeleton": "top_bottom",
        "is_saved": False,
        "tags": [],
    }
    outfit_items = [
        {
            "outfit_id": "outfit-mixed-meta-1",
            "slot": "top",
            "source_type": "wardrobe",
            "wardrobe_items": {
                "category": "tops",
                "slot": "top",
                "sub_category": "oxford-shirt",
                "primary_color": "white",
                "color_tags": ["white", "ivory"],
                "style_tags": ["classic", "minimal"],
            },
        },
        {
            "outfit_id": "outfit-mixed-meta-1",
            "slot": "bottom",
            "source_type": "catalog",
            "products": {
                "category": "Trousers",
                "slot": "bottom",
                "subtype": "chinos",
                "color_tags": ["khaki", "beige"],
                "colors": ["khaki"],
                "style_tags": ["smart casual"],
            },
        },
    ]
    mock_client = MockSupabaseClient(
        outfits=[outfit_row],
        outfit_items=outfit_items,
        outfit_events=[],
    )

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        res = await save_outfit("outfit-mixed-meta-1", body=None, token="dummy-token", user=test_user)
        assert res.success is True
        assert res.is_saved is True

        # Check recorded event metadata
        events = mock_client.tables["outfit_events"].inserted
        assert len(events) == 1
        ev_meta = events[0]["metadata"]

        # Wardrobe item attributes included
        assert "white" in ev_meta["colors"]
        assert "ivory" in ev_meta["colors"]
        assert "tops" in ev_meta["categories"]
        assert "oxford-shirt" in ev_meta["categories"]
        assert "classic" in ev_meta["styles"]
        assert "minimal" in ev_meta["styles"]

        # Catalog product attributes included
        assert "khaki" in ev_meta["colors"]
        assert "beige" in ev_meta["colors"]
        assert "trousers" in ev_meta["categories"]
        assert "chinos" in ev_meta["categories"]
        assert "smart casual" in ev_meta["styles"]

        # Default tag Try Later included
        assert ev_meta["tags"] == ["Try Later"]


@pytest.mark.anyio
async def test_update_outfit_tags_does_not_insert_event(test_user):
    """Verify PUT /{outfit_id}/tags updates tags and does NOT touch outfit_events."""
    outfit_row = {
        "id": "outfit-tag-update-1",
        "user_id": test_user.id,
        "occasion": "work",
        "skeleton": "top_bottom",
        "is_saved": True,
        "tags": ["Work"],
    }
    mock_client = MockSupabaseClient(outfits=[outfit_row], outfit_events=[])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = UpdateOutfitTagsRequest(tags=["Date Night", "Vacation"])
        res = await update_outfit_tags("outfit-tag-update-1", body=req, token="dummy-token", user=test_user)

        assert res["success"] is True
        assert res["tags"] == ["Date Night", "Vacation"]

        # outfit_events must have 0 inserts
        assert len(mock_client.tables["outfit_events"].inserted) == 0


@pytest.mark.anyio
async def test_record_outfit_event_save_is_idempotent(test_user):
    """Verify that calling POST /events with save when a save event already exists does not duplicate the event."""
    outfit_row = {
        "id": "outfit-ev-save-1",
        "user_id": test_user.id,
        "occasion": "casual",
        "vibe": "classic",
        "skeleton": "top_bottom",
    }
    existing_save_event = {
        "id": "existing-ev-uuid-1",
        "user_id": test_user.id,
        "outfit_id": "outfit-ev-save-1",
        "event_type": "save",
        "metadata": {"tags": ["Work"]},
        "created_at": "2026-10-21T12:00:00Z",
    }
    mock_client = MockSupabaseClient(
        outfits=[outfit_row],
        outfit_events=[existing_save_event],
    )

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = RecordOutfitEventRequest(event_type="save")
        res = await record_outfit_event("outfit-ev-save-1", body=req, token="dummy-token", user=test_user)

        # Returns existing event
        assert res.id == "existing-ev-uuid-1"
        assert res.event_type == "save"

        # No new row inserted
        assert len(mock_client.tables["outfit_events"].inserted) == 0


# ==============================================================================
# Step 5: Sparse Wardrobe Recommendation Behavior Tests
# ==============================================================================

@pytest.mark.anyio
async def test_case_1_sparse_wardrobe_with_eligible_catalog_products(test_user):
    """Case 1: Sparse wardrobe (2 garments) automatically completed with eligible catalog product without error."""
    wardrobe = [
        {
            "id": "11111111-0001-0000-0000-000000000000",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "sub_category": "t-shirt",
            "primary_color": "#FFFFFF",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "22222222-0001-0000-0000-000000000000",
            "user_id": test_user.id,
            "category": "bottom",
            "slot": "bottom",
            "sub_category": "jeans",
            "primary_color": "#1E3A8A",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
    ]

    catalog = [
        {
            "id": "33333333-0001-0000-0000-000000000000",
            "name": "Everyday White Sneaker",
            "category": "shoes",
            "slot": "shoes",
            "audience": "unisex",
            "price_cents": 199900,
            "color_tags": ["#FFFFFF"],
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
        }
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            occasion="casual",
            season="all_season",
            limit=2,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        # Must not show an error or missing_required_slots solely because the wardrobe has only 2 garments
        assert res.status in ("success", "partial_results")
        assert len(res.outfits) == 1

        outfit = res.outfits[0]
        # Never mislabel catalog-completed look as wardrobe-only
        assert outfit.wardrobe_only is False
        assert outfit.fallback_reason == "shortfall_catalog_completion"
        assert outfit.unlocked_by_product_id == "33333333-0001-0000-0000-000000000000"

        # Verify items: exactly 2 wardrobe items, 1 catalog item, no fabricated garments
        wardrobe_items = [it for it in outfit.items if it.source_type == "wardrobe"]
        catalog_items = [it for it in outfit.items if it.source_type == "catalog"]
        assert len(wardrobe_items) == 2
        assert len(catalog_items) == 1
        assert catalog_items[0].product_id == "33333333-0001-0000-0000-000000000000"
        assert catalog_items[0].name == "Everyday White Sneaker"


@pytest.mark.anyio
async def test_case_2a_sparse_wardrobe_without_eligible_catalog_products(test_user):
    """Case 2a: Sparse wardrobe where catalog has no eligible products matching occasion."""
    wardrobe = [
        {
            "id": "11111111-0002-0000-0000-000000000000",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "primary_color": "#FFFFFF",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "22222222-0002-0000-0000-000000000000",
            "user_id": test_user.id,
            "category": "bottom",
            "slot": "bottom",
            "primary_color": "#1E3A8A",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
    ]

    # Catalog only has wedding shoes, no casual shoes
    catalog = [
        {
            "id": "33333333-0002-0000-0000-000000000000",
            "name": "Luxury Formal Oxford",
            "category": "shoes",
            "slot": "shoes",
            "audience": "all",
            "price_cents": 499900,
            "color_tags": ["#000000"],
            "formality": 3,
            "occasions": ["wedding"],
            "seasons": ["all_season"],
        }
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            occasion="casual",
            season="all_season",
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 0
        assert res.status == "missing_required_slots"
        assert "shoes" in res.missing_slots
        assert "no eligible store pieces could complete a look" in (res.message or "")


@pytest.mark.anyio
async def test_case_2b_sparse_wardrobe_budget_exceeded_returns_cheapest_alternative(test_user):
    """Case 2b: Sparse wardrobe with catalog items exceeding user budget returns truthful diagnostic."""
    wardrobe = [
        {
            "id": "11111111-0003-0000-0000-000000000000",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "primary_color": "#FFFFFF",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
        {
            "id": "22222222-0003-0000-0000-000000000000",
            "user_id": test_user.id,
            "category": "bottom",
            "slot": "bottom",
            "primary_color": "#1E3A8A",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        },
    ]

    # Shoes cost 250000 cents (₹2500)
    catalog = [
        {
            "id": "33333333-0003-0000-0000-000000000000",
            "name": "Leather Low-Top Sneaker",
            "category": "shoes",
            "slot": "shoes",
            "audience": "unisex",
            "price_cents": 250000,
            "color_tags": ["#FFFFFF"],
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
        }
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        # User budget max is ₹1500 (150000 cents)
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            occasion="casual",
            season="all_season",
            budget_max=1500.0,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 0
        assert res.status == "missing_required_slots"
        assert res.budget_status == "no_products_in_budget"
        assert res.no_products_in_budget is True
        assert res.cheapest_alternative is not None
        assert res.cheapest_alternative["price_cents"] == 250000
        assert "within your budget could complete an outfit" in (res.message or "")


@pytest.mark.anyio
async def test_case_3_valid_below_threshold_looks_shown_with_clear_warning(test_user):
    """Case 3: Valid wardrobe and mixed looks below preferred quality threshold are displayed with warnings."""
    # 3a: Wardrobe look below threshold is shown with warning
    wardrobe = [
        {"id": "top-1", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#FF0000", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "bottom-1", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#00FF00", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "shoes-1", "user_id": test_user.id, "category": "shoes", "slot": "shoes", "primary_color": "#0000FF", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=[])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=True,
            min_quality_threshold=0.99,  # Very high threshold forces it below threshold
            occasion="casual",
            limit=1,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 1
        look = res.outfits[0]
        assert look.is_below_threshold is True
        assert look.quality_warning is not None
        assert "below your preferred quality threshold" in look.quality_warning
        assert res.quality_warning is not None

    # 3b: Sparse wardrobe completed with below-threshold catalog look is shown with warning (not hidden)
    sparse_wardrobe = [
        {"id": "top-2", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#FF0000", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "bottom-2", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#00FF00", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
    ]
    catalog = [
        {
            "id": "33333333-0004-0000-0000-000000000000",
            "name": "Neon Yellow Sneaker",
            "category": "shoes",
            "slot": "shoes",
            "audience": "unisex",
            "price_cents": 199900,
            "color_tags": ["#FFFF00"],
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
        }
    ]

    mock_client_sparse = MockSupabaseClient(wardrobe_items=sparse_wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client_sparse):
        req_sparse = GenerateOutfitsRequest(
            wardrobe_only=False,
            min_quality_threshold=0.99,
            occasion="casual",
            limit=1,
        )
        res_sparse = await generate_outfit_recommendations(req_sparse, token="dummy-token", user=test_user)

        assert len(res_sparse.outfits) == 1
        sparse_look = res_sparse.outfits[0]
        assert sparse_look.wardrobe_only is False
        assert sparse_look.is_below_threshold is True
        assert sparse_look.quality_warning is not None
        assert "below your preferred quality threshold" in sparse_look.quality_warning
        assert res_sparse.quality_warning is not None


@pytest.mark.anyio
async def test_case_4_genuinely_unavailable_looks_cleanly_fails_without_fabrication(test_user):
    """Case 4: Genuinely unavailable looks (e.g. 1 top only) returns clean missing slots, no fabricated items."""
    wardrobe = [
        {
            "id": "11111111-0005-0000-0000-000000000000",
            "user_id": test_user.id,
            "category": "top",
            "slot": "top",
            "primary_color": "#FFFFFF",
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
            "is_available": True,
        }
    ]

    catalog = [
        {
            "id": "33333333-0005-0000-0000-000000000000",
            "name": "White Sneaker",
            "category": "shoes",
            "slot": "shoes",
            "audience": "unisex",
            "price_cents": 199900,
            "color_tags": ["#FFFFFF"],
            "formality": 1,
            "occasions": ["casual"],
            "seasons": ["all_season"],
        }
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            occasion="casual",
            season="all_season",
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        # Cannot form an outfit with 1 top and at most 1 catalog shoes (bottoms are missing)
        assert len(res.outfits) == 0
        assert res.status == "missing_required_slots"
        assert "bottoms" in res.missing_slots


@pytest.mark.anyio
async def test_case_5_request_exceeding_unique_combinations_returns_partial_results(test_user):
    """Case 5: Requesting more looks than can be uniquely produced returns partial_results without duplication."""
    wardrobe = [
        {"id": "top-1", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#000000", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "bottom-1", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#1E3A8A", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "shoes-1", "user_id": test_user.id, "category": "shoes", "slot": "shoes", "primary_color": "#FFFFFF", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
    ]

    # Exactly 1 combination can be formed
    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=[])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=True,
            occasion="casual",
            limit=5,  # Request 5 looks when only 1 is physically possible
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 1
        assert res.status == "partial_results"
        # No duplicates or fabricated filler items
        item_sets = [tuple(sorted((it.wardrobe_item_id or it.product_id) for it in o.items if (it.wardrobe_item_id or it.product_id))) for o in res.outfits]
        assert len(item_sets) == len(set(item_sets))


# ==============================================================================
# Step 6: Recommendation Redundancy & Result-Count Reporting Tests
# ==============================================================================

@pytest.mark.anyio
async def test_step_6_duplicate_candidates_rejected(test_user):
    """Verify that exact duplicate candidates (identical sets of garment IDs) are strictly rejected."""
    wardrobe = [
        {"id": "w-top-1", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#FFFFFF", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "w-top-2", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#000000", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "w-bot-1", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#1E3A8A", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "w-shoe-1", "user_id": test_user.id, "category": "shoes", "slot": "shoes", "primary_color": "#FFFFFF", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "w-shoe-2", "user_id": test_user.id, "category": "shoes", "slot": "shoes", "primary_color": "#000000", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=[])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=True,
            occasion="casual",
            limit=4,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 4
        # Assert each returned outfit has a unique combination of items
        item_sets = [
            tuple(sorted((it.wardrobe_item_id or it.product_id) for it in o.items if (it.wardrobe_item_id or it.product_id)))
            for o in res.outfits
        ]
        assert len(item_sets) == len(set(item_sets)), "No duplicate item sets permitted across recommended outfits"


@pytest.mark.anyio
async def test_step_6_same_core_with_different_completion_items(test_user):
    """Verify that when distinct core combinations are exhausted, completing the same core with different catalog items is permitted and produces distinct looks."""
    # Sparse wardrobe: exactly 1 top and 1 bottom (1 core)
    wardrobe = [
        {"id": "w-core-top", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#FFFFFF", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "w-core-bottom", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#1E3A8A", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
    ]

    # Catalog contains 3 distinct shoes with valid UUID IDs
    catalog = [
        {"id": "44444444-0001-0000-0000-000000000000", "name": "White Canvas Sneaker", "category": "shoes", "slot": "shoes", "audience": "unisex", "price_cents": 150000, "occasions": ["casual"], "seasons": ["all_season"]},
        {"id": "44444444-0002-0000-0000-000000000000", "name": "Black Leather Oxford", "category": "shoes", "slot": "shoes", "audience": "unisex", "price_cents": 250000, "occasions": ["casual"], "seasons": ["all_season"]},
        {"id": "44444444-0003-0000-0000-000000000000", "name": "Brown Suede Chelsea Boot", "category": "shoes", "slot": "shoes", "audience": "unisex", "price_cents": 350000, "occasions": ["casual"], "seasons": ["all_season"]},
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            occasion="casual",
            limit=3,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 3
        assert res.status == "success"

        # All 3 share the same wardrobe core
        for o in res.outfits:
            assert o.wardrobe_only is False
            core_ids = {pair[1] for pair in o.core_signature}
            assert core_ids == {"w-core-top", "w-core-bottom"}

        # Each has a distinct completion product
        product_ids = [o.unlocked_by_product_id for o in res.outfits]
        assert set(product_ids) == {
            "44444444-0001-0000-0000-000000000000",
            "44444444-0002-0000-0000-000000000000",
            "44444444-0003-0000-0000-000000000000",
        }

        # Item sets are strictly unique
        item_sets = [
            tuple(sorted((it.wardrobe_item_id or it.product_id) for it in o.items if (it.wardrobe_item_id or it.product_id)))
            for o in res.outfits
        ]
        assert len(item_sets) == 3


@pytest.mark.anyio
async def test_step_6_exhausted_candidate_pools_reports_partial_results_truthfully(test_user):
    """Verify that when a wardrobe cannot produce the requested count, it reports partial_results with exact counts without implying the requested count was met."""
    wardrobe = [
        {"id": "w-top-solo", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#FFFFFF", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "w-bottom-solo", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#1E3A8A", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "w-shoe-solo", "user_id": test_user.id, "category": "shoes", "slot": "shoes", "primary_color": "#000000", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=[])

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=True,
            occasion="casual",
            limit=5,  # Requested 5, but only 1 exists
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 1
        assert res.status == "partial_results"
        assert res.message == "Found 1 of 5 requested unique outfit(s) for 'casual'. All valid combinations from your rack have been shown."
        assert "to meet your selection" not in (res.message or "")


@pytest.mark.anyio
async def test_step_6_fewer_than_requested_mixed_results_reports_truthfully(test_user):
    """Verify that when mixed recommendations return fewer than requested, it returns partial_results and truthful count, never claiming selection was met."""
    # Sparse wardrobe: 1 top, 1 bottom, no shoes
    wardrobe = [
        {"id": "w-top-1", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#FFFFFF", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "w-bot-1", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#1E3A8A", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
    ]

    # Catalog only has 2 shoes with valid UUID IDs
    catalog = [
        {"id": "55555555-0001-0000-0000-000000000000", "name": "Sneaker A", "category": "shoes", "slot": "shoes", "audience": "unisex", "price_cents": 150000, "occasions": ["casual"], "seasons": ["all_season"]},
        {"id": "55555555-0002-0000-0000-000000000000", "name": "Sneaker B", "category": "shoes", "slot": "shoes", "audience": "unisex", "price_cents": 200000, "occasions": ["casual"], "seasons": ["all_season"]},
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            occasion="casual",
            limit=4,  # Requested 4, but only 2 can be produced
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 2
        assert res.status == "partial_results"
        assert res.message == "Found 2 of 4 requested outfit(s) for 'casual', completed with store pieces. All valid combinations have been shown."
        assert "to meet your selection" not in (res.message or "")


@pytest.mark.anyio
async def test_step_1_outfit_update_failure_after_event_recording_rolls_back_event(test_user):
    """Verify atomic abort: if outfits.update fails inside transaction,
    the entire transaction aborts, leaving outfit unsaved with 0 recorded events."""
    outfit_row = {
        "id": "outfit-comp-fail-1",
        "user_id": test_user.id,
        "occasion": "casual",
        "vibe": "minimal",
        "skeleton": "top_bottom",
        "is_saved": False,
        "tags": [],
    }
    mock_client = MockSupabaseClient(
        outfits=[outfit_row],
        outfit_events=[],
        fail_outfits_update=True,  # Simulate DB failure on outfits update
        enable_save_rpc=True,      # Test atomic RPC path
    )

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        with pytest.raises(AppException) as exc_info:
            await save_outfit("outfit-comp-fail-1", body=None, token="dummy-token", user=test_user)

        assert exc_info.value.status_code == 500
        assert exc_info.value.code == "SAVE_ERROR"

        # Verify outfit row remains unsaved
        unmodified_outfit = mock_client.tables["outfits"]._data[0]
        assert unmodified_outfit["is_saved"] is False
        assert unmodified_outfit["tags"] == []

        # Verify atomic abort committed no event rows
        assert len(mock_client.tables["outfit_events"].inserted) == 0
        assert len(mock_client.tables["outfit_events"]._data) == 0


@pytest.mark.anyio
async def test_step_1_atomic_rpc_success_persists_outfit_and_event(test_user):
    """Verify that save_outfit_with_event RPC atomically persists both outfit is_saved/tags and outfit_events record."""
    outfit_row = {
        "id": "outfit-rpc-ok-1",
        "user_id": test_user.id,
        "occasion": "work",
        "vibe": "classic",
        "skeleton": "top_bottom",
        "is_saved": False,
        "tags": [],
    }
    mock_client = MockSupabaseClient(
        outfits=[outfit_row],
        outfit_events=[],
        enable_save_rpc=True,
    )

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = SaveOutfitRequest(tags=["Work"])
        res = await save_outfit("outfit-rpc-ok-1", body=req, token="dummy-token", user=test_user)

        assert res.success is True
        assert res.is_saved is True
        assert res.tags == ["Work"]

        # Verify outfit row in mock was updated by RPC
        saved_outfit = mock_client.tables["outfits"]._data[0]
        assert saved_outfit["is_saved"] is True
        assert saved_outfit["tags"] == ["Work"]

        # Verify outfit_events record was committed by RPC
        events = mock_client.tables["outfit_events"]._data
        assert len(events) == 1
        assert events[0]["event_type"] == "save"
        assert events[0]["outfit_id"] == "outfit-rpc-ok-1"


@pytest.mark.anyio
async def test_step_1_atomic_rpc_failure_rolls_back_atomically(test_user):
    """Verify that when the RPC encounters an error inside the transaction, the entire transaction aborts."""
    outfit_row = {
        "id": "outfit-rpc-fail-1",
        "user_id": test_user.id,
        "occasion": "party",
        "vibe": "glam",
        "skeleton": "dress",
        "is_saved": False,
        "tags": [],
    }
    mock_client = MockSupabaseClient(
        outfits=[outfit_row],
        outfit_events=[],
        enable_save_rpc=True,
        fail_events_insert=True,  # Simulate event insert failure inside transaction
    )

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        with pytest.raises(AppException) as exc_info:
            await save_outfit("outfit-rpc-fail-1", body=None, token="dummy-token", user=test_user)

        # In fallback or RPC failure, outfit remains unsaved
        assert exc_info.value.status_code == 500
        unmodified_outfit = mock_client.tables["outfits"]._data[0]
        assert unmodified_outfit["is_saved"] is False
        assert len(mock_client.tables["outfit_events"]._data) == 0


@pytest.mark.anyio
async def test_step_1_repeated_saves_preserve_idempotency_and_update_tags(test_user):
    """Verify that repeated saves or retagging an already-saved look updates tags without duplicate Style DNA events under both RPC and fallback."""
    outfit_row = {
        "id": "outfit-repeat-save-1",
        "user_id": test_user.id,
        "occasion": "casual",
        "vibe": "minimal",
        "skeleton": "top_bottom",
        "is_saved": False,
        "tags": [],
    }
    mock_client = MockSupabaseClient(
        outfits=[outfit_row],
        outfit_events=[],
        enable_save_rpc=True,
    )

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        # 1. First save
        res1 = await save_outfit("outfit-repeat-save-1", body=SaveOutfitRequest(tags=["Work"]), token="dummy-token", user=test_user)
        assert res1.success is True
        assert res1.tags == ["Work"]
        assert len(mock_client.tables["outfit_events"]._data) == 1

        # 2. Second save with new tags
        res2 = await save_outfit("outfit-repeat-save-1", body=SaveOutfitRequest(tags=["Work", "Vacation"]), token="dummy-token", user=test_user)
        assert res2.success is True
        assert res2.tags == ["Work", "Vacation"]

        # Style DNA event count must remain exactly 1
        assert len(mock_client.tables["outfit_events"]._data) == 1
        assert mock_client.tables["outfits"]._data[0]["tags"] == ["Work", "Vacation"]


@pytest.mark.anyio
async def test_step_2_catalog_product_with_missing_seasons_excluded_for_specific_season(test_user):
    """Verify that catalog products with missing or empty seasons metadata are excluded when a specific season is requested."""
    # Sparse wardrobe: top + bottom, requires shoes to complete
    wardrobe = [
        {"id": "w-top-w", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#000000", "formality": 1, "occasions": ["casual"], "seasons": ["winter", "all_season"], "is_available": True},
        {"id": "w-bot-w", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#1E3A8A", "formality": 1, "occasions": ["casual"], "seasons": ["winter", "all_season"], "is_available": True},
    ]

    # Catalog product has missing seasons (None or empty list)
    catalog = [
        {
            "id": "66666666-0001-0000-0000-000000000000",
            "name": "Unannotated Canvas Sneaker",
            "category": "shoes",
            "slot": "shoes",
            "audience": "unisex",
            "price_cents": 150000,
            "occasions": ["casual"],
            "seasons": [],  # Missing/empty season metadata
        }
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        # Request a specific season: 'winter'
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            occasion="casual",
            season="winter",
            limit=1,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        # Unannotated catalog product must NOT be used to assert winter compatibility without evidence
        assert len(res.outfits) == 0, "Unannotated product must not complete specific seasonal look without evidence"


@pytest.mark.anyio
async def test_step_2_catalog_product_with_missing_seasons_eligible_for_all_season(test_user):
    """Verify that catalog products with missing or empty seasons metadata remain eligible when season is all_season (no climate restriction)."""
    wardrobe = [
        {"id": "w-top-a", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#000000", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
        {"id": "w-bot-a", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#1E3A8A", "formality": 1, "occasions": ["casual"], "seasons": ["all_season"], "is_available": True},
    ]

    catalog = [
        {
            "id": "66666666-0002-0000-0000-000000000000",
            "name": "Unannotated Canvas Sneaker",
            "category": "shoes",
            "slot": "shoes",
            "audience": "unisex",
            "price_cents": 150000,
            "occasions": ["casual"],
            "seasons": None,  # None metadata
        }
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            occasion="casual",
            season="all_season",
            limit=1,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        # When no specific climate is requested (all_season), unannotated product is eligible
        assert len(res.outfits) == 1
        assert res.outfits[0].unlocked_by_product_id == "66666666-0002-0000-0000-000000000000"


@pytest.mark.anyio
async def test_step_2_catalog_product_with_explicit_all_season_eligible_for_specific_season(test_user):
    """Verify that a catalog product with explicit 'all_season' metadata is eligible to complete a specific seasonal look."""
    wardrobe = [
        {"id": "w-top-as", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#000000", "formality": 1, "occasions": ["casual"], "seasons": ["winter", "all_season"], "is_available": True},
        {"id": "w-bot-as", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#1E3A8A", "formality": 1, "occasions": ["casual"], "seasons": ["winter", "all_season"], "is_available": True},
    ]

    catalog = [
        {
            "id": "66666666-0003-0000-0000-000000000000",
            "name": "Year-Round Leather Sneaker",
            "category": "shoes",
            "slot": "shoes",
            "audience": "unisex",
            "price_cents": 150000,
            "occasions": ["casual"],
            "seasons": ["all_season"],  # Explicit all-season
        }
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            occasion="casual",
            season="winter",
            limit=1,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 1
        assert res.outfits[0].unlocked_by_product_id == "66666666-0003-0000-0000-000000000000"


@pytest.mark.anyio
async def test_step_2_catalog_product_with_matching_season_eligible(test_user):
    """Verify that a catalog product explicitly matching the target season is eligible."""
    wardrobe = [
        {"id": "w-top-m", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#000000", "formality": 1, "occasions": ["casual"], "seasons": ["winter"], "is_available": True},
        {"id": "w-bot-m", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#1E3A8A", "formality": 1, "occasions": ["casual"], "seasons": ["winter"], "is_available": True},
    ]

    catalog = [
        {
            "id": "66666666-0004-0000-0000-000000000000",
            "name": "Thermal Shearling Boot",
            "category": "shoes",
            "slot": "shoes",
            "audience": "unisex",
            "price_cents": 250000,
            "occasions": ["casual"],
            "seasons": ["winter"],  # Explicit matching season
        }
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            occasion="casual",
            season="winter",
            limit=1,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 1
        assert res.outfits[0].unlocked_by_product_id == "66666666-0004-0000-0000-000000000000"


@pytest.mark.anyio
async def test_step_2_catalog_product_with_non_matching_season_excluded(test_user):
    """Verify that a catalog product tagged with a non-matching season is strictly excluded."""
    wardrobe = [
        {"id": "w-top-nm", "user_id": test_user.id, "category": "top", "slot": "top", "primary_color": "#000000", "formality": 1, "occasions": ["casual"], "seasons": ["winter"], "is_available": True},
        {"id": "w-bot-nm", "user_id": test_user.id, "category": "bottom", "slot": "bottom", "primary_color": "#1E3A8A", "formality": 1, "occasions": ["casual"], "seasons": ["winter"], "is_available": True},
    ]

    catalog = [
        {
            "id": "66666666-0005-0000-0000-000000000000",
            "name": "Breathable Summer Espadrille",
            "category": "shoes",
            "slot": "shoes",
            "audience": "unisex",
            "price_cents": 120000,
            "occasions": ["casual"],
            "seasons": ["summer"],  # Explicitly conflicting season
        }
    ]

    mock_client = MockSupabaseClient(wardrobe_items=wardrobe, products=catalog)

    with patch("app.routers.outfits.get_user_scoped_supabase_client", return_value=mock_client):
        req = GenerateOutfitsRequest(
            wardrobe_only=False,
            occasion="casual",
            season="winter",
            limit=1,
        )
        res = await generate_outfit_recommendations(req, token="dummy-token", user=test_user)

        assert len(res.outfits) == 0, "Summer product must be excluded from winter recommendations"





