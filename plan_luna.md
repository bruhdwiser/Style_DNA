# Implementation Plan: Deterministic Recommendations, Core Deduplication & Automatic Catalog Completion

**File Target**: `plan_luna.md`  
**Audience**: Luna / Engineering Team  
**Repository**: `Flashfits-AI`  
**Status**: DRAFT FOR REVIEW (Comprehensive Specification — Plan Only, No Code/Migrations Edited)  
**Last Updated**: October 2026

---

## Executive Summary

An audit of the outfit recommendation engine identified three critical architectural flaws:
1. **Garment Identity Bug**: `OutfitCandidate.item_ids` evaluates `getattr(item, "id", id(item))`. Since items loaded from the database are Python dictionaries, `getattr` fails and returns the CPython memory address integer (`id(item)`), breaking identity comparisons, tie-breaking, and catalog candidate detection.
2. **Forced Randomization on Normal Requests**: Both "PULL LOOKS" and "SHUFFLE ALTERNATIVES" in the frontend generate `Math.floor(Math.random() * 10000000)`, causing every generation to be treated as stochastic with score jitter and random anchor sampling.
3. **Broken Catalog Fallback & Repetitive Looks**: The engine only rejects exact item set duplicates, leading to multiple looks with identical tops and bottoms varying only by shoes. Furthermore, the catalog fallback loop fails silently due to the garment identity bug, preventing mixed store looks from ever being returned.

This plan details the complete, repository-grounded blueprint to make recommendations strictly repeatable for unchanged inputs, eliminate repetitive core garment looks, and provide automatic store-completed looks when a user's wardrobe cannot fulfill their requested look count.

---

## 1. Verified Current Behavior & Code Evidence

| Area | Current Implementation | File & Line Reference | Verification & Defect Analysis |
| :--- | :--- | :--- | :--- |
| **Garment ID Representation** | `tuple(str(getattr(item, "id", id(item))) for item in self.slots.values())` | [`backend/app/styling/skeletons.py:L28-33`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/styling/skeletons.py#L28-L33) | **P0 Defect**: Items loaded from Supabase are Python `dict`s. `getattr(dict, "id")` fails, defaulting to `id(dict)` (CPython memory address). Candidate IDs change on every request and across processes. |
| **Normal Request Seed** | `const seedToUse = customSeed !== undefined ? customSeed : Math.floor(Math.random() * 10000000)` | [`frontend/src/pages/OutfitsPage.tsx:L165`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/frontend/src/pages/OutfitsPage.tsx#L165) | **P0 Defect**: "PULL LOOKS" generates a random 7-digit integer. The server sees a non-zero seed and activates stochastic mode on every generation. |
| **Shuffle Request Seed** | `onClick={() => handleGenerate(Math.floor(Math.random() * 10000000))}` | [`frontend/src/pages/OutfitsPage.tsx:L464`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/frontend/src/pages/OutfitsPage.tsx#L464) | **P0 Defect**: Shuffle sends an arbitrary random seed without tracking visible items, offering zero rotation guarantee or repetition protection. |
| **Stochastic Engine Jitter** | `is_stochastic = seed is not None and seed != 0` | [`backend/app/styling/generator.py:L94`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/styling/generator.py#L94) | **P0 Defect**: Whenever `seed != 0`, random score jitter `[-0.02, 0.02]` is added and an anchor outfit is randomly chosen from the top 3 (`rng.choice`), making identical inputs produce different outputs. |
| **Catalog Piece Detection** | `if catalog_item_id not in cand.item_ids: continue` | [`backend/app/routers/outfits.py:L556-557`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/routers/outfits.py#L556-L557) | **P0 Defect**: Because of the `item_ids` memory-address bug, `catalog_item_id` (a string UUID) is never in `cand.item_ids`. **Catalog fallback is completely broken and produces 0 mixed looks**. |
| **Swallowed DB Persistence** | `except Exception as exc: logger.warning(...)` | [`backend/app/routers/outfits.py:L439-445`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/routers/outfits.py#L439-L445) & [`L627-633`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/routers/outfits.py#L627-L633) | **P0 Defect**: If inserting an outfit row fails (e.g., RLS, network, constraint), the failure is swallowed and the unpersisted outfit is returned to the user. Subsequent saves or ratings 404. |
| **UI Conflicting Toggles** | Two mutually exclusive switches: "Add a shop piece" (`allowOneNewItem`) and "Use only my rack" (`wardrobeOnly`) | [`frontend/src/pages/OutfitsPage.tsx:L380-415`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/frontend/src/pages/OutfitsPage.tsx#L380-L415) | **P1 Defect**: Toggling one off can leave both `false`, leading to an ambiguous engine state. If the user wants 6 looks, the engine does not automatically fill the shortfall with catalog pieces unless hardcoded threshold conditions are met. |
| **Catalog Availability / Stock** | `"is_available": True` hardcoded | [`backend/app/routers/outfits.py:L539`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/routers/outfits.py#L539) | **P1 Verified**: The `products` schema contains `price_cents`, `audience`, `slot`, `subtype`, `color_tags`, `formality`, `style_tags`, `occasions`, `seasons`, `fit`, `pattern`, but **NO `stock`, `is_available`, or `updated_at` column** exists. Catalog row presence in `products` is the sole proxy for active availability. |
| **Timestamp Change Detection** | `wardrobe_items` has `updated_at`, `products` does NOT | [`scripts/schema.sql`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/scripts/schema.sql) & migrations | **P1 Verified**: Relying purely on SQL timestamps is unsafe because `products` lacks `updated_at`, and `wardrobe_items` lacks a PostgreSQL `before update` trigger (manual DB edits do not advance timestamps). |

---

## 2. Prioritized List of Defects

1. **[P0] Object Memory Address Garment Identity**:
   `OutfitCandidate.item_ids` extracts `id(item)` instead of `_value(item, "id")`, breaking equality checks, catalog candidate detection, and tie-breaking across requests.
2. **[P0] Uncontrolled Randomization of Normal Generation**:
   Frontend generates `Math.random()` on every "PULL LOOKS" click, triggering stochastic score jitter and random anchor selection in the backend.
3. **[P0] Broken Catalog Fallback Loop**:
   Because `catalog_item_id not in cand.item_ids` always evaluates to `True`, the engine silently drops all generated mixed looks and returns empty catalog recommendations.
4. **[P0] Swallowed Persistence Failures**:
   Failed database inserts for outfits and outfit items log warnings but return transient IDs to the client, which 404 when saved or rated.
5. **[P1] Repetitive Core Garments in Multi-Look Results**:
   MMR only measures full-set Jaccard distance and silhouette tags. A user gets 3–4 looks with identical shirts and trousers, varying only by shoes.
6. **[P1] Small Wardrobe Shortfall Handling**:
   When a wardrobe cannot produce the requested limit (e.g. 6 looks), the system either duplicates looks, fails with missing slots, or fails to automatically leverage available store items.
7. **[P1] Ambiguous Store Opt-In UI**:
   The user interface has two separate switches (`allowOneNewItem` and `wardrobeOnly`) rather than a single explicit "Use only my rack" rule that defaults cleanly.
8. **[P2] Client-Side Shuffle Without Core Exclusion**:
   Clicking "SHUFFLE ALTERNATIVES" generates a random integer without passing visible core signatures, often displaying the exact same looks back to the user.

---

## 3. Core Architectural Specifications

### 3.1 Repeatability & In-Memory Content Fingerprint
- **Why Database Timestamps Alone Are Unsafe**:
  1. `public.products` has no `updated_at` column.
  2. `public.wardrobe_items` has `updated_at`, but no database-level trigger enforces auto-update if records are modified out-of-band.
- **Proposed Safe Solution: In-Memory Content Fingerprint**:
  The recommendation endpoint already loads all user wardrobe items into memory (`client.from_("wardrobe_items").select("*").eq("user_id", user.id)`). We compute a stable SHA-256 fingerprint over the actual styling-relevant attributes:
  ```python
  def compute_recommendation_fingerprint(
      user_id: str,
      wardrobe_items: list[dict[str, Any]],
      profile: dict[str, Any] | None,
      affinity_fingerprint: str,
      occasion: str,
      season: str,
      vibe: str | None,
      wardrobe_only: bool,
      budget_max: float | None,
      eligible_products: list[dict[str, Any]] | None = None,
  ) -> str:
      # Stable token representation of user's active garments
      # Hash all normalized fields actually consumed by rules, scoring,
      # affinity adjustment, and rendering; timestamps alone are insufficient.
      garment_tokens = sorted(
          json.dumps({key: it.get(key) for key in STYLING_INPUT_FIELDS}, sort_keys=True, separators=(",", ":"))
          for it in wardrobe_items
      )
      garments_hash = hashlib.sha256(";".join(garment_tokens).encode()).hexdigest()
      catalog_tokens = sorted(
          json.dumps({key: p.get(key) for key in CATALOG_INPUT_FIELDS}, sort_keys=True, separators=(",", ":"))
          for p in (eligible_products or [])
      )
      catalog_hash = hashlib.sha256(";".join(catalog_tokens).encode()).hexdigest()
      
      composite = (
          f"{user_id}|{occasion}|{season}|{vibe or ''}|{wardrobe_only}|{budget_max or 0}|"
          f"{garments_hash}|{json.dumps(profile or {}, sort_keys=True, separators=(',', ':'))}|"
          f"{affinity_fingerprint}|{catalog_hash}"
      )
      return hashlib.sha256(composite.encode()).hexdigest()
  ```
- **Normal Generate vs. Shuffle**:
  - **Normal ("PULL LOOKS")**:
    - Seed is derived deterministically: `seed = int(fingerprint[:8], 16) % 10_000_000`.
    - `is_stochastic = False`, score jitter = `0.0`.
    - Anchor candidate is strictly `ranked[0]` (top scoring look).
    - Guarantees: **Identical inputs produce identical ranked looks every single time.**
  - **Shuffle Alternatives ("SHUFFLE ALTERNATIVES")**:
    - Seed is rotated: `seed = (int(fingerprint[:8], 16) ^ (shuffle_index * 7919)) % 10_000_000`.
    - `is_stochastic = True`.
    - Frontend passes core signatures from the immediately preceding screen; the backend validates each ID against the caller's loaded wardrobe and eligible catalog set.
    - Strictly exclude previously shown core combinations while unseen valid alternatives remain. When alternatives are exhausted, return the best valid candidates with an exhaustion message rather than an error.

#### Fingerprint correctness requirements
- Define `STYLING_INPUT_FIELDS` from every field actually consumed by `hard_filter_candidate`, `score_outfit`, affinity adjustment, and explanation/rendering (including all normalized color/style tags and garment attributes).
- Include every profile/body-guidance value actually consumed by scoring, not only `body_type`.
- Fingerprint the normalized affinity result from `calculate_affinities`, or canonical event IDs plus metadata used to compute it. A latest timestamp alone can miss changes when timestamps tie or events are deleted/reset.
- Define `CATALOG_INPUT_FIELDS` from every product field used for eligibility, scoring, and rendering. Because products lack `updated_at`, hash those field values rather than relying on timestamps.
- Include all request options that change eligibility/scoring. `limit` need not change the candidate fingerprint if it only truncates the ranked list; include it if search or selection behavior depends on it.

---

### 3.2 Stable Garment Identity & Core Deduplication
- **Garment Identity**:
  In [`backend/app/styling/skeletons.py`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/styling/skeletons.py), replace `getattr(item, "id", id(item))` with `str(_value(item, "id", ""))`.
- **Core vs. Peripheral Garment Slots**:
  - `CORE_SLOTS = frozenset({"top", "bottom", "ethnic_bottom", "dress", "ethnic_set", "saree"})`
  - `PERIPHERAL_SLOTS = frozenset({"shoes", "layer", "bag", "jewelry", "dupatta"})`
- **Core Signature Property**:
  `OutfitCandidate.core_signature` should encode stable `(slot, item_id)` pairs, not only an unordered set of IDs. This preserves slot assignments and avoids accidental signature collisions.
- **MMR Core Diversity Policy**:
  The proposed `0.45` repeat-core penalty is an unvalidated hypothesis, not a fixed requirement. Compare candidate values against fixtures with varied wardrobe sizes and quality distributions before choosing one. The acceptance behavior is: select distinct core combinations before repeating a core when valid distinct candidates exist; after they are exhausted, allow unique peripheral variations up to the number of unique valid outfits.

---

### 3.3 Automatic Catalog Completion Specification

#### Trigger Policy (The Shortfall Completion Policy)
1. If the user explicitly selects **"Use only my rack"** (`wardrobe_only = True`), catalog completion **NEVER** activates.
2. If catalog use is permitted (`wardrobe_only = False`):
   - **Step A**: Generate, validate, and deduplicate wardrobe-only looks; retain candidates meeting `score >= min_quality_threshold`.
   - **Step B**: Let $W$ be the number of distinct, above-threshold wardrobe looks, capped at `limit`.
   - **Step C**: If $W < \text{limit}$, calculate shortfall $K = \text{limit} - W$.
   - **Step D**: If $K > 0$, automatically trigger catalog completion to generate up to $K$ mixed outfits.
   - If the wardrobe is missing a required slot (e.g. 0 shoes in closet), $W = 0, K = \text{limit}$; catalog completion automatically fills the missing slot.
3. If the catalog cannot fill the shortfall, show otherwise hard-rule-valid, unique, below-threshold wardrobe looks as last-resort alternatives to fill remaining requested slots. Display a clear quality warning on each affected look and in the results summary. Never claim those looks meet the quality threshold. If fewer than `limit` total valid looks remain, return successful partial results, not an error.
4. Backwards compatibility: `wardrobe_only=True` always disables catalog use. When `wardrobe_only=False`, automatic shortfall completion does not require `allow_one_new_item=True`; keep accepting the legacy field and document whether it is ignored/deprecated in this mode. Do not leave the two fields with conflicting behavior.

#### Rules for Catalog Completion
1. **Strict 1-Store-Item Limit**: Every mixed outfit must contain $\ge 1$ wardrobe items and **exactly 1** catalog store item. No look may contain 2+ catalog items.
2. **Full Styling Constraint Enforcement**:
   - `audience`: Trace the authoritative user audience source in the existing schema/API. Do not assume `style_profiles.audience` exists. If no verified audience exists, only accept products explicitly labeled `unisex` or `all`; never infer from body type, names, or images.
   - `slot`: Must match a slot that completes at least one valid skeleton for this wardrobe and request.
   - `occasions`: Must match the requested occasion or a compatibility explicitly defined by the existing occasion-cluster rules. Do not treat every `casual` product as compatible with every occasion.
   - `seasons`: Must contain the requested season, a documented compatible alias, or `all_season`. Define and test a conservative behavior for missing season tags.
   - `budget_max`: Price must satisfy `price_cents <= budget_max * 100` (if set).
   - `style_tags` / vibe: the current engine does not apply the submitted vibe to ranking. The implementation plan must either make vibe-aware scoring a prerequisite (using an explicit mapping based on the existing taxonomy) or clearly defer vibe filtering and disclose that limitation. Do not claim a mixed outfit meets a vibe that the code did not evaluate. Keep the same policy for wardrobe-only and mixed candidates.
   - Inventory: current products schema has no stock/availability field. Row presence can mean catalog-listed only, not guaranteed purchasable/in-stock. If guaranteed availability is required, propose a separate additive schema/admin change.
   - Apply actual existing formality, occasion, season, anti-clash, and scoring rules to the complete mixed candidate. Do not claim pattern-on-pattern validation unless that rule exists or is added and tested.
3. **Shortfall Filling & Ranking**:
   - Determine every slot that can validly complete a wardrobe skeleton instead of selecting one arbitrary gap.
   - Evaluate all eligible products or use a documented, tested computational cap; do not assume `shortfall * 2` is sufficient. Rank by complete-outfit compatibility, applying price only as an approved preference/filter.
   - Add each eligible product to the actual wardrobe and run the standard skeleton, hard-filter, score, and explanation pipeline. Verify every mixed candidate contains exactly one catalog product and at least one wardrobe item.
   - Deduplicate against wardrobe results and other mixed results; diversify by core garment IDs before peripheral items.
   - Combined Result: `final_outfits = wardrobe_outfits + mixed_outfits[:K]`.
4. **Behavior on Partial Catalog Fulfill**:
   - If only 2 store pieces are eligible, and total looks $W + M < \text{limit}$:
     Return the $W + M$ looks with `status: "partial_results"`.
     **This is explicitly treated as a successful partial recommendation, not an error.**
   - Banner message: `"Found 2 looks from your rack and 2 shop-completed styles. We couldn't find enough matching pieces in the shop to reach 6 looks."`
5. **Behavior on Budget Exceeded**:
   - If catalog pieces exist for the gap slot but all exceed `budget_max`:
     Return the wardrobe looks with `status: "partial_results"`, `no_products_in_budget: True`, and `cheapest_alternative` populated.
   - If no eligible catalog items satisfy hard constraints, append otherwise hard-rule-valid, unique below-threshold wardrobe looks as warned alternatives. Never weaken hard rules or misrepresent their scores just to reach `limit`.

---

## 4. Proposed Implementation Phases

### Phase 1: Pure Styling Engine Fixes (Zero DB / Zero API Changes)
*Objective: Eliminate memory address identities, implement core deduplication, and make MMR deterministic.*
1. Edit [`backend/app/styling/skeletons.py`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/styling/skeletons.py):
   - Replace `getattr(item, "id", id(item))` with `str(_value(item, "id", ""))`.
   - Add `CORE_SLOTS` and `OutfitCandidate.core_signature`.
2. Edit [`backend/app/styling/generator.py`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/styling/generator.py):
   - In `_mmr_diversify`: disable jitter for normal generation, pick the top candidate deterministically as anchor, and use a tested core-diversity policy. Treat `0.45` as a hypothesis to validate against representative fixtures, not an established value.
   - Accept `exclude_core_signatures: set[frozenset[str]] | None = None` and `is_shuffle: bool = False`.
3. Add unit tests in [`backend/tests/test_outfit_generator.py`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/tests/test_outfit_generator.py) verifying:
   - Dict string ID extraction;
   - Deterministic repeatability with `seed=0`;
   - Core combination deduplication;
   - Small wardrobe boundary handling.

### Phase 2: Router & Schema Hardening (Catalog Fallback & Persistence)
*Objective: Implement automatic shortfall completion, content fingerprinting, and strict persistence safety.*
1. Edit [`backend/app/schemas/outfit.py`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/schemas/outfit.py):
   - Add `shuffle: bool = False`, `shuffle_index: int = 0`, `exclude_core_keys: list[list[str]] = []` to `GenerateOutfitsRequest`.
   - Add `"partial_results"` to valid `status` literals in `GenerateOutfitsResponse`.
   - Add response data identifying below-threshold-but-valid fallback looks (for example `quality_warning_outfit_ids`) so the UI can label each card and show a summary warning.
2. Edit [`backend/app/routers/outfits.py`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/routers/outfits.py):
   - Implement `compute_recommendation_fingerprint(...)`.
   - Generate wardrobe-only looks first.
   - If `not body.wardrobe_only` and the count of distinct above-threshold wardrobe candidates is less than `body.limit`, calculate shortfall $K$ and generate mixed looks to fill up to $K$.
   - Preserve the approved compatibility behavior for legacy `allow_one_new_item`.
   - Use a verified audience source or restrict to `unisex`/`all`; apply season, vibe, budget, catalog-listed state, occasion, slot, and hard rules to each complete mixed look.
   - Fix catalog candidate filtering: `catalog_item_id in cand.item_ids` now succeeds because `item_ids` are string UUIDs.
   - Keep durable generation persistence in this phase because save/event endpoints require persisted outfit IDs. Never return unpersisted IDs. Since outfit and outfit_items are currently separate REST writes, verify whether an RPC/transaction function is feasible. Use an approved atomic mechanism or a documented compensating-delete strategy; if persistence is incomplete, return a structured error and do not leave orphaned rows.
   - Return `status = "partial_results"` when $0 < \text{total\_outfits} < \text{limit}$. If warned below-threshold wardrobe looks are included, return their IDs in the quality-warning response field even when the requested count is reached.

### Phase 3: Frontend Alignment (Single Toggle & Transparent UI)
*Objective: Unify "Use only my rack" toggle and show partial results clearly.*
1. Edit [`frontend/src/lib/api.ts`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/frontend/src/lib/api.ts):
   - Add `shuffle?: boolean`, `shuffle_index?: number`, `exclude_core_keys?: string[][]` to `GenerateOutfitsPayload`.
2. Edit [`frontend/src/pages/OutfitsPage.tsx`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/frontend/src/pages/OutfitsPage.tsx):
   - Replace the two conflicting switches with a single clean control:
     **"Use only my rack"** (`wardrobeOnly: boolean`, default `false`). Catalog completion is therefore on by default; the user must explicitly opt out to enforce wardrobe-only results.
     When checked, never include store items. When unchecked, show "Budget Max (Optional)" and an explanatory note: *"The shop can fill the gap if your rack cannot make enough looks."*
   - Align the API default with this product behavior or explicitly require the frontend to send `wardrobe_only=false`; document the compatibility impact for older clients that omit the field. Do not silently preserve a server default that makes the new default behavior unavailable.
   - Normal "PULL LOOKS" calls `handleGenerate(false)` (sending `shuffle: false`).
   - "SHUFFLE ALTERNATIVES" calls `handleGenerate(true)` (sending `shuffle: true`, incremented `shuffle_index`, and sanitized `exclude_core_keys`).
   - Render `status === 'partial_results'` as an informative amber banner (not an error).

---

## 5. Algorithms in Pseudocode

### 5.1 Core Garment MMR Selection
```python
def mmr_diversify_with_core_priority(
    ranked_candidates: list[tuple[float, OutfitCandidate]],
    limit: int,
    seed: int,
    is_shuffle: bool = False,
    exclude_core_signatures: set[frozenset[str]] | None = None,
) -> list[tuple[float, OutfitCandidate]]:
    if not ranked_candidates:
        return []

    rng = random.Random(seed)
    is_stochastic = is_shuffle
    excluded_cores = exclude_core_signatures or set()

    # Exclude previously shown cores while unseen valid choices exist. If all
    # alternatives are exhausted, restore the candidates and signal exhaustion.
    unseen = [(score, cand) for score, cand in ranked_candidates
              if not (is_shuffle and cand.core_signature in excluded_cores)]
    remaining = unseen if unseen else ranked_candidates

    # Deterministic primary sort: score descending, tie-break by sorted item UUIDs
    remaining.sort(key=lambda x: (-x[0], x[1].item_ids))

    # Step 2: Choose anchor
    selected = []
    if is_stochastic:
        anchor = rng.choice(remaining[:min(3, len(remaining))])
        selected.append(anchor)
        remaining = [item for item in remaining if item[1].item_ids != anchor[1].item_ids]
    else:
        selected.append(remaining.pop(0))

    # Step 3: MMR Loop
    while len(selected) < min(limit, len(ranked_candidates)) and remaining:
        best_idx = -1
        best_val = float("-inf")

        for idx, (score, cand) in enumerate(remaining):
            max_sim = max(_similarity(cand, s[1]) for s in selected)
            max_sil_sim = max(_silhouette_similarity(cand, s[1]) for s in selected)
            exact_sil_count = sum(1 for s in selected if _silhouette(cand) == _silhouette(s[1]))

            # Use a tested policy parameter for repeated core combinations.
            core_overlap = any(cand.core_signature == s[1].core_signature for s in selected)
            core_penalty = CORE_REPEAT_PENALTY if core_overlap else 0.0

            diversity_penalty = (0.20 * max_sim) + (0.35 * max_sil_sim) + (0.30 * exact_sil_count) + core_penalty
            jitter = rng.uniform(-0.015, 0.015) if is_stochastic else 0.0

            mmr_score = (0.65 * score) - diversity_penalty + jitter
            if mmr_score > best_val:
                best_val = mmr_score
                best_idx = idx

        if best_idx < 0:
            break
        selected.append(remaining.pop(best_idx))

    return selected
```

### 5.2 Automatic Shortfall Catalog Completion
```python
def generate_recommendations(user_wardrobe, request_body, profile, affinities):
    # 1. Wardrobe-only looks first
    wardrobe_candidates = engine.generate_outfits(user_wardrobe, ...)
    valid_wardrobe = [c for c in wardrobe_candidates if c.score >= request_body.min_quality_threshold]

    # 2. Check if user insisted on wardrobe only
    if request_body.wardrobe_only:
        if not valid_wardrobe:
            return empty_or_missing_slots_response()
        return success_or_partial_response(valid_wardrobe[:request_body.limit])

    # 3. Shortfall Calculation
    shortfall = request_body.limit - len(valid_wardrobe)
    if shortfall <= 0:
        return success_response(valid_wardrobe[:request_body.limit])

    # 4. Automatic Catalog Fallback for shortfall
    gap_slots = identify_valid_completion_slots(user_wardrobe, occasion=request_body.occasion)
    eligible_products = query_catalog(
        audience=verified_user_audience_or_unisex_all(profile),
        slots=gap_slots,
        occasion=request_body.occasion,
        season=request_body.season,
        budget_max=request_body.budget_max,
    )

    if not eligible_products:
        # Catalog could not fill the shortfall. Append hard-rule-valid,
        # unique below-threshold wardrobe candidates as warned alternatives.
        warned_wardrobe = select_below_threshold_valid_wardrobe_candidates(
            all_wardrobe_candidates,
            exclude=valid_wardrobe,
            limit=shortfall,
        )
        all_results = valid_wardrobe + warned_wardrobe
        return GenerateOutfitsResponse(
            outfits=all_results,
            status="success" if len(all_results) >= request_body.limit else (
                "partial_results" if all_results else "no_matching_combinations"
            ),
            quality_warning_outfit_ids=[o.id for o in warned_wardrobe],
            message=build_completion_and_quality_message(valid_wardrobe, mixed_outfits=[], warned_wardrobe=warned_wardrobe, limit=request_body.limit),
        )

    # 5. Build 1-store-item mixed outfits
    mixed_outfits = []
    for prod in eligible_products[:DOCUMENTED_AND_TESTED_CANDIDATE_CAP]:
        cand = engine.generate_mixed(user_wardrobe, store_item=prod)
        if cand and cand.score >= request_body.min_quality_threshold:
            if contains_exactly_one_catalog_item_and_at_least_one_wardrobe_item(cand):
                mixed_outfits.append(cand)

    mixed_outfits = deduplicate_and_rank_against_wardrobe(mixed_outfits, valid_wardrobe)
    mixed_outfits = mixed_outfits[:shortfall]

    # Catalog outfits get first chance to fill the shortfall. Then use any
    # remaining slots for warned below-threshold wardrobe candidates.
    remaining_slots = max(0, request_body.limit - len(valid_wardrobe) - len(mixed_outfits))
    warned_wardrobe = select_below_threshold_valid_wardrobe_candidates(
        all_wardrobe_candidates,
        exclude=valid_wardrobe,
        limit=remaining_slots,
    )
    all_outfits = valid_wardrobe + mixed_outfits + warned_wardrobe
    status = "success" if len(all_outfits) >= request_body.limit else "partial_results"
    return GenerateOutfitsResponse(
        outfits=all_outfits,
        status=status,
        quality_warning_outfit_ids=[o.id for o in warned_wardrobe],
        message=build_completion_and_quality_message(valid_wardrobe, mixed_outfits, warned_wardrobe, request_body.limit),
    )
```

---

## 6. API, Status & Message Contract

### Response Status Definitions
- `"success"`: Full requested count was returned ($N = \text{limit}$).
- `"partial_results"`: Valid looks returned, but fewer than `limit` ($0 < N < \text{limit}$). **Treated as successful recommendation in UI, displaying informative notice rather than error.**
- Quality warnings are independent of result count. If below-threshold but otherwise valid wardrobe looks are included, return their IDs (for example `quality_warning_outfit_ids`) and show a warning on each card plus a concise summary. A full count can have `status="success"` and still include quality warnings; fewer than `limit` remains `partial_results`.
- `"missing_required_slots"`: Use only for wardrobe-only mode when required rack slots are absent. If catalog use was allowed and some outfits exist, use `partial_results`; if none can be constructed, use `no_matching_combinations` with a clear reason. Do not present catalog exhaustion as a server error.
- `"no_matching_combinations"`: 0 outfits passed styling rules for the occasion/season.
- `"empty_wardrobe"`: Rack has 0 clothing pieces.
- `"error"`: Database or internal server failure.

---

## 7. Risks & Unresolved Product Decisions

1. **Catalog Inventory Proxy**:
   - *Risk*: `products` table does not have an `is_available` or `stock` column.
   - *Decision*: Row presence means "catalog-listed" only, not guaranteed purchasable or in stock. If guaranteed availability is required, propose a separate additive migration and define how admin inventory updates it.
2. **Shuffle Lookback Depth**:
   - *Decision*: Restrict `exclude_core_keys` to the **1 immediately preceding screen**. In small wardrobes, accumulating 3+ screens of history quickly leads to an empty set.
3. **Client-Side Signature Validation**:
   - *Risk*: Malicious client sending arbitrary UUIDs in `exclude_core_keys`.
   - *Mitigation*: The backend filters `exclude_core_keys` against the caller's actual wardrobe item IDs and active catalog IDs before passing them to the generator.
4. **Audience Source**:
   - `style_profiles` has no audience column in the inspected migration. Verify any alternative authoritative source; otherwise use only `unisex`/`all` catalog labels.
5. **Below-Threshold Wardrobe Looks — DECIDED**:
   - If catalog completion cannot fill the requested count, show otherwise hard-rule-valid, unique below-threshold wardrobe looks as last-resort alternatives, with an explicit warning on each affected card and a summary warning. Do not claim they meet the quality threshold.
6. **Legacy Fallback Flag**:
   - `allow_one_new_item` already exists. Specify its backward-compatible behavior when `wardrobe_only=False`; the explicit wardrobe-only choice must always take precedence.
7. **Persistence Atomicity**:
   - Outfit and item references are written separately today. Verify an RPC/transaction option or define a tested compensation path; do not return incomplete records.

---

## 8. Acceptance Criteria & Test Matrix

### Test Matrix

| # | Test Scenario | Execution Environment | Expected Result |
| :--- | :--- | :--- | :--- |
| **T1** | **Dict UUID Extraction** | Local `pytest` (Existing) | `OutfitCandidate.item_ids` resolves to `"t1"`, `"b1"`, not numeric CPython memory address strings. |
| **T2** | **Repeatability with Same Input** | Local `pytest` (Existing) | `generate_outfits()` called 10 times with identical dicts and `seed=0` produces the exact same ranked candidate order every time. |
| **T3** | **Core Garment Repetition Penalty** | Local `pytest` (Existing) | Wardrobe with 2 tops, 2 bottoms, 4 shoes: All 4 distinct top+bottom combinations are selected before any top+bottom pair repeats with alternate shoes. |
| **T4** | **Small Wardrobe Requesting 6 Looks** | Local `pytest` (Existing) | Wardrobe with 1 top, 1 bottom, 2 shoes requesting `limit=6` returns exactly 2 non-identical looks without errors or padding duplicates. |
| **T5** | **Automatic Shortfall Completion** | Local pytest with mocked catalog | Wardrobe can form 2 qualified looks; catalog use is allowed; 4 distinct mixed looks, each with exactly one catalog item and at least one wardrobe item, fill `limit=6` when enough valid products exist. |
| **T6** | **"Use Only My Rack" Enforcement** | Local `pytest` (Existing) | When `wardrobe_only=True`, 0 catalog items are added even if wardrobe produces fewer looks than `limit`. |
| **T7** | **Partial Results Status** | Local `pytest` (Existing) | When wardrobe produces 2 looks and catalog can only produce 1 look (shortfall of 4 unsatisfied), returns 3 looks with `status="partial_results"`. |
| **T8** | **Budget Cap Exclusion** | Local `pytest` (Existing) | Catalog items exceeding `budget_max` are excluded; cheapest alternative is populated if 0 products fit budget. |
| **T9** | **Audience & Occasion Filtering on Store Items** | Local pytest with mocked catalog | Verify authoritative audience behavior; absent a verified user audience, only `unisex`/`all` products qualify. Verify occasion compatibility and hard rules. |
| **T10** | **Shuffle Core Divergence** | Local pytest | Excluded core signatures are absent while unseen valid candidates exist; exhausted alternatives return valid results plus an exhaustion message. |
| **T11** | **Persistence Safety** | Local API test with mocked DB | Inject failure at outfit insert, item insert, and RPC/compensation boundary. No incomplete outfit is returned as success; no orphan remains under the approved strategy. |
| **T12** | **End-to-End Supabase RLS API** | External / Live DB Required | Verifies `/outfits/generate` respects user isolation under live PostgreSQL RLS policies; mocks do not prove RLS. |
| **T13** | **UI Shuffle Flow** | Browser Automation Required | Verifies clicking "SHUFFLE ALTERNATIVES" follows the agreed exclusion policy. Saved-look behavior is outside this phase. |
| **T14** | **Use-Only-Rack Opt-Out** | Local API test with mocked catalog | `wardrobe_only=True` never selects catalog items even when wardrobe results are fewer than requested. |
| **T15** | **Budget, Season, Vibe, and Unknown Tags** | Local pytest with mocked catalog | Out-of-budget and hard-rule-invalid products are excluded; missing tags follow the approved conservative rule; results do not claim unavailable stock data. |
| **T16** | **Catalog Candidate Search Cap** | Local pytest with mocked catalog | A better valid product beyond an arbitrary short slice is not missed; any computational cap is documented and tested. |
| **T17** | **Empty Wardrobe Boundary** | Local API test with mocked catalog | With zero wardrobe items, the one-store-item-per-look rule cannot create a mixed outfit. Return the documented empty-wardrobe/shop-gap guidance without a server error or fabricated outfit. |
| **T18** | **Below-Threshold Fallback Warning** | Local API test with mocked catalog | If catalog completion cannot fill the shortfall, include remaining unique, hard-rule-valid below-threshold wardrobe looks, identify them in response data, and render a visible warning; never label them as meeting the threshold. |

---
**End of Plan**. Awaiting review before implementation. Product decision recorded: if catalog completion cannot fill the requested count, show otherwise hard-rule-valid, unique below-threshold wardrobe looks as last-resort alternatives with a clear per-look and summary quality warning.
