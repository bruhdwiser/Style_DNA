from fastapi import APIRouter, Depends, status
from ..core.exceptions import AppException, NotFoundException
from ..core.security import get_current_token, get_current_user
from ..core.supabase import get_public_supabase_client, get_user_scoped_supabase_client
from ..schemas.cart import (
    CartItemCreate,
    CartItemProduct,
    CartItemResponse,
    CartItemUpdate,
    CartResponse,
)
from ..schemas.user import AuthenticatedUser

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("", response_model=CartResponse)
async def get_cart(
    current_user: AuthenticatedUser = Depends(get_current_user),
    token: str = Depends(get_current_token),
) -> CartResponse:
    """Retrieves all items in the authenticated user's cart.
    
    SECURITY: Scoped strictly to the verified Supabase user (auth.uid()).
    Preserves Postgres RLS policies on public.cart_items.
    """
    user_client = get_user_scoped_supabase_client(token)

    try:
        response = (
            user_client.from_("cart_items")
            .select(
                "id, quantity, product_id, created_at, "
                "product:products(id, name, price_cents, original_price_cents, image_url, category)"
            )
            .eq("cart_user_id", current_user.id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as e:
        raise AppException(
            message=f"Failed to fetch cart items: {str(e)}",
            code="DATABASE_ERROR",
            status_code=500,
        )

    raw_items = response.data or []
    items: list[CartItemResponse] = []
    total_cents = 0
    item_count = 0

    for row in raw_items:
        prod_data = row.get("product")
        product = None
        if prod_data and isinstance(prod_data, dict):
            product = CartItemProduct(
                id=str(prod_data.get("id")),
                name=prod_data.get("name") or "Product",
                price_cents=int(prod_data.get("price_cents") or 0),
                original_price_cents=prod_data.get("original_price_cents"),
                image_url=prod_data.get("image_url"),
                category=prod_data.get("category") or "General",
            )
            total_cents += product.price_cents * int(row.get("quantity") or 1)

        quantity = int(row.get("quantity") or 1)
        item_count += quantity

        items.append(
            CartItemResponse(
                id=str(row.get("id")),
                product_id=str(row.get("product_id")),
                quantity=quantity,
                selected_color=row.get("selected_color"),
                selected_size=row.get("selected_size"),
                product=product,
                created_at=row.get("created_at"),
            )
        )

    return CartResponse(
        items=items,
        total_cents=total_cents,
        total=round(total_cents / 100, 2),
        item_count=item_count,
    )


@router.post("", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
async def add_or_update_cart_item(
    payload: CartItemCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    token: str = Depends(get_current_token),
) -> CartItemResponse:
    """Adds a valid catalog product to the authenticated user's cart or updates its quantity.
    
    SECURITY:
    - Cart ownership is derived strictly from current_user.id, never from the request body.
    - Verified that product_id belongs to an authentic catalog product.
    - Never trusts client-supplied price or product ownership claims.
    """
    public_client = get_public_supabase_client()
    user_client = get_user_scoped_supabase_client(token)

    # 1. Verify that product exists in catalog
    try:
        prod_res = (
            public_client.from_("products")
            .select("id, name, price_cents, original_price_cents, image_url, category")
            .eq("id", payload.product_id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        raise AppException(
            message=f"Failed to verify catalog product: {str(e)}",
            code="DATABASE_ERROR",
            status_code=500,
        )

    if not prod_res.data or len(prod_res.data) == 0:
        raise NotFoundException(
            message=f"Product with UUID '{payload.product_id}' was not found in catalog"
        )

    catalog_product = prod_res.data[0]

    # 2. Ensure parent carts record exists for current_user.id
    try:
        user_client.from_("carts").upsert(
            {"user_id": current_user.id},
            on_conflict="user_id",
        ).execute()
    except Exception as e:
        raise AppException(
            message=f"Failed to ensure user cart record: {str(e)}",
            code="DATABASE_ERROR",
            status_code=500,
        )

    # 3. Upsert cart_items record
    upsert_data = {
        "cart_user_id": current_user.id,
        "product_id": payload.product_id,
        "quantity": payload.quantity,
    }

    try:
        item_res = (
            user_client.from_("cart_items")
            .upsert(
                upsert_data,
                on_conflict="cart_user_id,product_id",
            )
            .select("id, quantity, product_id, created_at")
            .execute()
        )
    except Exception as e:
        raise AppException(
            message=f"Failed to upsert cart item: {str(e)}",
            code="DATABASE_ERROR",
            status_code=500,
        )

    if not item_res.data or len(item_res.data) == 0:
        raise AppException(
            message="No cart item was returned after operation",
            code="DATABASE_ERROR",
            status_code=500,
        )

    item_row = item_res.data[0]

    return CartItemResponse(
        id=str(item_row.get("id")),
        product_id=str(item_row.get("product_id")),
        quantity=int(item_row.get("quantity")),
        selected_color=payload.selected_color,
        selected_size=payload.selected_size,
        product=CartItemProduct(
            id=str(catalog_product.get("id")),
            name=catalog_product.get("name"),
            price_cents=int(catalog_product.get("price_cents")),
            original_price_cents=catalog_product.get("original_price_cents"),
            image_url=catalog_product.get("image_url"),
            category=catalog_product.get("category"),
        ),
        created_at=item_row.get("created_at"),
    )


@router.patch("/{item_id}", response_model=CartItemResponse)
async def update_cart_item_quantity(
    item_id: str,
    payload: CartItemUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    token: str = Depends(get_current_token),
) -> CartItemResponse:
    """Updates the quantity of a specific item in the user's cart."""
    user_client = get_user_scoped_supabase_client(token)

    try:
        response = (
            user_client.from_("cart_items")
            .update({"quantity": payload.quantity})
            .eq("id", item_id)
            .eq("cart_user_id", current_user.id)
            .select(
                "id, quantity, product_id, created_at, "
                "product:products(id, name, price_cents, original_price_cents, image_url, category)"
            )
            .execute()
        )
    except Exception as e:
        raise AppException(
            message=f"Failed to update cart item: {str(e)}",
            code="DATABASE_ERROR",
            status_code=500,
        )

    if not response.data or len(response.data) == 0:
        raise NotFoundException(message=f"Cart item '{item_id}' not found in your cart")

    row = response.data[0]
    prod_data = row.get("product") or {}

    return CartItemResponse(
        id=str(row.get("id")),
        product_id=str(row.get("product_id")),
        quantity=int(row.get("quantity")),
        selected_color=row.get("selected_color"),
        selected_size=row.get("selected_size"),
        product=CartItemProduct(
            id=str(prod_data.get("id")),
            name=prod_data.get("name") or "Product",
            price_cents=int(prod_data.get("price_cents") or 0),
            original_price_cents=prod_data.get("original_price_cents"),
            image_url=prod_data.get("image_url"),
            category=prod_data.get("category") or "General",
        ),
        created_at=row.get("created_at"),
    )


@router.delete("/{item_id}", status_code=status.HTTP_200_OK)
async def remove_cart_item(
    item_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    token: str = Depends(get_current_token),
) -> dict:
    """Removes a specific item from the user's cart."""
    user_client = get_user_scoped_supabase_client(token)

    try:
        user_client.from_("cart_items").delete().eq("id", item_id).eq(
            "cart_user_id", current_user.id
        ).execute()
    except Exception as e:
        raise AppException(
            message=f"Failed to remove item from cart: {str(e)}",
            code="DATABASE_ERROR",
            status_code=500,
        )

    return {"success": True, "deleted_id": item_id}


@router.delete("", status_code=status.HTTP_200_OK)
async def clear_cart(
    current_user: AuthenticatedUser = Depends(get_current_user),
    token: str = Depends(get_current_token),
) -> dict:
    """Clears all items from the authenticated user's cart."""
    user_client = get_user_scoped_supabase_client(token)

    try:
        user_client.from_("cart_items").delete().eq(
            "cart_user_id", current_user.id
        ).execute()
    except Exception as e:
        raise AppException(
            message=f"Failed to clear cart: {str(e)}",
            code="DATABASE_ERROR",
            status_code=500,
        )

    return {"success": True, "cleared": True}
