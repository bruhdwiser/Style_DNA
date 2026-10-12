from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from ..core.exceptions import AppException, NotFoundException
from ..core.security import require_admin
from ..core.supabase import get_admin_supabase_client, get_public_supabase_client
from ..schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
)
from ..schemas.user import AuthenticatedUser

router = APIRouter(prefix="/products", tags=["Products"])


PRODUCT_SELECT_FIELDS = (
    "id, name, description, price_cents, original_price_cents, image_url, category, "
    "is_new, is_sale, colors, sizes, created_at, audience, slot, subtype, color_tags, "
    "formality, style_tags, occasions, seasons, fit, pattern, seed_key"
)


def _row_to_product_response(row: dict) -> ProductResponse:
    return ProductResponse(
        id=str(row.get("id")),
        name=row.get("name") or "Unnamed Product",
        description=row.get("description"),
        price_cents=int(row.get("price_cents") or 0),
        original_price_cents=row.get("original_price_cents"),
        category=row.get("category") or "General",
        image_url=row.get("image_url"),
        colors=row.get("colors") or [],
        sizes=row.get("sizes") or [],
        is_new=bool(row.get("is_new")),
        is_sale=bool(row.get("is_sale")),
        created_at=row.get("created_at"),
        audience=row.get("audience") or "all",
        slot=row.get("slot"),
        subtype=row.get("subtype"),
        color_tags=row.get("color_tags") or [],
        formality=row.get("formality"),
        style_tags=row.get("style_tags") or [],
        occasions=row.get("occasions") or [],
        seasons=row.get("seasons") or [],
        fit=row.get("fit"),
        pattern=row.get("pattern"),
        seed_key=row.get("seed_key"),
    )


@router.get("", response_model=ProductListResponse)
async def list_products(
    limit: int = Query(12, ge=1, le=100, description="Number of items to return per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    search: Optional[str] = Query(None, description="Case-insensitive substring search on product name"),
    category: Optional[str] = Query(None, description="Filter by category (use 'all' for no filter)"),
    sort: str = Query("featured", description="Sorting criteria: featured, price-low, price-high, name"),
    audience: Optional[str] = Query(None, description="Filter by audience (women, unisex, men)"),
    slot: Optional[str] = Query(None, description="Filter by styling slot (top, bottom, saree, etc.)"),
    formality: Optional[int] = Query(None, ge=0, le=3, description="Filter by formality level (0-3)"),
    max_price_cents: Optional[int] = Query(None, ge=0, description="Filter by maximum price in cents/paise"),
) -> ProductListResponse:
    """Retrieves paginated products with search, category filtering, styling slot filtering, and sorting.
    
    Product UUIDs are preserved intact without any local sequential integer remapping.
    """
    supabase = get_public_supabase_client()

    query = supabase.from_("products").select(
        PRODUCT_SELECT_FIELDS,
        count="exact",
    )

    # Search filter
    if search and search.strip():
        query = query.ilike("name", f"%{search.strip()}%")

    # Category filter
    if category and category.strip().lower() != "all":
        query = query.ilike("category", category.strip())

    # Audience filter: styling suggestions use women/unisex; general storefront displays all when None
    if audience and audience.strip().lower() != "all":
        aud = audience.strip().lower()
        if aud == "women":
            query = query.in_("audience", ["women", "unisex", "all"])
        elif aud == "men":
            query = query.in_("audience", ["men", "unisex", "all"])
        else:
            query = query.eq("audience", aud)

    # Slot filter (for outfit skeleton resolution and styling suggestions)
    if slot and slot.strip():
        query = query.eq("slot", slot.strip().lower())

    # Formality filter
    if formality is not None:
        query = query.eq("formality", formality)

    # Max price filter (for budget constraints in styling suggestions)
    if max_price_cents is not None:
        query = query.lte("price_cents", max_price_cents)

    # Sorting
    if sort == "price-low":
        query = query.order("price_cents", desc=False, nulls_first=False)
    elif sort == "price-high":
        query = query.order("price_cents", desc=True, nulls_first=False)
    elif sort == "name":
        query = query.order("name", desc=False)
    else:  # 'featured' or default
        query = query.order("created_at", desc=True)

    # Pagination
    query = query.range(offset, offset + limit - 1)

    try:
        response = query.execute()
    except Exception as e:
        raise AppException(
            message=f"Failed to query products from database: {str(e)}",
            code="DATABASE_ERROR",
            status_code=500,
        )

    raw_items = response.data or []
    total_count = response.count if response.count is not None else len(raw_items)

    items = [_row_to_product_response(row) for row in raw_items]

    next_offset = offset + len(items)
    has_more = next_offset < total_count

    return ProductListResponse(
        items=items,
        total=total_count,
        next_offset=next_offset,
        has_more=has_more,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str) -> ProductResponse:
    """Retrieves full details for a single product by its Supabase UUID."""
    supabase = get_public_supabase_client()

    try:
        response = (
            supabase.from_("products")
            .select(PRODUCT_SELECT_FIELDS)
            .eq("id", product_id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        raise AppException(
            message=f"Error looking up product: {str(e)}",
            code="DATABASE_ERROR",
            status_code=500,
        )

    if not response.data or len(response.data) == 0:
        raise NotFoundException(message=f"Product with ID '{product_id}' was not found")

    return _row_to_product_response(response.data[0])


# ==============================================================================
# Administrative Product Endpoints (Protected by require_admin)
# ==============================================================================

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    admin_user: AuthenticatedUser = Depends(require_admin),
) -> ProductResponse:
    """Creates a new catalog product.
    
    SECURITY: Strict server-side authorization check ensures only verified administrators
    can perform product creation.
    """
    admin_client = get_admin_supabase_client()

    insert_data = {
        "name": payload.name,
        "description": payload.description,
        "price_cents": payload.price_cents,
        "original_price_cents": payload.original_price_cents,
        "category": payload.category,
        "image_url": payload.image_url,
        "colors": payload.colors,
        "sizes": payload.sizes,
        "is_new": payload.is_new,
        "is_sale": payload.is_sale,
        "audience": payload.audience or "all",
        "slot": payload.slot,
        "subtype": payload.subtype,
        "color_tags": payload.color_tags,
        "formality": payload.formality if payload.formality is not None else 1,
        "style_tags": payload.style_tags,
        "occasions": payload.occasions,
        "seasons": payload.seasons,
        "fit": payload.fit,
        "pattern": payload.pattern,
        "seed_key": payload.seed_key,
    }

    try:
        response = admin_client.from_("products").insert(insert_data).execute()
    except Exception as e:
        raise AppException(
            message=f"Failed to create product in database: {str(e)}",
            code="DATABASE_ERROR",
            status_code=500,
        )

    if not response.data or len(response.data) == 0:
        raise AppException(
            message="No product was returned after insertion",
            code="DATABASE_ERROR",
            status_code=500,
        )

    return _row_to_product_response(response.data[0])


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: str,
    admin_user: AuthenticatedUser = Depends(require_admin),
) -> dict:
    """Deletes a product by UUID.
    
    SECURITY: Protected by require_admin to eliminate previous unauthenticated deletion flaw.
    """
    admin_client = get_admin_supabase_client()

    try:
        response = admin_client.from_("products").delete().eq("id", product_id).execute()
    except Exception as e:
        raise AppException(
            message=f"Failed to delete product: {str(e)}",
            code="DATABASE_ERROR",
            status_code=500,
        )

    return {"success": True, "deleted_id": product_id}
