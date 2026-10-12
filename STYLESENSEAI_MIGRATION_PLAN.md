# StyleSenseAI Features for FlashFit: Migration Plan

## Purpose and source of truth

This plan brings the StyleSenseAI styling experience into the existing FlashFit repository. StyleSenseAI is the product direction and feature reference; FlashFit is the implementation target and remains the codebase being changed.

The StyleSenseAI master guide contains product requirements, suggested sequencing, and ready-to-paste prompts aimed at a different FastAPI/Next.js project. Those prompts and their commands are reference material, not instructions to execute in this repository. This plan translates their useful requirements to FlashFit's Next.js App Router, Supabase Auth/Postgres/Storage, and existing OpenRouter integration. The supplied FlashFit `PROJECT_DOCUMENTATION.md` describes the current implementation and its known risks; verify its claims against source before each implementation phase.

## Product outcome

Evolve FlashFit from a catalog shopping site with a catalog-aware chatbot into a women-focused personal styling product:

1. A signed-in user builds a private digital wardrobe and edits item tags.
2. During onboarding, the user provides style preferences and body type; measurements are optional. Before each styling request, the user selects an occasion and can adjust the desired vibe.
3. The app matches those inputs against the user's wardrobe, ranks occasion-appropriate outfits using clothing compatibility and the user's chosen fit/style preferences, explains each recommendation, and supports saves and feedback.
4. When the wardrobe cannot produce enough suitable looks, the app identifies useful missing items and matches them to FlashFit's Supabase catalog. The user can opt in to a mixed outfit containing one new catalog product.
5. Feedback improves future ordering in a transparent, explainable way.

The existing catalog, product pages, authentication, and cart remain the commerce foundation. StyleSenseAI's separate FastAPI service, Redis job queue, pgvector stack, and Python model providers are not prerequisites for this plan.

## Current FlashFit baseline

Based on the supplied documentation and a focused source inspection:

- Next.js 15 App Router, React 19, TypeScript, Supabase Auth/Postgres, and an OpenRouter endpoint are already present.
- `public.products` has basic commerce fields (price, category, colors, sizes, image), but lacks the structured occasion, formality, fit, and style attributes needed for deterministic matching.
- `/api/ai-chat` reads catalog products and asks an LLM to produce shopping advice and product links. It is not a wardrobe-aware outfit engine, and its response is free text rather than a validated recommendation contract.
- There is no wardrobe, outfit, style-profile, body-profile, consent-for-sensitive-data, or recommendation-feedback flow in the documented schema/routes.
- The cart API authenticates users; the documentation also identifies unprotected product mutations/admin pages and a client-side admin password. Those access-control gaps should be closed before adding private wardrobe and profile data.
- Product IDs are UUIDs in Supabase, while the listing API maps them to local numeric IDs. Preserve UUIDs end-to-end for all new styling and catalog references, and reconcile the existing mismatch before reusing product links in new flows.

This is a planning baseline, not a full security or code audit. The repo already has local changes in `package-lock.json`, `scripts/schema.sql`, and an untracked `PROJECT_DOCUMENTATION.md`; preserve them during implementation.

## Target architecture in this repository

```text
Next.js pages and components
  ├─ styling journey: profile → wardrobe → generate → saved looks → gaps/shop
  └─ existing shop, product detail, cart, and login
          │ same-origin Next.js route handlers
          ├─ auth/session and authorization checks via Supabase user client
          ├─ deterministic outfit and gap services (TypeScript, server-side)
          ├─ catalog matching against structured Supabase product attributes
          └─ optional OpenRouter assistance, isolated from core ranking
                  │
Supabase Auth + Postgres/RLS + private Storage
```

Keep outfit generation deterministic and useful without an OpenRouter key. Use the LLM as an optional language layer only (for example, phrasing an explanation from already-selected items); it must not invent catalog IDs, override occasion exclusions, or receive photos/body measurements. For initial wardrobe tagging, use user edits and structured forms. Treat automatic image classification as a later, opt-in provider after the manual flow works.

## Implementation sequence

### Phase 0 — Baseline, identifiers, and access control

**Work:** confirm the actual Supabase schema and route behavior; make product IDs consistent from listing through detail, cart, and AI links; protect admin pages and product mutation APIs with a server-verified admin role; remove the client-side password gate and restrict/remove the debug route. Use migrations for schema and RLS changes rather than relying on dashboard-only edits.

**Why first:** the new wardrobe and profile tables contain user-owned data, and existing service-role routes can bypass RLS. Establish ownership rules before adding those records.

**Done when:** unauthenticated users cannot mutate products or access admin functions; ordinary authenticated users cannot perform admin actions; UUIDs remain intact through catalog links and cart actions; migrations can be applied without deleting existing catalog data.

### Phase 1 — Structured catalog foundation

**Work:** extend products with normalized styling attributes: audience/category and subtype, color tags, formality, style tags, occasions, seasons, and fit where applicable. Add stable seed keys and make sample/demo seeds repeatable. Keep prices in integer cents in the database and display INR consistently. Preserve the existing product table and storefront fields.

**Done when:** catalog queries can filter by product UUID, category/slot, occasion, formality, price ceiling, and style attributes; repeated seed runs do not duplicate products; existing shop/product/cart behavior still uses the same product records.

### Phase 2 — Account style profile and privacy choices

**Work:** add an onboarding/profile flow that asks for favorite styles, colors, budget, and body type. Measurements are optional, individually explained, and skippable; collect only the measurements needed to improve fit guidance. Add explicit, revocable consent records before storing measurements or sending any data to an external AI provider. Restrict profile/body data with RLS and support editing/deletion. Use neutral, body-positive fit language and do not calculate BMI, weight judgments, or attractiveness scores.

**Done when:** a user can create/update/delete only their own profile; the flow works without body measurements; sensitive fields are never exposed through public catalog routes or sent to OpenRouter; consent can be reviewed and withdrawn.

### Phase 3 — Private wardrobe and item tagging

**Work:** add a user-owned wardrobe item table and a private Supabase Storage bucket. Store image paths rather than base64 data in product rows. Add upload validation, per-user ownership policies, item CRUD, and a review/edit screen for category, colors, fit, formality, occasions, seasons, and style tags. Start with manual tags and allow an optional later classifier to propose tags for user confirmation. Include a wardrobe coverage summary by outfit slot.

**Done when:** users can upload, edit, and delete their own clothing items; signed-in users cannot read another user's images or records; incomplete/uncertain tags are visible and editable; the app reports when a wardrobe lacks a needed slot.

### Phase 4 — Explainable outfit generation

**Work:** implement a server-side TypeScript rules engine that takes the selected occasion and vibe plus the user's saved style preferences, body type, and any measurements they chose to provide. It builds valid outfit skeletons from that user's wardrobe, filters by occasion/season/formality, then ranks combinations using occasion fit, clothing attributes, color/style compatibility, and applicable fit guidance. It diversifies results and returns short explanations that identify which user inputs and clothing attributes influenced the match. Missing optional measurements must never block outfit generation. Start with women-focused categories and configurable occasion rules (college, casual, office, date, brunch, party, festive, wedding, vacation). Make dupatta optional for kurta looks and support saree + optional jewelry + shoes. Keep rules/config separate from route handlers.

**Done when:** generation uses only the caller's wardrobe and receives the selected occasion plus saved preferences/body profile; changing occasion or style preferences can change the ranked results; providing optional measurements can refine fit guidance while omitting them still works; festive/wedding restrictions prevent clearly incompatible combinations; explanations refer to actual user inputs and item attributes; missing wardrobe/profile states return structured codes the UI can handle.

### Phase 5 — Saved looks, feedback, and visible learning

**Work:** persist generated outfits and outfit-item references, then record like/dislike/save/skip events. Start learning with transparent tag-affinity counts or a small weighted ranker; use those signals to reorder already-valid outfit candidates. Add a Style DNA page that shows normalized preference affinities and event count. Do not claim visual learning or a trained proprietary model unless one is actually added and evaluated.

**Done when:** events belong to the authenticated user and valid outfits; repeated positive feedback on a tag changes later ordering in a reproducible way; users can inspect and reset learned preferences.

### Phase 6 — Gap analysis and catalog suggestions

**Work:** compare valid wardrobe-only outfits with counterfactual outfits that add one missing slot/item. Rank gaps by the number and quality of additional outfits they unlock, then match products using structured attributes and budget. Add suggestions to gap results and a user-controlled “allow one new item” option. Clearly label product recommendations as FlashFit catalog products. For empty budget matches, return an explicit reason and (optionally) the cheapest available alternative. Do not scrape retailers.

**Done when:** gap counts are stable for the same input; suggested products come from existing Supabase product UUIDs and obey budget/occasion filters; wardrobe-only mode never includes products; mixed outfits clearly identify the new item and why fallback occurred.

### Phase 7 — Complete the user journey and integrate the existing AI assistant

**Work:** build mobile-first screens in this order: onboarding inputs for style preferences and body type with skippable measurements; wardrobe upload/review; per-request occasion + vibe + wardrobe-only toggle; outfit results with explanations tied to the selected inputs and wardrobe items; gaps/shop; Style DNA; saved looks; and privacy settings. Add links from the existing AI/shop surfaces into the styling journey. Keep the current chatbot as a separate conversational entry point; if it consumes styling context, send only the minimum user-approved, non-sensitive summary and validate every returned product UUID against the catalog.

**Done when:** a new user can complete the journey from account setup to generated outfit and catalog gap suggestion; empty/error states route to the relevant setup screen; the chatbot cannot create product links to nonexistent products or bypass styling rules.

### Phase 8 — Hardening and release readiness

**Work:** add focused tests for RLS/ownership, schema migrations, outfit constraints, budget filtering, fallback behavior, and feedback ordering. Add idempotent demo data and document exactly which recommendations are rules-based, LLM-assisted, or manually tagged. Update the README and API/UI contract after route shapes settle. Review account deletion/export and storage cleanup for all new user-owned records.

**Done when:** a clean environment can be initialized from documented migrations/seeds; no secrets are needed for the rules-based demo; private data and media are removed with the owning account; demo claims match the shipped implementation.

## Data model proposal

Add these tables with `user_id` ownership, indexes for common filters, and RLS policies that enforce ownership:

| Table | Purpose | Important fields |
| --- | --- | --- |
| `style_profiles` | Durable preferences | `user_id`, `style_tags`, `favorite_colors`, `budget_cents`, `preferred_occasions` |
| `body_profiles` | Optional fit inputs | `user_id`, minimal measurements/shape guidance, updated timestamp; sensitive access only |
| `user_consents` | Versioned, revocable consent | `user_id`, purpose, policy version, granted/revoked timestamps |
| `wardrobe_items` | Clothing owned by user | `user_id`, private `image_path`, category/subtype, tags, confidence/source, timestamps |
| `outfits` | Generated/saved look | `user_id`, occasion, score, explanation, saved state, generation metadata |
| `outfit_items` | Outfit composition | `outfit_id`, exactly one of `wardrobe_item_id` or `product_id`, slot, rank |
| `outfit_events` | Feedback/learning events | `user_id`, `outfit_id`, event type, timestamp |

Use database constraints for mutually exclusive wardrobe/product references and cascading cleanup only where ownership is unambiguous. Keep product styling attributes on `products` initially; split a separate catalog-style table only if the existing schema or query needs justify it.

## Key API surface to add

Follow existing Next.js route conventions and use Supabase's authenticated server client for user data. Proposed route families:

- `/api/style-profile` — read/update preferences and consent state.
- `/api/wardrobe` and `/api/wardrobe/[id]` — list/create/update/delete wardrobe items; upload flow uses private Storage.
- `/api/outfits/generate` — occasion, vibe, budget/profile options, and `useOnlyWardrobe` / `allowOneNewItem` controls.
- `/api/outfits/[id]/events` and `/api/outfits/saved` — feedback and saved looks.
- `/api/gaps` and `/api/suggestions` — missing slots and matched catalog products.
- `/api/style-dna` — derived, user-owned affinity summary.

Keep response IDs as UUIDs. Validate request bodies with Zod, cap upload size/type and generation candidate counts, return structured errors such as `wardrobe_empty`, `body_profile_missing`, `no_products_in_budget`, and `fallback_used`, and never trust client-supplied prices or ownership IDs.

## Scope boundaries and choices

Build the reliable core first: manual tagging, deterministic outfit rules, a local Supabase catalog, and explicit feedback. Defer live retailer APIs, trend intelligence, video scanning, visual similarity search, automatic body estimation, heavy image models, and complex model registries. The StyleSense guide's “demo catalog” becomes FlashFit's existing catalog; retailer search links are unnecessary unless FlashFit later adds a licensed outbound shopping provider.

The guide proposes a specific women-focused taxonomy and demo flow. Treat those as product defaults because they are in the requested StyleSenseAI direction, but keep taxonomy and occasion rules configurable so FlashFit can broaden its audience later without rewriting the engine.

## Recommended first implementation slice

Start with Phase 0 and Phase 1, then deliver one complete vertical path: authenticated user → add a few manually tagged wardrobe items → generate and save wardrobe-only outfits for one occasion. This validates ownership, schema, and the styling engine before introducing private photo processing, body data, feedback ranking, or mixed shopping fallback. Add the phases above in order, with the acceptance criteria as review checkpoints.
