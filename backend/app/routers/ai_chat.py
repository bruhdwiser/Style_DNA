import logging
import re
from typing import Dict, List, Optional, Tuple
import httpx
from fastapi import APIRouter
from ..core.config import settings
from ..core.supabase import get_public_supabase_client
from ..schemas.ai import ChatRequest, ChatResponse, RecommendedProduct

logger = logging.getLogger("flashfit.ai")
router = APIRouter(prefix="/ai-chat", tags=["AI Styling"])

FALLBACK_MODELS = [
    "meta-llama/llama-3.2-3b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "mistralai/mistral-7b-instruct:free",
]

# Regex pattern for markdown links: [Link Text](URL)
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def extract_and_sanitize_links(
    raw_text: str, catalog_by_id: Dict[str, dict]
) -> Tuple[str, List[RecommendedProduct]]:
    """Validates every product link in the LLM output against the real Supabase catalog.
    
    CRITICAL SECURITY & RELIABILITY GUARANTEE:
    - If a link points to a valid catalog UUID: retains [Product Name](/product/{uuid})
    - If a link points to an invalid/hallucinated ID:
      - Attempts name-match against authentic catalog items
      - If no authentic catalog match exists: strips the link, preserving text only
    - Prevents model hallucination from routing users to 404s or nonexistent products.
    """
    recommended_map: Dict[str, RecommendedProduct] = {}

    # Build lower-cased name-to-product mapping for fallback matching
    catalog_by_name = {
        p.get("name", "").strip().lower(): p for p in catalog_by_id.values() if p.get("name")
    }

    def replace_link(match: re.Match) -> str:
        link_text = match.group(1).strip()
        url = match.group(2).strip()

        # Extract product ID if link resembles /product/ID or /shop/ID or bare ID
        target_id = url
        for prefix in ("/product/", "/shop/", "product/", "shop/"):
            if target_id.startswith(prefix):
                target_id = target_id[len(prefix) :].strip()
                break

        # Case 1: Target ID directly matches an authentic catalog UUID
        if target_id in catalog_by_id:
            prod = catalog_by_id[target_id]
            recommended_map[target_id] = RecommendedProduct(
                id=target_id,
                name=prod.get("name") or link_text,
                price=round(int(prod.get("price_cents") or 0) / 100, 2),
                image_url=prod.get("image_url"),
                category=prod.get("category"),
            )
            return f"[{link_text}](/product/{target_id})"

        # Case 2: Target ID was hallucinated (e.g. /product/123), but link text matches a real product
        matched_by_name = catalog_by_name.get(link_text.lower())
        if matched_by_name:
            real_id = str(matched_by_name.get("id"))
            recommended_map[real_id] = RecommendedProduct(
                id=real_id,
                name=matched_by_name.get("name") or link_text,
                price=round(int(matched_by_name.get("price_cents") or 0) / 100, 2),
                image_url=matched_by_name.get("image_url"),
                category=matched_by_name.get("category"),
            )
            return f"[{link_text}](/product/{real_id})"

        # Case 3: Completely hallucinated product or external URL. Strip the link to plain text!
        logger.warning(
            f"Sanitized hallucinated or untrusted product link: text='{link_text}', url='{url}'"
        )
        return link_text

    sanitized_text = MARKDOWN_LINK_PATTERN.sub(replace_link, raw_text)
    return sanitized_text, list(recommended_map.values())


def generate_deterministic_fallback(
    message: str, catalog: List[dict]
) -> Tuple[str, List[RecommendedProduct]]:
    """Generates a helpful, structured fashion recommendation without requiring an OpenRouter API key.
    
    Guarantees that the app remains functional even when AI keys are absent or upstream APIs fail.
    """
    if not catalog:
        return (
            "Welcome to FlashFit! Our styling assistant is ready, but our catalog is currently empty. "
            "Please check back soon for our latest arrivals!",
            [],
        )

    # Simple keyword-based relevance matching
    msg_lower = message.lower()
    matched = [
        p
        for p in catalog
        if (p.get("name") and p["name"].lower() in msg_lower)
        or (p.get("category") and p["category"].lower() in msg_lower)
        or (p.get("description") and any(word in p["description"].lower() for word in msg_lower.split() if len(word) > 3))
    ]

    selected_items = (matched if matched else catalog)[:3]
    recommendations = []
    lines = [
        "Here are curated recommendations from our collection to elevate your style:\n"
    ]

    for p in selected_items:
        p_id = str(p.get("id"))
        p_name = p.get("name") or "Fashion Item"
        price_inr = round(int(p.get("price_cents") or 0) / 100, 2)
        category = p.get("category") or "General"
        image_url = p.get("image_url")

        lines.append(f"• [{p_name}](/product/{p_id}) — ₹{price_inr:.2f} ({category})")
        recommendations.append(
            RecommendedProduct(
                id=p_id,
                name=p_name,
                price=price_inr,
                image_url=image_url,
                category=category,
            )
        )

    lines.append(
        "\nClick any piece above to view full details, choose your size, and add it to your cart!"
    )

    return "\n".join(lines), recommendations


@router.post("", response_model=ChatResponse)
async def chat_with_stylist(payload: ChatRequest) -> ChatResponse:
    """Provides fashion styling recommendations using catalog-grounded AI inference.
    
    SECURITY & INTEGRITY:
    - Validates message shape and length (1-1000 characters).
    - Fetches up to 50 authentic products strictly via read-only queries (no database writes).
    - Verifies all returned product UUIDs against the Supabase catalog.
    - Strips hallucinated or nonexistent links.
    - Gracefully falls back to deterministic recommendations if OpenRouter is unconfigured.
    """
    supabase = get_public_supabase_client()

    # 1. Fetch available products (read-only query)
    try:
        prod_res = (
            supabase.from_("products")
            .select("id, name, description, price_cents, category, image_url")
            .limit(50)
            .execute()
        )
        catalog_list = prod_res.data or []
    except Exception as e:
        logger.error(f"Error fetching catalog for AI chat: {e}")
        catalog_list = []

    catalog_by_id = {str(p["id"]): p for p in catalog_list if "id" in p}

    # 2. If OpenRouter key is not configured, return deterministic fallback
    if not settings.OPENROUTER_API_KEY or not settings.OPENROUTER_API_KEY.strip():
        msg, recs = generate_deterministic_fallback(payload.message, catalog_list)
        return ChatResponse(
            message=msg,
            recommended_products=recs,
            model_used="deterministic-fallback",
        )

    # 3. Format catalog context with authentic UUIDs for prompt grounding
    if catalog_list:
        catalog_context = "\n".join(
            f"- {p.get('name')} (UUID: {p.get('id')}): {p.get('description') or 'No description'}, "
            f"Price: ₹{(int(p.get('price_cents') or 0) / 100):.2f}, Category: {p.get('category') or 'General'}"
            for p in catalog_list
        )
    else:
        catalog_context = "No products currently available in the catalog."

    system_prompt = (
        "You are Flashfits AI, a professional fashion styling assistant for our boutique store.\n\n"
        "**OUR STORE CATALOG** (You must ONLY recommend items from this catalog):\n"
        f"{catalog_context}\n\n"
        "**CRITICAL RULES:**\n"
        "1. Recommend ONLY items present in the catalog above.\n"
        "2. ALWAYS include clickable product links formatted with the exact UUID: [Product Name](/product/{UUID})\n"
        "   Example: [Beige Satin Blouse](/product/550e8400-e29b-41d4-a716-446655440000)\n"
        "3. State prices in Indian Rupees (₹).\n"
        "4. Suggest 2-4 complementary items to create a cohesive outfit.\n"
        "5. Keep responses concise, warm, knowledgeable, and encouraging (3-5 sentences).\n\n"
        f"**CONVERSATION HISTORY:**\n{payload.conversation_history or 'New conversation'}\n\n"
        f"**USER MESSAGE:**\n{payload.message}\n\n"
        "**YOUR STYLING ADVICE:**"
    )

    models_to_try = [settings.OPENROUTER_MODEL] + [
        m for m in FALLBACK_MODELS if m != settings.OPENROUTER_MODEL
    ]

    # 4. Attempt LLM generation across model chain
    for model in models_to_try:
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                res = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": settings.SITE_URL,
                        "X-Title": "Flashfits Fashion AI",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": system_prompt}],
                        "temperature": 0.7,
                        "max_tokens": 1200,
                    },
                )

                if res.status_code == 200:
                    data = res.json()
                    raw_content = data.get("choices", [{}])[0].get("message", {}).get("content")
                    if raw_content:
                        # 5. Sanitize model output and validate product links
                        sanitized_msg, verified_recs = extract_and_sanitize_links(
                            raw_content, catalog_by_id
                        )
                        return ChatResponse(
                            message=sanitized_msg,
                            recommended_products=verified_recs,
                            model_used=model,
                        )
        except Exception as e:
            logger.warning(f"OpenRouter model '{model}' failed: {e}. Trying next fallback...")
            continue

    # 6. If all models failed or timed out, provide graceful deterministic fallback
    logger.error("All OpenRouter models failed. Serving deterministic recommendation fallback.")
    fallback_msg, fallback_recs = generate_deterministic_fallback(payload.message, catalog_list)
    return ChatResponse(
        message=fallback_msg,
        recommended_products=fallback_recs,
        model_used="deterministic-fallback",
    )
