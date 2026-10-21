# Outfit Engine Rewrite Guide

This guide translates `OUTFIT_ENGINE_SPEC.md` into staged, repository-aware instructions for a coding agent. The source spec is a product proposal, not an instruction to replace the existing architecture wholesale. Keep the existing FastAPI API, persisted outfit records, Style DNA feedback, wardrobe/catalog distinction, and privacy boundaries working while implementing it.

## Goal

Make outfit recommendations feel more intentional and varied through richer garment roles, occasion-aware compatibility, multi-label vibes, color/pattern coordination, freshness, explanations, and safe alternatives. Keep generation deterministic for the same inputs and seed. Rules decide whether a look is valid; preferences and freshness only rank valid looks.

## Repository facts to respect

- The active engine is `backend/app/styling/`; it is Python, not `engine/`.
- The API and persistence flow live in `backend/app/routers/outfits.py` and `backend/app/schemas/outfit.py`.
- The current engine uses broad categories (`top`, `bottom`, `dress`, `saree`, `ethnic_set`, `shoes`, etc.), skeletons, rules, feature weights, Style DNA, and MMR. Frontend request/response contracts are in `frontend/src/lib/api.ts` and `frontend/src/pages/OutfitsPage.tsx`.
- `plan_luna.md` already contains work on deterministic ranking and catalog shortfall behavior. Read it before duplicating or contradicting that work.
- `backend/app/styling/body_fit.py` is also connected to body guidance/profile features. The spec's removal of body-fit scoring from recommendations does **not** authorize deleting body-profile APIs, consent handling, settings, or data export/deletion behavior.
- The attached spec's `engine/data/*.yaml`, `engine/validate_data.py`, and new module paths do not match this repository. Do not create a parallel engine. If data-driven rules are adopted, place them under `backend/app/styling/data/` and load them through a small validated interface, or keep the initial rules in Python config while migrating incrementally.

## Recommended implementation decisions

1. **Migrate in place.** Add canonical `piece_id`/role metadata alongside legacy database categories. Normalize at the engine boundary; do not require a risky database-wide rename as the first step. Keep a legacy category map and ensure old wardrobe rows still generate outfits.
2. **Separate hard validity from ranking.** Pairing `X`, unavailable items, duplicate IDs, incompatible slot/core structures, occasion exclusions, season/warmth gates, and budget caps exclude candidates. Never use score weights to soften these rules.
3. **Preserve current external contracts.** Add optional request/response fields compatibly. Keep saved-look/event persistence semantics and RLS-scoped database access. Do not return generated IDs that were not durably persisted.
4. **Treat missing tags conservatively but usefully.** Missing optional attributes should not crash generation. For a conditional stretch rule, unknown condition data should not be treated as a match; a safe core pairing can still be used where available. Record the fallback in `docs/DECISIONS.md`.
5. **Do not overpromise stock.** A product row means catalog-listed unless the schema provides verified stock/availability. Preserve currency and price units consistently; the spec uses INR while backend values may use cents/decimal rupees.
6. **Dynamic means contextual and fresh, not random noise.** Use selected occasion, up to three vibes, weather/season, wardrobe history, profile preferences, and feedback to rerank. Normal generation should be repeatable; a separate explicit shuffle action may use a seed and prior core signatures.
7. **No body-shape logic in outfit ranking.** Remove its score contribution and explanation language from recommendation generation only, after checking call sites. Do not remove unrelated profile/body guidance features without a separate explicit product decision.
8. **Resolve source-spec inconsistencies before encoding them.** In `docs/DECISIONS.md`, document decisions for at least:
   - Occasion list mismatch: current engine includes `formal` and `date`; proposal uses `date_night` and omits `formal`.
   - Shoe requirement mismatch: proposal says every outfit requires a shoe, while existing engine intentionally supports shoe-less wardrobes.
   - `E-LEH × sneakers` special allowance versus its blanket rule against sneakers with traditional sets; do not allow sneakers with wedding looks.
   - Formality spread wording says `spread max−min ≤ 2` but also calls spread `≥ 3` a hard fail; use the former interpretation.
   - Two loud-pattern rule says multiplier ×0.2 but also frames it as a violation; choose whether it is a hard exclusion or severe score penalty and apply consistently.
   - Score uses a 0.55 threshold, while gap analysis uses 0.65; keep these separate and configurable.
   - Spec's season caps use warmth, whereas current engine has season tags; define precedence and behavior when one is missing.
   - Golden recipes include some pairings/occasion cases not supported by the pairing or occasion tables; reconcile recipes against hard rules instead of weakening hard rules silently.

## Suggested phases

### Phase 0 — Baseline and decisions

Inspect the current engine, schemas, API route, frontend payload/rendering, database migrations, and `plan_luna.md`. Produce `docs/DECISIONS.md` with the conflicts above, compatibility strategy, score units/thresholds, and any changes deliberately deferred. No UI redesign or database enum migration in this phase.

### Phase 1 — Canonical taxonomy and compatibility layer

Add canonical occasion aliases and piece-role metadata for the proposed taxonomy. Map legacy categories/subcategories into canonical piece IDs without changing stored rows. Represent outfit cores explicitly enough to distinguish western separates, one-piece, sets, ethnic fusion, saree, and lehenga separates. Preserve shoe-less fallback when the wardrobe has no shoes, labeling the result accurately; when shoes exist, require a valid shoe for a complete look.

### Phase 2 — Rules and candidate generation

Implement symmetric pairing data/config and evaluate core, stretch, and forbidden edges consistently. Add role overrides for blouses, occasion suitability conditions, layer compatibility, one-layer maximum, availability, budget, formality-spread, and season/warmth rules. Prune candidates during construction and retain a documented candidate cap. Verify that ethnic sets and traditional bottoms cannot acquire forbidden sneakers/loafers, independent of occasion. Add deterministic ID-based deduplication; never use object identity or memory addresses.

### Phase 3 — Contextual scoring and diversity

Refactor feature scoring to named, normalized components with config weights. Remove body-fit from recommendation score and user-facing outfit explanations. Add occasion fit, multi-vibe affinity/coherence, pairing strength, palette/pattern/statement coordination, formality fit, preference/Style DNA, and freshness. Missing user history should yield a neutral freshness score. Keep weights summing to 1 and clamp every component. Use deterministic top-N plus MMR on normal requests; explicit shuffle can exclude recent core combinations and use seeded tie-breaking. Do not include trend scoring until real trend data exists.

### Phase 4 — Explanations, complements, and gap analysis

Generate explanations only from facts/rules that actually fired. Build complement suggestions from the same pairing graph, never return forbidden edges. Reuse the valid-outfit generator for gap analysis, and clearly distinguish owned items from catalog suggestions. Descriptions must only mention strict/core complements and known item attributes. Keep catalog product text grounded in the actual catalog record.

### Phase 5 — API and frontend integration

Extend API contracts additively for vibes, season, shuffle, freshness inputs, quality warnings, and partial-result messages as needed. Preserve current defaults unless intentionally changing them with a documented compatibility decision. Keep catalog completion opt-out semantics consistent between backend and UI. Show partial results as useful results, and label any below-threshold fallback individually. Do not show an outfit as owned if it contains a catalog item.

### Phase 6 — Data migration and rollout

Only after normalization works with legacy data, decide whether DB tagging/schema migrations are required. Make migrations forward-only, additive where possible, and safe for existing records. Roll out with legacy fallback, log component scores and rejected-rule reasons without logging sensitive body data, and compare recommendation coverage before removing old paths.

## Agent prompt: inspect and plan

```text
Read OUTFIT_ENGINE_IMPLEMENTATION_GUIDE.md, OUTFIT_ENGINE_SPEC.md (if available), CLAUDE.md, and plan_luna.md. Inspect the current styling engine, outfit API/schema, frontend contract, and relevant database migrations. Do not edit code yet. Produce docs/DECISIONS.md and a concise implementation plan that resolves every conflict listed in the guide, maps spec concepts to existing modules, identifies backward-compatibility risks, and proposes small reviewable phases. Preserve privacy boundaries, RLS, saved outfit persistence, Style DNA, and shoe-less wardrobe behavior unless a decision explicitly changes them.
```

## Agent prompt: implement one phase

Use this prompt once per phase, replacing `{PHASE}` with exactly one phase number and title:

```text
Implement only {PHASE} from OUTFIT_ENGINE_IMPLEMENTATION_GUIDE.md and the approved docs/DECISIONS.md. First inspect the relevant code and current git diff. Keep changes scoped to that phase, preserve existing API/database compatibility, and do not rewrite unrelated UI or profile/body-guidance features. Treat hard outfit rules as exclusions and preference/freshness as ranking only. Update or add focused tests only when I explicitly request verification. Before finishing, summarize changed files, behavior, compatibility notes, unresolved decisions, and commands I can run to verify it.
```

## Agent prompt: review implementation

```text
Review the current diff against OUTFIT_ENGINE_IMPLEMENTATION_GUIDE.md, OUTFIT_ENGINE_SPEC.md, docs/DECISIONS.md, and CLAUDE.md. Look for invalid pairings, missing legacy mappings, behavior changes to API defaults, nondeterministic normal generation, body data in recommendation explanations/logs, ungrounded complement text, catalog ownership/persistence errors, and frontend contract mismatches. Do not edit. Report findings by severity with file and line references, then list decisions still needed.
```

## Windows command reference

Run from the repository root. These are suggestions; use only the commands appropriate to the phase and your environment.

```powershell
# Read the project instructions and plan
Get-Content -Raw CLAUDE.md
Get-Content -Raw plan_luna.md

# Locate outfit engine and API touchpoints
rg -n "generate_outfits|feature_scores|score_outfit|hard_filter_candidate|wardrobe_only|allow_one_new_item" backend/app backend/tests frontend/src

# Inspect tracked changes before implementation/review
git status --short
git diff -- backend/app/styling backend/app/routers/outfits.py backend/app/schemas/outfit.py frontend/src/lib/api.ts frontend/src/pages/OutfitsPage.tsx

# Optional verification, only when requested
.\backend\.venv\Scripts\python.exe -m pytest backend/tests
Set-Location frontend; npm run build
```

## Definition of done

- Legacy wardrobe rows still normalize and can produce recommendations.
- Hard constraints and pairing rules are applied uniformly to generation, complements, gap analysis, and catalog-completed looks.
- Normal requests are deterministic for identical inputs; shuffle is explicit and seeded.
- Scores are explainable, normalized, and do not use body-shape data.
- Missing attributes degrade predictably and never bypass a hard constraint.
- API persistence, RLS, Style DNA feedback, and owned/catalog labeling remain correct.
- Documentation records decisions, and every implementation phase has a clear diff and rollout note.
