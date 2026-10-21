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
    "liquid/lfm-2.5-2.6b:free",
    "apodex/apodex-1.1-mini:free",
    "google/gemma-4-26b-a4b-it:free",
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
            prod_name = prod.get("name") or "View Piece"
            recommended_map[target_id] = RecommendedProduct(
                id=target_id,
                name=prod_name,
                price=round(int(prod.get("price_cents") or 0) / 100, 2),
                image_url=prod.get("image_url"),
                category=prod.get("category"),
            )
            display_label = prod_name if link_text == target_id else link_text
            return f"[{display_label}](/product/{target_id})"

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

    # Pass 2: Auto-link any catalog items mentioned in bold (e.g. **Product Name**)
    # that weren't formatted as markdown links by the LLM
    for name_lower, prod in sorted(catalog_by_name.items(), key=lambda x: len(x[0]), reverse=True):
        if len(name_lower) < 4:
            continue
        p_id = str(prod.get("id"))
        p_name = prod.get("name")
        if not p_id or not p_name or f"/product/{p_id}" in sanitized_text:
            continue

        bold_pattern = re.compile(rf"\*\*{re.escape(p_name)}\*\*", re.IGNORECASE)
        if bold_pattern.search(sanitized_text):
            sanitized_text = bold_pattern.sub(f"[{p_name}](/product/{p_id})", sanitized_text, count=1)
            if p_id not in recommended_map:
                recommended_map[p_id] = RecommendedProduct(
                    id=p_id,
                    name=p_name,
                    price=round(int(prod.get("price_cents") or 0) / 100, 2),
                    image_url=prod.get("image_url"),
                    category=prod.get("category"),
                )

    return sanitized_text, list(recommended_map.values())


# Stopwords to filter out conversational noise
FASHION_STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "from",
    "by", "about", "into", "through", "after", "over", "between", "out", "against",
    "during", "without", "before", "under", "around", "among", "can", "you", "help",
    "me", "i", "we", "my", "your", "our", "want", "need", "looking", "look", "like",
    "give", "show", "some", "what", "where", "how", "when", "why", "which", "who",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "please", "suggest", "recommend", "wear", "wearing", "style", "styling"
}

FASHION_CONCEPT_KEYWORDS = {
    "winter": ["outerwear", "jacket", "coat", "blazer", "hoodie", "sweatshirt", "sweater", "trench", "warm", "fleece", "boots"],
    "winterwear": ["outerwear", "jacket", "coat", "blazer", "hoodie", "sweatshirt", "sweater", "trench", "warm", "fleece", "boots"],
    "cold": ["outerwear", "jacket", "coat", "sweater", "hoodie", "boots"],
    "sneaker": ["footwear", "sneakers", "shoes"],
    "sneakers": ["footwear", "sneakers", "shoes"],
    "shoe": ["footwear", "shoes", "boots", "sneakers", "heels", "flats", "juttis"],
    "shoes": ["footwear", "shoes", "boots", "sneakers", "heels", "flats", "juttis"],
    "boot": ["footwear", "shoes", "boots"],
    "boots": ["footwear", "shoes", "boots"],
    "ethnic": ["ethnic wear", "saree", "kurta", "lehenga", "anarkali", "dupatta", "juttis"],
    "saree": ["ethnic wear", "saree", "chanderi", "banarasi", "kanjivaram", "silk"],
    "sari": ["ethnic wear", "saree", "chanderi", "banarasi", "kanjivaram", "silk"],
    "kurta": ["ethnic wear", "kurta", "ethnic_set"],
    "formal": ["formal", "blazer", "trousers", "shirt", "suit", "oxford"],
    "office": ["formal", "blazer", "trousers", "shirt", "workwear"],
    "work": ["formal", "blazer", "trousers", "shirt", "workwear"],
    "casual": ["casual", "streetwear", "denim", "t-shirt", "jeans", "joggers", "sneakers"],
    "party": ["party", "evening", "dress", "satin", "heels", "shimmer"],
    "summer": ["casual", "linen", "cotton", "dress", "shorts", "crop top"],
}


def generate_deterministic_fallback(
    message: str, catalog: List[dict]
) -> Tuple[str, List[RecommendedProduct]]:
    """Generates a helpful, structured fashion recommendation without requiring an OpenRouter API key.
    
    Guarantees that the app remains functional even when AI keys are absent or upstream APIs fail.
    Uses semantic concept matching and balanced slot selection instead of arbitrary first-n slicing.
    """
    if not catalog:
        return (
            "Welcome to StyleSense! Our styling assistant is ready, but our catalog is currently empty. "
            "Please check back soon for our latest arrivals!",
            [],
        )

    # 1. Clean message tokens, ignoring stopwords
    words = re.findall(r"[a-zA-Z0-9_-]+", message.lower())
    query_tokens = [w for w in words if w not in FASHION_STOPWORDS and len(w) > 2]

    # 2. Expand tokens using fashion concept dictionary
    target_concepts = set(query_tokens)
    for token in query_tokens:
        if token in FASHION_CONCEPT_KEYWORDS:
            target_concepts.update(FASHION_CONCEPT_KEYWORDS[token])

    # 3. Score catalog products against query concepts
    scored_items = []
    for p in catalog:
        name_lower = (p.get("name") or "").lower()
        desc_lower = (p.get("description") or "").lower()
        cat_lower = (p.get("category") or "").lower()
        slot_lower = (p.get("slot") or "").lower()

        score = 0
        # Direct token match in name / category / slot gives highest score
        for qt in query_tokens:
            if qt in name_lower:
                score += 5
            if qt in cat_lower or qt in slot_lower:
                score += 4

        # Concept matches
        for c in target_concepts:
            if c in name_lower:
                score += 3
            if c in cat_lower or c in slot_lower:
                score += 3
            if c in desc_lower:
                score += 1

        scored_items.append((score, p))

    # Sort descending by score
    scored_items.sort(key=lambda x: x[0], reverse=True)

    # 4. Pick balanced, diverse items across different slots/categories
    selected_items: List[dict] = []
    seen_slots: set[str] = set()

    # First pass: items with score > 0, ensuring distinct slots where possible
    for score, item in scored_items:
        if score > 0:
            slot = item.get("slot") or item.get("category") or "item"
            if slot not in seen_slots or len(selected_items) < 2:
                selected_items.append(item)
                seen_slots.add(slot)
            if len(selected_items) >= 3:
                break

    # If we still have fewer than 3 items, pick diverse pieces across categories
    if len(selected_items) < 3:
        for _, item in scored_items:
            if item not in selected_items:
                slot = item.get("slot") or item.get("category") or "item"
                if slot not in seen_slots or len(selected_items) < 2:
                    selected_items.append(item)
                    seen_slots.add(slot)
                if len(selected_items) >= 3:
                    break

    # Final safety fallback
    if not selected_items:
        selected_items = catalog[:3]

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
            .select("id, name, description, price_cents, category, slot, image_url")
            .limit(200)
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
        "You are StyleSense AI, a professional fashion styling assistant for our boutique store.\n\n"
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
            req_body: dict = {
                "model": model,
                "messages": [{"role": "user", "content": system_prompt}],
                "temperature": 0.7,
                "max_tokens": 1200,
            }
            # For models like nemotron-3.5-lightning, reasoning effort none disables internal
            # thinking traces so the response content is output immediately
            if "nemotron" in model.lower():
                req_body["reasoning"] = {"effort": "none"}

            async with httpx.AsyncClient(timeout=25.0) as client:
                res = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": settings.SITE_URL,
                        "X-Title": "StyleSense Fashion AI",
                    },
                    json=req_body,
                )

                if res.status_code == 200:
                    data = res.json()
                    msg = data.get("choices", [{}])[0].get("message", {})
                    raw_content = msg.get("content") or msg.get("reasoning") or ""
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
                else:
                    logger.warning(
                        f"OpenRouter model '{model}' returned HTTP {res.status_code}: {res.text[:150]}"
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
