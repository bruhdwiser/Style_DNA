# Outfit Engine Architecture Decisions & Conflict Resolutions

**Status:** Approved for Implementation Planning  
**Date:** October 2026  
**Context:** Translating `OUTFIT_ENGINE_SPEC.md` and `OUTFIT_ENGINE_IMPLEMENTATION_GUIDE.md` into the active codebase (`backend/app/styling/`).

---

## 1. Conflict Resolutions

This section records explicit decisions for the 8 conflicts identified in §8 of `OUTFIT_ENGINE_IMPLEMENTATION_GUIDE.md`.

### 1.1 Occasion List Mismatch
* **Context:** The existing engine recognizes `casual`, `work`, `party`, `formal`, `gym`, `lounge`, `ethnic`, `date`, and `date_night`. The new specification proposal uses `date_night` and omits `formal`.
* **Decision:** Retain both `formal` and `date`/`date_night`.
  * Treat `date` and `date_night` as bidirectional synonyms in the canonical occasion map (`date` $\leftrightarrow$ `date_night`).
  * Preserve `formal` as a top-level occasion. In the existing wardrobe database and product catalog, many items (blazers, dress shirts, formal trousers, evening gowns, bandhgalas) are tagged `formal`. Omitting `formal` would break existing wardrobe items and occasion filters.
  * Canonical occasion set: `casual`, `work`, `party`, `formal`, `date_night` (with `date` alias), `gym`, `lounge`, `ethnic`, `wedding`.

### 1.2 Shoe Requirement Mismatch
* **Context:** The proposal states every outfit requires a shoe. The existing engine intentionally supports shoe-less wardrobes because many users upload only tops and bottoms or prefer indoor/traditional looks.
* **Decision:** Preserve shoe-less fallback when the wardrobe has no compatible shoes.
  * If a user's wardrobe contains compatible shoes (or catalog completion is enabled), candidate generation requires a valid, compatible shoe.
  * If the user's wardrobe contains **no** compatible shoes and catalog completion is disabled (`wardrobe_only=True`), the engine generates valid top+bottom or one-piece looks, annotating the outfit candidate with `shoes_included: False` and an informative message ("No compatible shoes found in your wardrobe; generated outfit without footwear").
  * This prevents zero-result dropouts for users building their digital wardrobe incrementally.

### 1.3 `E-LEH × sneakers` vs Traditional Sets Blanket Ban
* **Context:** The proposal introduces an exception allowing lehengas (`E-LEH`) with sneakers as modern fusion, but also establishes a blanket hard rule that ethnic sets and traditional bottoms strictly forbid athletic footwear (sneakers/running shoes).
* **Decision:** No sneakers with wedding or high-formality lehenga looks.
  * Differentiate by formality and occasion:
    * If `formality >= 4` or occasion is `wedding` or `festive_formal`: sneakers are **strictly forbidden** (hard exclusion).
    * If `formality <= 2` (contemporary casual fusion skirts/crop-top lehengas) and occasion is `casual` or `college`: sneakers are permitted only under explicit fusion styling.
  * Traditional sarees, sherwanis, and bridal lehengas strictly enforce forbidden edges against athletic sneakers, gym trainers, and casual flip-flops.

### 1.4 Formality Spread Interpretation
* **Context:** Proposal text states both "spread max−min $\le$ 2" and "spread $\ge$ 3 is a hard fail".
* **Decision:** Use the strict formula: if `(max(item.formality) - min(item.formality)) >= 3`, **hard fail (exclude candidate)**.
  * All items in a candidate outfit must satisfy:
    $$\Delta_{\text{formality}} = \max_{i}(f_i) - \min_{i}(f_i) \le 2$$
  * *Example:* A formal tuxedo blazer ($f=5$) cannot pair with relaxed lounge sweatpants ($f=1$); $\Delta = 4 \ge 3 \implies$ hard exclusion.
  * *Example:* A smart-casual blazer ($f=3$) with clean dark denim ($f=2$) and leather sneakers ($f=2$); $\Delta = 1 \le 2 \implies$ valid candidate.

### 1.5 Two Loud Patterns Rule
* **Context:** Proposal references both a $\times 0.2$ score multiplier (soft penalty) and a "violation" (hard exclusion) for outfits combining two loud/statement patterns.
* **Decision:** Two loud patterns is a **HARD EXCLUSION**.
  * Outfits with $\ge 2$ items having `pattern_intensity == "loud"` (or bold prints like animal print, loud floral, wide contrasting plaid) are excluded during hard filtering.
  * Combining one loud pattern with one subtle pattern (e.g., micro-check shirt + solid trousers, or bold printed skirt + solid top) is valid and evaluated by color/pattern harmony.
  * Applying a soft score penalty risks edge cases where a high base score allows visually jarring clashing prints into top-ranked recommendations.

### 1.6 Thresholds for Generation vs Gap Analysis
* **Context:** The proposal mentions a $0.55$ threshold for outfit recommendations, $0.65$ for gap analysis, and $0.70$ for high-confidence catalog suggestions.
* **Decision:** Maintain separate, explicitly named configuration constants in `backend/app/styling/rules.py`:
  * `MIN_OUTFIT_SCORE_RECOMMENDATION = 0.55`: Minimum composite score for a generated outfit to be shown to the user.
  * `MIN_OUTFIT_SCORE_GAP_ANALYSIS = 0.65`: Threshold for identifying a wardrobe gap (requires higher conviction that adding an item completes a high-quality look).
  * `MIN_OUTFIT_SCORE_CATALOG_COMPLETION = 0.60`: Minimum score when complementing a wardrobe look with a catalog item.
  * `HIGH_CONFIDENCE_THRESHOLD = 0.70`: Quality badge eligibility in UI.

### 1.7 Season Caps vs Warmth
* **Context:** The proposal defines season caps using a numerical warmth rating (1–5), whereas the existing engine uses categorical season tags (`summer`, `winter`, `monsoon`, `spring_fall`, `all_season`).
* **Decision:** Season tags take primary precedence, with inferred warmth as secondary validation.
  * Every item already has or can be mapped to categorical `season_tags`.
  * If request specifies `season="summer"`: items tagged solely for `winter` (or heavy wool/fleece outerwear) are hard-filtered out.
  * If an item lacks explicit season metadata, derive it from subcategory/fabric tags (e.g., `heavy_coat` $\implies$ `winter`, `linen_shirt` $\implies$ `summer`). Default unknown items to `all_season`.
  * Numerical warmth is computed as an optional property for layering validation (e.g., no double heavy outerwear).

### 1.8 Golden Recipes vs Hard Rules
* **Context:** Some golden recipes in styling proposals propose pairings or occasion combinations that could conflict with general pairing tables or formality caps.
* **Decision:** Hard rules **always** supersede golden recipes.
  * Golden recipes serve as skeleton templates and positive priors during candidate ranking, but they never bypass hard filters (availability, occasion exclusion, formality spread $\le 2$, forbidden footwear, two loud patterns).
  * If a recipe template yields a candidate that violates a hard filter in the given user context, that candidate is pruned.

---

## 2. Architecture & Design Principles

### 2.1 Migrate in Place (`backend/app/styling/`)
* **No parallel engine:** Do not create a separate `engine/` directory. All changes take place within `backend/app/styling/`.
* **Zero database breakage:** The production Supabase database uses existing enums and columns (`clothing_items.category`, `subcategory`, `color_palette`, `occasions`, etc.). All taxonomy normalization, piece ID assignment, and role mapping happen in-memory at the boundary of `backend/app/styling/taxonomy.py`.

### 2.2 Strict Separation of Hard Validity vs Ranking
* **Stage 1 (Pruning):** Hard constraints eliminate invalid candidates completely:
  * Availability / non-duplicate IDs
  * Skeleton core completeness
  * Pairing graph: forbidden edges ($X$)
  * Occasion exclusions
  * Formality spread ($\Delta \le 2$)
  * Pattern clash (max 1 loud pattern)
  * Season exclusion
  * Budget cap (when catalog items are included)
* **Stage 2 (Ranking):** Valid candidates are scored on $[0.0, 1.0]$ across normalized, bounded feature functions.
* **Stage 3 (Diversification):** Maximal Marginal Relevance (MMR) ensures diversity of silhouettes, color stories, and core pieces across the returned top-$K$ outfits.

### 2.3 Removal of Body-Fit from Recommendations
* **Recommendation Engine:** Remove `body_fit` scoring from `score_outfit()`, remove `body_fit` weight from `OUTFIT_RULE_CONFIG`, and remove body-shape rationale from `explain_outfit()`.
* **Profile & Consent Retention:** Retain `backend/app/styling/body_fit.py` and all body-profile endpoints, consent flags, and settings in `backend/app/routers/` for user profile features. The change strictly applies to recommendation generation and explanation text.

### 2.4 Deterministic Generation & Seeded Shuffle
* Preserving `plan_luna.md`:
  * Normal requests with identical inputs and wardrobe items produce deterministic, stable rankings.
  * Sorting and candidate deduplication use stable composite keys (score descending, garment IDs sorted).
  * An explicit "Shuffle" / "Regenerate" action passes an explicit seed or excludes prior core signatures.

### 2.5 Additive Schema Evolution
* `backend/app/schemas/outfit.py` and `backend/app/routers/outfits.py` maintain backward compatibility:
  * New fields (`vibes`, `season`, `shoes_included`, `formality_spread`) are optional with sensible defaults.
  * Existing frontend consumers (`OutfitsPage.tsx`, `api.ts`) continue to function without breaking changes.

---

## 3. Module Mapping & Responsibilities

| Spec Concept | Codebase Target | Scope of Modifications |
| :--- | :--- | :--- |
| **Canonical Taxonomy & Roles** | `backend/app/styling/taxonomy.py` | Add `PieceRole`, canonical role mappings from legacy categories, and `derive_canonical_role()` while maintaining `CATEGORY_TO_SLOT`. |
| **Skeletons & Cores** | `backend/app/styling/skeletons.py` | Add ethnic lehenga separates skeleton (`top + ethnic_bottom + dupatta/layer`). Retain `CORE_SLOTS` and `OutfitCandidate`. |
| **Hard Rules & Pairing Graph** | `backend/app/styling/rules.py` | Add symmetric pairing graph (core/stretch/forbidden edges), formality spread check ($\Delta \le 2$), two-loud-pattern check, and canonical occasion aliases. |
| **Feature Scoring & Weights** | `backend/app/styling/features.py` | Remove `body_fit`. Add `occasion_fit`, `pairing_strength`, `vibe_affinity`, `formality_fit`, and `freshness`. Rebalance weights to sum to 1.0. |
| **Explanations** | `backend/app/styling/explain.py` | Ground explanations in active feature scores and rule tags. Remove body-type explanations entirely. |
| **Variations & MMR** | `backend/app/styling/variations.py` & `generator.py` | Update variation weights to match new feature names. Ensure deterministic MMR tie-breaking. |
| **Gap Analysis & Complements** | `backend/app/styling/gaps.py` | Ground gap analysis in updated rules and $0.65$ threshold. Use symmetric pairing graph for complement recommendations. |
| **Router & Schemas** | `backend/app/routers/outfits.py` & `backend/app/schemas/outfit.py` | Add additive fields (`vibes`, `shoes_included`, `quality_notes`). Preserve atomic RPC persistence and RLS. |

---

## 4. Feature Scoring Rebalancing

### Current Weights vs Target Weights (Phase 3)

| Component | Current Weight | Target Weight | Rationale |
| :--- | :---: | :---: | :--- |
| `body_fit` | **0.26** | **0.00** | Removed per product spec from recommendation scoring. |
| `occasion_fit` | 0.14 | **0.18** | Occasion appropriateness is the primary user intent. |
| `pairing_strength` | *None* | **0.16** | Core vs stretch vs neutral pairing affinity from graph. |
| `color_harmony` | 0.20 | **0.16** | Palette harmony, neutrals, and contrast balance. |
| `style_coherence` | 0.16 | **0.14** | Archetype alignment across pieces. |
| `vibe_affinity` | *None* | **0.10** | Multi-label vibe match (e.g., streetwear, minimal, chic). |
| `formality_fit` | *None* | **0.08** | Harmony within the allowed formality spread. |
| `season_fit` | 0.12 | **0.06** | Weather/season appropriateness. |
| `freshness` | *None* | **0.06** | Novelty based on recent wear/generation history (neutral 0.5 if no history). |
| `style_dna` | *None* (ad-hoc) | **0.04** | User feedback affinity / personal style vector. |
| `layering` | 0.06 | **0.02** | Layer compatibility bonus when layering is present. |
| `novelty` | 0.06 | *Merged* | Folded into `freshness`. |
| **Total** | **1.00** | **1.00** | Clean, normalized, bounded sum to 1.00. |

---

## 5. Deliberately Deferred Work

1. **Database Schema Enum Migrations:** Altering Supabase tables or performing full column renaming is deferred to Phase 6. In-memory normalization is zero-risk and forward-compatible.
2. **Dynamic Trend Scoring Engine:** Deferred until real-time market or editorial trend ingestion feeds exist. Using placeholder trend weights would introduce pseudo-random bias.
3. **Complex Multi-Layer Stacking:** Enforcing at most one layer (jacket/cardigan/dupatta) per outfit candidate. 3+ layer stacking requires garment-level dimensional measurements not currently captured.
4. **External YAML Rule Loader:** Pairing rules and config remain in Python modules (`rules.py`) during initial phases to ensure type-checking, testability, and zero filesystem latency.
