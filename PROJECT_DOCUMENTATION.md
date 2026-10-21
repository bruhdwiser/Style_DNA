# StyleSense AI (formerly Flashfits) - Architecture & System Documentation

**Project:** StyleSense AI (formerly Flashfits AI)  
**Brand Identity:** *StyleSense — Public Dressing Room* ("Get dressed. Go somewhere.")  
**Frontend Architecture:** React 19 + Vite Single-Page Application (`frontend/`)  
**Backend Architecture:** FastAPI (Python 3.10+) Microservice (`backend/`)  
**Styling Engine:** Ported Pure Python StyleSenseAI Engine (`backend/app/styling/`)  
**Data, Auth & Storage:** Supabase (PostgreSQL, GoTrue, S3-Compatible Private Storage)  
**AI Assistant Provider:** OpenRouter API (Server-side optional enhancement layer)  
**Status:** Completed migration from legacy root Next.js full-stack app to decoupled React + Vite and FastAPI architecture with full editorial design system and test suite (October 2026).

---

## 1. Verified vs. Planned/Pending Behavior

To maintain engineering integrity, this documentation distinguishes between behaviors verified directly within this codebase and planned/pending behaviors:

### A. Verified Behavior in Current Codebase
- **Deterministic Pure Python Styling Engine**: Full port of StyleSenseAI rules in `backend/app/styling/` (skeletons, color harmonies, formality constraints, seasonal logic, archetype scoring, and counterfactual gap unlocks).
- **Comprehensive Backend Test Suite**: 43 passing unit and integration tests in `backend/tests/` covering body guidance, gap analysis, outfit generator ranking, occasion rules, skeletons, style DNA learning, wardrobe image processing, catalog completion, persistence rollback, and saved outfit tags.
- **Garment Identity & Core Signatures**: Garment identity is strictly extracted via dictionary `["id"]` and object `.id` (never Python memory identity). Core slot signatures `(slot, garment_id)` prevent redundant core repetitions before distinct valid alternatives are exhausted.
- **Deterministic Recommendation & Shuffle Mode**: Normal generation requests produce deterministic results. Shuffle mode explicitly requests alternative pairings by excluding previous-screen core signatures.
- **Catalog Completion & Shortfall Recovery**: Enabled by default with a strict opt-out ("Use only my rack"). High-quality wardrobe looks are evaluated first; any shortfall against requested count is filled using eligible single catalog products matching occasion, season, vibe, audience, budget, formality, and anti-clash rules. If catalog items cannot fill the shortfall, valid below-threshold wardrobe alternatives are included with explicit per-look and summary warnings.
- **Saved Looks & Canonical Tag Model**: Forward-only migration adding `tags text[]` with GIN indexing (`idx_outfits_user_saved_tags`). Outfits can be saved for later with user-selected canonical tags (`Work`, `Date Night`, `Wedding`, `Vacation`, `Try Later`, defaulting to `Try Later`). Idempotent Style DNA logging ensures repeat saves or tag updates do not inflate scores.
- **Interaction Semantics**: Explicit meanings for Keep/Like (`event_type: "like"`), Wore It (`event_type: "wear"`), Not For Me (`event_type: "dislike"`, which resets `is_saved: False` and clears tags while preserving audit history), and Save for Later (`event_type: "save"` with tags).
- **Error Visibility & Rollback**: Persistence failures raise visible errors and banner alerts; success is never reported on failure, and optimistic UI changes roll back cleanly.
- **Silhouette Diversity & Jitter**: Maximal Marginal Relevance (MMR) ranking in `generator.py` incorporating silhouette similarity penalties, exact silhouette counting, and stochastic jitter for distinct recommendations.
- **Shoe-Optional Skeletons**: Flexible skeleton combinations allowing valid 1-piece and 2-piece outfit generation when the user has not yet uploaded shoes.
- **Occasion Clustering & Anti-Clash Rules**: Strict occasion taxonomy mapping (`item_occasion_match`) and clash prevention rules (`no_sneakers_with_ethnic_formal`, `no_formal_shoes_for_lounge`).
- **Owner-Scoped Data Models & Migrations**: 8 forward-only SQL migrations in `scripts/migrations/` covering product styling attributes, style profiles, neutral body guidance, user consents, digital wardrobe, outfits, outfit items, outfit events, cart variants, and outfit tags.
- **FastAPI Endpoints**: Full CRUD, validation, and serialization contracts implemented using Pydantic v2 schemas across 12 router modules.
- **Batch Storage URL Signing**: `_batch_build_signed_view_urls` in `wardrobe.py` batch-signs image and thumbnail download URLs in a single roundtrip, preventing sequential blocking and client-side 404s.
- **Semantic Deterministic AI Chat Fallback**: Robust fallback in `ai_chat.py` utilizing fashion stopwords, concept expansion dictionaries, and balanced slot selection when external AI APIs are absent or offline.
- **React + Vite Frontend**: Complete 14-route styling journey built with modern React 19, TypeScript, React Router v7, and Vanilla CSS adhering to the "Public Dressing Room" design system. Verified with 100% clean production build (`npm run build` in `frontend/` produces clean bundles with 0 errors).
- **Grounded Catalog Links**: Product UUIDs are strictly validated against catalog records, preventing hallucinated product recommendations.
- **Privacy & Safety Constraints**: Zero body measurements or body types are sent to OpenRouter or external AI providers. Garment photos sent to OpenRouter require explicit user consent and are stripped of EXIF metadata and resized using Pillow.
- **GDPR Export & Account Purge**: Dedicated endpoints (`GET /api/v1/me/export`, `DELETE /api/v1/me/account`) for data portability and complete user deletion across database tables and private storage objects.

### B. Planned / Pending Behavior (Requires Remote Infrastructure)
- **Live Multi-User Remote Verification**: Multi-tenant separation has been implemented via Postgres RLS policies and caller-scoped clients; physical multi-user testing against a live remote Supabase production project is pending final cloud deployment.
- **Third-Party Payment Gateway Integration**: Cart and checkout preview are fully functional; live payment processing (e.g. Razorpay/Stripe webhook verification) is planned for future e-commerce phases.
- **Legacy Next.js Removal**: Legacy Next.js files remain intact at the repository root to prevent service disruption until user review and formal cutover approval.

---

## 2. Architecture Overview

```text
┌────────────────────────────────────────────────────────┐
│             React + Vite Frontend (Port 5173)         │
│  - React 19 + TypeScript + Vanilla CSS                │
│  - React Router DOM v7 (Client-Side SPA Routing)      │
│  - Browser Supabase Client (Auth Session & Direct S3) │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ HTTP / JSON (Bearer JWT)
                            ▼
┌────────────────────────────────────────────────────────┐
│              FastAPI Backend (Port 8000)               │
│  - Python 3.10+ / Pydantic v2 / Pillow Image Processor │
│  - Bearer Token Cryptographic Verification             │
│  - Caller-Scoped Supabase Client Pool (Enforcing RLS) │
│  - Server-Side Admin Authorization (Allowlist Enforced)│
│  - Core Routers: Cart, Wardrobe, Outfits, Gaps, DNA    │
└─────────────┬───────────────────────────┬──────────────┘
              │                           │
              │ SQL / Storage (RLS)       │ Optional Phrasing & Vision
              ▼                           ▼
┌───────────────────────────┐   ┌──────────────────────────┐
│      Supabase Cloud       │   │      OpenRouter AI       │
│  - PostgreSQL DB with RLS │   │  - Garment Tag Suggest.  │
│  - GoTrue Auth            │   │  - Explanation Phrasing  │
│  - Private S3 Bucket      │   │  - NO Body Data Allowed  │
└───────────────────────────┘   └──────────────────────────┘
```

---

## 3. Directory Layout

```text
Flashfits-AI/
├── backend/                         # FastAPI Python Backend
│   ├── .venv/                      # Python virtual environment
│   ├── app/
│   │   ├── core/                   # Security, settings, Supabase client pool
│   │   │   ├── config.py           # Pydantic BaseSettings (tokens, admin, CORS)
│   │   │   ├── exceptions.py       # Standardized API error envelopes
│   │   │   ├── image_processing.py # Pillow sanitization & EXIF stripping
│   │   │   ├── security.py         # Bearer token verification & admin guards
│   │   │   └── supabase.py         # Supabase client pool (anon, caller, admin)
│   │   ├── routers/                # REST API routers (/api/v1/*)
│   │   │   ├── admin.py            # Admin health and stats
│   │   │   ├── ai_chat.py          # Grounded stylist chat + deterministic fallback
│   │   │   ├── analytics.py        # Telemetry tracking & admin analytics
│   │   │   ├── auth.py             # User profile, export & account deletion
│   │   │   ├── cart.py             # RLS-enforced shopping cart CRUD
│   │   │   ├── gaps.py             # Wardrobe gap analysis & catalog suggestions
│   │   │   ├── health.py           # Health check endpoints
│   │   │   ├── outfits.py          # Pure engine outfit generation & saved looks
│   │   │   ├── products.py         # Catalog listing, detail & admin inventory
│   │   │   ├── style_dna.py        # Style DNA affinities & affinity reset
│   │   │   ├── style_profile.py    # Style preferences, body guidance & consents
│   │   │   └── wardrobe.py         # Closet uploads, batch signed URLs, tags
│   │   ├── schemas/                # Pydantic request/response data contracts
│   │   ├── styling/                # Ported pure Python StyleSenseAI engine
│   │   │   ├── body_fit.py         # Neutral body fit rules
│   │   │   ├── color.py            # Color harmonies & palettes
│   │   │   ├── explain.py          # Structured factual explanation generator
│   │   │   ├── features.py         # Feature extraction & attribute mapping
│   │   │   ├── gaps.py             # Counterfactual gap unlocking engine
│   │   │   ├── generator.py        # Combinatorial skeleton outfit generator
│   │   │   ├── learning.py         # Bounded Style DNA affinity tracking
│   │   │   ├── rules.py            # Formality, seasonal & occasion matching
│   │   │   ├── skeletons.py        # Slot templates (Western, Ethnic, Fusion)
│   │   │   ├── taxonomy.py         # Canonical categories, fits & occasions
│   │   │   └── variations.py       # Minor outfit variation generator
│   │   └── main.py                 # FastAPI application factory & CORS setup
│   ├── tests/                      # 43 Passing Pytest Test Cases
│   │   ├── conftest.py             # Test fixtures & Supabase client mocks
│   │   ├── test_body_guidance.py   # Neutral body guidance tests
│   │   ├── test_gap_analysis.py    # Wardrobe gap analysis tests
│   │   ├── test_outfit_generator.py# Outfit generation & MMR ranking tests
│   │   ├── test_outfit_rules.py    # Occasion, seasonal & formality rules
│   │   ├── test_outfit_skeletons.py# Skeletons & shoe-optional tests
│   │   ├── test_outfits_router.py  # Router endpoints, catalog completion, persistence rollback & saved tags
│   │   ├── test_style_dna.py       # Affinity learning & reset tests
│   │   └── test_wardrobe_service.py# Image processing & batch URL signing tests
│   ├── requirements.txt            # Python dependencies
│   ├── pyproject.toml              # Python project metadata
│   └── .env.example                # Backend environment template
│
├── frontend/                        # React + Vite Frontend
│   ├── src/
│   │   ├── components/             # Reusable UI & AdminGuard
│   │   │   ├── ui/                 # Button, Card, Input, Badge, Separator
│   │   │   ├── AdminGuard.tsx      # Client-side UI guard for admin routes
│   │   │   ├── navigation.tsx      # Editorial masthead (STYLESENSE / ISSUE 01)
│   │   │   ├── footer.tsx          # Colophon footer
│   │   │   └── product-card.tsx    # Editorial product card component
│   │   ├── contexts/               # Auth & Cart React contexts
│   │   ├── lib/                    # Typed API client & Supabase browser wrapper
│   │   ├── pages/                  # React Router page views (14 routes)
│   │   │   ├── AboutPage.tsx       # Platform story & architecture
│   │   │   ├── AdminAnalyticsPage.tsx # Real-time telemetry analytics dashboard
│   │   │   ├── AdminPage.tsx       # Product inventory CRUD management
│   │   │   ├── AiStylistPage.tsx   # Dedicated AI styling studio (/ai)
│   │   │   ├── AuthCallbackPage.tsx# GoTrue OAuth redirect exchange handler
│   │   │   ├── CartPage.tsx        # Shopping bag & checkout preview
│   │   │   ├── HomePage.tsx        # Editorial cover, categories, featured picks
│   │   │   ├── LoginPage.tsx       # Supabase email/password & OAuth sign-in
│   │   │   ├── OutfitsPage.tsx     # Occasion generator, feedback & gap analysis
│   │   │   ├── SettingsPage.tsx    # Privacy, consents, GDPR export & account purge
│   │   │   ├── ShopPage.tsx        # Catalog search, filter, and pagination
│   │   │   ├── ShopProductDetailPage.tsx # Modern product detail view (/shop/:id)
│   │   │   ├── StyleDnaPage.tsx    # Style DNA affinities & affinity reset
│   │   │   ├── StyleOnboardingPage.tsx # Style profile wizard & editor
│   │   │   └── WardrobePage.tsx    # Digital closet, uploads, AI tags & coverage
│   │   ├── App.tsx                 # Route declarations & route guards
│   │   ├── main.tsx                # Application bootstrap with Context Providers
│   │   └── index.css               # Editorial design tokens, reset & components
│   ├── DESIGN_SYSTEM.md            # "Public Dressing Room" Design Specification
│   ├── package.json                # Frontend dependencies
│   ├── tsconfig.app.json           # TypeScript configuration with @/* path alias
│   ├── vite.config.ts              # Vite server, Tailwind v4 plugin & /api/v1 proxy
│   └── .env.example                # Browser-safe environment template
│
├── scripts/                         # Database schema & SQL migrations
│   ├── schema.sql                  # Base database schema
│   ├── seed-styling-products.sql   # Idempotent seed data for styling catalog
│   ├── make-admin.sql              # Admin promotion SQL script
│   ├── make-tanishq-admin.sql      # Tanishq admin promotion SQL script
│   ├── debug-admin-setup.sql       # Admin verification SQL script
│   └── migrations/                 # Forward-only database migrations
│       ├── 2026-10-21_save_outfit_rpc.sql # Atomic save_outfit_with_items function
│       └── 2026-10-21_add_outfit_tags.sql # Tags array and GIN index on public.outfits
│
├── PROJECT_DOCUMENTATION.md        # Comprehensive system documentation
├── README.md                       # Quickstart & setup guide
└── CLAUDE.md                       # Claude & LLM developer context guide
```

---

## 4. Database Schema & Migration History

All database migrations are strictly forward-only and additive, preserving existing product UUIDs, pricing conventions, and cart items:

| Sequence | Migration File | Target Tables / Operations | Purpose |
|---|---|---|---|
| 1 | `scripts/schema.sql` | `products`, `cart_items`, `analytics_events`, `admin_users` | Base commerce tables with UUID primary keys and basic RLS. |
| 2 | `scripts/migrations/2026-10-12_add-cart-item-variants.sql` | `cart_items` | Adds `selected_color` and `selected_size` to cart records. |
| 3 | `scripts/migrations/2026-10-12_add-product-styling-attributes.sql` | `products` | Extends catalog with styling attributes: `audience`, `slot`, `subtype`, `color_tags`, `formality`, `style_tags`, `occasions`, `seasons`, `fit`, `pattern`, `seed_key`. |
| 4 | `scripts/migrations/2026-10-12_add-style-profiles-and-consents.sql` | `style_profiles`, `body_profiles`, `user_consents` | Stores user style preferences, neutral derived body guidance, and explicit revocable privacy consents with owner-scoped RLS. |
| 5 | `scripts/migrations/2026-10-12_add-wardrobe-items-and-storage.sql` | `wardrobe_items`, Storage bucket `wardrobe` | Owner-scoped digital closet items, slot coverage, and private Supabase Storage bucket policies. |
| 6 | `scripts/migrations/2026-10-12_add-outfits-and-saved-looks.sql` | `outfits`, `outfit_items` | Persists generated outfits, item references, component scores, and saved looks with cross-table RLS validation. |
| 7 | `scripts/migrations/2026-10-12_add-outfit-events-and-style-dna.sql` | `outfit_events` | Stores authenticated user feedback events (`like`, `dislike`, `save`, `wear`, `skip`) for transparent Style DNA affinity learning. |
| 8 | `scripts/seed-styling-products.sql` | `products` | Idempotent seed script inserting women and unisex garments with rich styling taxonomy tags. |
| 9 | `scripts/migrations/2026-10-21_save_outfit_rpc.sql` | `save_outfit_with_items` function | Atomic RPC persisting an outfit and its items in a single ACID transaction under security invoker RLS. |
| 10 | `scripts/migrations/2026-10-21_add_outfit_tags.sql` | `outfits` | Adds `tags text[] NOT NULL DEFAULT '{}'` and GIN index `idx_outfits_user_saved_tags` for fast saved look tag queries. |

### Row-Level Security (RLS) Policies
- **User Ownership**: All user tables enforce `user_id = auth.uid()` for `SELECT`, `INSERT`, `UPDATE`, and `DELETE`.
- **Cross-Table Validation**: `outfit_items` triggers/policies ensure an outfit item can only reference wardrobe items owned by the outfit's creator.
- **Admin Privilege**: Product creation, inventory updates, and analytics reading require verification against the server-enforced `ADMIN_EMAILS` list or `public.admin_users` table.

---

## 5. API Surface & Endpoints

All backend endpoints are prefixed with `/api/v1` and organized into modular FastAPI routers:

### Products & Catalog
- `GET /api/v1/products`: List and filter catalog products with pagination, category, price range, and search.
- `GET /api/v1/products/{id}`: Retrieve detailed product attributes by UUID.
- `POST /api/v1/admin/products`: (Admin only) Create a new catalog item.
- `PATCH /api/v1/admin/products/{id}`: (Admin only) Update product details or stock.
- `DELETE /api/v1/admin/products/{id}`: (Admin only) Delete a product from inventory.

### Shopping Cart
- `GET /api/v1/cart`: Retrieve current authenticated user's cart items with total item count and price.
- `POST /api/v1/cart/items`: Add a product to the cart with optional size and color variants.
- `PATCH /api/v1/cart/items/{id}`: Update quantity or variants for a cart item.
- `DELETE /api/v1/cart/items/{id}`: Remove an item from the cart.

### Style Profile & Consents
- `GET /api/v1/style-profile`: Retrieve user style preferences, onboarding state, and derived body guidance.
- `PUT /api/v1/style-profile`: Save or update style preferences, preferred occasions, and budget.
- `POST /api/v1/style-profile/body-guidance`: Compute and store neutral derived body guidance in memory with explicit consent.
- `DELETE /api/v1/style-profile/body-guidance`: Permanently delete derived body guidance.
- `POST /api/v1/style-profile/consents`: Grant or revoke specific privacy consents (`body_guidance_storage`, `wardrobe_photo_analysis`).

### Digital Wardrobe
- `GET /api/v1/wardrobe`: List owned wardrobe items with optional category filtering and review status. Automatically resolves temporary signed view URLs using high-performance batch signing (`_batch_build_signed_view_urls`) to prevent sequential blocking.
- `GET /api/v1/wardrobe/coverage`: Summary of wardrobe coverage across slots (`tops`, `bottoms`, `layers`, `shoes`, `sarees`).
- `POST /api/v1/wardrobe/uploads`: Request a signed upload URL to private Supabase Storage.
- `POST /api/v1/wardrobe/suggest-tags`: AI photo tag suggestion with consent check, Pillow image sanitize, and taxonomy validation.
- `PATCH /api/v1/wardrobe/{id}`: Update tags, availability, or review status for a wardrobe item.
- `DELETE /api/v1/wardrobe/{id}`: Delete a wardrobe item and its corresponding storage objects.

### Outfits & Feedback
- `POST /api/v1/outfits/generate`:
  - **Purpose**: Generates occasion-specific outfits using the pure Python styling engine with deterministic normal generation, shuffle alternative mode, and automatic catalog completion.
  - **Request Body (`GenerateOutfitsRequest`)**:
    - `occasion` (str, required): e.g., `"Work"`, `"Casual"`, `"Party"`, `"Formal"`, `"Date Night"`.
    - `season` (str, default `"all"`): Target season for seasonal compatibility rules.
    - `vibe` (str | None): Optional style vibe modifier.
    - `limit` (int, default 6, 1–20): Number of outfit recommendations requested.
    - `wardrobe_only` (bool, default `False`): Strict opt-out switch ("Use only my rack"). When `True`, store items are strictly prohibited.
    - `budget_max` (float | None): Maximum price in dollars/currency units for catalog items.
    - `allow_one_new_item` (bool, default `True`): Deprecated/legacy compatibility switch. Subservient to `wardrobe_only`.
    - `min_quality_threshold` (float, default 0.65): Score threshold separating high-quality looks from fallback looks.
    - `seed` (int, default 0): Integer seed (overridden by server content fingerprint on normal requests).
    - `shuffle` (bool, default `False`): When `True`, activates alternative shuffle mode with rotated seed and core exclusion.
    - `shuffle_index` (int, default 0): Monotonically increasing shuffle turn counter.
    - `exclude_core_keys` (list[list[str]], default `[]`): Array of previous-screen core `(slot, item_id)` pairs to exclude.
  - **Response (`GenerateOutfitsResponse`)**:
    - `outfits` (list[OutfitResponse]): Persisted outfits with slot items, component scores, reasons, and tags.
    - `status` (str): `"success"`, `"partial_results"`, `"no_matching_combinations"`, `"missing_required_slots"`, `"empty_wardrobe"`.
    - `quality_warning_outfit_ids` (list[str]): IDs of below-threshold valid wardrobe looks included as shortfall fallback.
    - `no_products_in_budget` (bool): True if catalog pieces exist for the slot but exceed `budget_max`.
    - `cheapest_alternative` (dict | None): Cheapest catalog item that would complete the outfit if budget is exceeded.
    - `message` (str | None): Human-readable explanation of recommendations, shortfalls, and quality warnings.

- `GET /api/v1/outfits/saved`:
  - **Purpose**: Retrieve saved outfits for the authenticated user with populated slot items, tags, and aggregated filter metadata.
  - **Query Parameters**:
    - `tag` (str | None): Optional filter by canonical tag (`"Work"`, `"Date Night"`, `"Wedding"`, `"Vacation"`, `"Try Later"`). Employs PostgreSQL array containment (`outfits.tags @> ARRAY[tag]`).
  - **Response (`SavedOutfitsListResponse`)**:
    - `outfits` (list[OutfitResponse]): List of outfits with `is_saved == True`, matching tag (if specified).
    - `total` (int): Total count of saved outfits matching the query.
    - `available_tags` (list[str]): Distinct canonical tags across all saved outfits owned by this user (e.g. `["Work", "Try Later"]`), for rendering dynamic filter chips in the UI.

- `POST /api/v1/outfits/{id}/save`:
  - **Purpose**: Save an outfit for later with user-selected canonical tags and record idempotent Style DNA feedback.
  - **Request Body (`SaveOutfitRequest`)**:
    - `tags` (list[str], default `["Try Later"]`): Classification tags selected by user, normalized against `APPROVED_OUTFIT_TAGS`.
  - **Response (`SaveOutfitResponse`)**:
    - `id` (str): Outfit UUID.
    - `is_saved` (bool): `True`.
    - `tags` (list[str]): Normalized saved tags array.
    - `message` (str): Confirmation message.
  - **Behavioral Guarantees**:
    - **Fail-Closed Consistency**: Marking an outfit as saved and recording its save interaction in `outfit_events` are strictly consistent. On initial save, the event is recorded first; if writing the event fails, the operation fails cleanly with HTTP 500 (`SAVE_EVENT_ERROR`) and `is_saved` remains `False`.
    - **Idempotency**: If the outfit was already saved or had its save event recorded, repeat saves update tags without inserting duplicate `outfit_events` rows.
    - **Mixed Look Metadata Coverage**: Item extraction queries both `wardrobe_items` and `products` from `outfit_items`, incorporating catalog attributes (`color_tags`, `colors`, `style_tags`, `category`, `subtype`) without fabricating wardrobe-specific attributes.

- `PUT /api/v1/outfits/{id}/tags`:
  - **Purpose**: Update classification tags on an already-saved outfit under caller RLS ownership without affecting Style DNA score weights.
  - **Request Body (`UpdateOutfitTagsRequest`)**:
    - `tags` (list[str], required): Updated tag array, normalized against `APPROVED_OUTFIT_TAGS` (defaults to `["Try Later"]` if empty).
  - **Response (`SaveOutfitResponse`)**:
    - Returns updated outfit ID, `is_saved: True`, and normalized tags.

- `DELETE /api/v1/outfits/{id}/save`:
  - **Purpose**: Unsave an outfit for the caller.
  - **Behavior**: Sets `is_saved = False` and resets `tags = '{}'` on `public.outfits`. Does not delete the audit event history in `outfit_events`.

- `POST /api/v1/outfits/{id}/events`:
  - **Purpose**: Record an authenticated interaction feedback event for explainable Style DNA learning.
  - **Request Body (`OutfitEventCreate`)**:
    - `event_type` (str, required): `"like"`, `"dislike"`, `"save"`, `"wear"`, `"skip"`.
  - **Feedback Semantics & Side Effects**:
    - `"like"`: Positive preference signal (+0.6 Style DNA).
    - `"wear"`: Real-life validation signal (+1.0 Style DNA).
    - `"dislike"` ("Not For Me"): Negative preference signal (-0.8 Style DNA). **Side effect**: Atomically sets `is_saved = False` and resets `tags = '{}'` on `public.outfits`, removing it from the user's saved list while preserving the event record for Style DNA learning.
    - `"skip"`: Neutral/dismissive signal (-0.2 Style DNA).
    - `"save"`: Saved for later (+2.0 Style DNA). Handled primarily via `POST /outfits/{id}/save`.

### Gaps & Style DNA
- `GET /api/v1/gaps`: Perform counterfactual wardrobe analysis identifying missing slots that unlock outfits, with catalog suggestions.
- `GET /api/v1/style-dna`: Retrieve normalized positive and negative tag affinities and total event count.
- `POST /api/v1/style-dna/reset`: Reset all learned Style DNA affinities to baseline.

### Conversational Stylist & Grounded Chat
- `POST /api/v1/ai/chat`: Interactive fashion stylist conversation. Features multi-model fallback chain, reasoning payload control (`effort: none` for Nemotron models), strict catalog grounding, and robust deterministic fallback using semantic fashion concept matching when AI keys are omitted.

### User Account & Privacy
- `GET /api/v1/me/export` (and `/api/v1/auth/export`): GDPR data export bundle including profile, wardrobe, outfits, and events.
- `DELETE /api/v1/me/account` (and `/api/v1/auth/account`): Complete account deletion cascading across all database tables and private storage.

---

## 6. Frontend Routing Matrix

| Route | Page Component | Protected? | Capabilities |
|---|---|---|---|
| `/` | `HomePage` | No | Storefront hero, value props, categories, featured picks. |
| `/shop` | `ShopPage` | No | Search, filter by category/price/stock, and sort. |
| `/shop/:id` | `ShopProductDetailPage` | No | Modern product detail, size selector, add-to-cart. |
| `/product/:id` | `ShopProductDetailPage` | No | Classic product detail route alias to modern view. |
| `/cart` | `CartPage` | Yes | View cart, adjust quantities, remove items, checkout preview. |
| `/login` | `LoginPage` | No | Email/password sign-in/up and Google OAuth button. |
| `/auth/callback` | `AuthCallbackPage` | No | GoTrue OAuth hash token listener & redirect handler. |
| `/style-onboarding` | `StyleOnboardingPage` | Yes | Style profile wizard; edits profile when `?edit=true`. |
| `/wardrobe` | `WardrobePage` | Yes | Closet items, slot coverage, direct uploads, AI tag modal. |
| `/outfits` | `OutfitsPage` | Yes | Studio generator with 'Use only my rack' toggle, deterministic normal generation, shuffle mode, catalog completion cards with price/slot reason, below-threshold quality warnings, Saved Looks with canonical tag modal (`Work`, `Date Night`, `Wedding`, `Vacation`, `Try Later`), tag filter chip bar, inline tag editing, feedback bar (Wore It, Keep, Not For Me, Skip), and Gaps analysis tab. |
| `/style-dna` | `StyleDnaPage` | Yes | Normalized tag affinities & affinity reset action. |
| `/settings` | `SettingsPage` | Yes | Privacy consents, body guidance deletion, GDPR export, account purge. |
| `/profile` | `SettingsPage` | Yes | Route alias to `/settings`. |
| `/ai` | `AiStylistPage` | No | Dedicated AI styling studio conversation with catalog links. |
| `/admin` | `AdminPage` | Admin | Product management & inventory CRUD (`AdminGuard`). |
| `/admin/add-product` | `AdminPage` | Admin | Create product form (`AdminGuard`). |
| `/admin/analytics` | `AdminAnalyticsPage` | Admin | Real-time views, sales, and conversion stats (`AdminGuard`). |
| `/about` | `AboutPage` | No | Platform story, mission, and styling philosophy. |

---

## 7. "Public Dressing Room" Editorial Design System

Documented in `frontend/DESIGN_SYSTEM.md`, the platform embraces a fashion desk / backstage fitting room aesthetic:

### Design Tokens (`frontend/src/index.css`)
- Canvas: `--paper` (`#F4F0E8`), `--paper-strong` (`#E7E1D5`)
- Typography & Ink: `--ink` (`#181716`), `--ink-soft` (`#5E5A54`)
- Structural Rules: `--line` (`#C9C2B6`)
- Signals & Actions: `--acid` (`#DFFF00` for active states/filters), `--cobalt` (`#234BFF` for links/info), `--signal` (`#E33B1E` for destructive)

### Non-Negotiables
1. **Zero Gradients & No Floating Blobs**: Clean, tactile broadsheet layouts.
2. **0px Border Radius**: Square corners throughout (2px on inputs only).
3. **Typography**: System fonts only (Baskerville/Georgia serif display, Helvetica/Arial interface sans, Consolas/SF Mono uppercase metadata). Zero remote font dependencies.
4. **Editorial Masthead & Colophon**: `STYLESENSE / ISSUE 01` top bar with mobile index drawer; newspaper colophon footer.
5. **No AI Gimmicks**: Avoid sparkles, magic wands, or "AI Powered" badges; phrase actions as "suggestions", "matches", or "Why this works".

---

## 8. Security, Privacy & AI Boundary Guarantees

1. **Cryptographic JWT Verification**:
   - The FastAPI backend validates all incoming Bearer tokens using Supabase Auth endpoints or local HMAC secret verification (`SUPABASE_JWT_SECRET`).
   - Requests without valid authorization return `401 Unauthorized`.
2. **Caller-Scoped Supabase Client**:
   - For all user-facing data operations, FastAPI creates a Supabase client configured with the verified caller's Bearer token.
   - Postgres Row-Level Security automatically scopes operations to `auth.uid() = user_id`.
3. **Zero Body Data Leakage**:
   - Under no circumstances are body measurements, body shapes, or self-selected body types sent to OpenRouter or external AI providers.
   - Measurement calculations for derived shape guidance occur entirely in ephemeral server memory and raw measurements are discarded immediately.
4. **Specific Consent for Photos**:
   - Before any garment photo is processed by OpenRouter vision for tag suggestions, explicit user consent is verified via the `user_consents` table (`wardrobe_photo_analysis`) or an in-modal consent confirmation dialog.
   - Uploaded photos are sanitized with Pillow (EXIF metadata stripped, resized) before transmission.
5. **Taxonomy & Grounding Validation**:
   - All AI-suggested tags are validated against `backend/app/styling/taxonomy.py`. Hallucinations are discarded.
   - The user must explicitly review and confirm tags before the item is saved.
   - Any product UUID suggested by AI chat or fallback rules is checked against `public.products`, stripping hallucinated links.

---

## 9. Honest AI & Rules Claims

- **Outfit Generation is Deterministic**:
  The outfit generator is **not** a generative AI black box or trained neural network. It is a deterministic rule engine that uses combinatorial slot skeletons, colour wheel harmonies (complementary, analogous, triadic, monochrome), formality scores, occasion dress codes, and fit guidelines.
- **Style DNA is Explainable Heuristic Learning**:
  Style DNA does not claim to use deep visual representation learning. It applies bounded mathematical adjustments (+1.0 for wear, +0.6 for save/like, -0.8 for dislike, -0.2 for skip) to color, style, and category affinity scores. Outfit validity rules and occasion constraints always dominate affinity scores.
- **OpenRouter is Strictly Optional**:
  The platform works completely offline from AI APIs. If `OPENROUTER_API_KEY` is not present, outfit explanations use factual rule-based templates, and photo tag suggestions fall back to deterministic taxonomy defaults.

---

## 10. Environment Variable Names & Local Setup

### A. Environment Variable Inventory (Names Only)

#### Backend (`backend/.env`):
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `ADMIN_EMAILS`
- `ADMIN_USER_IDS`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `CORS_ORIGINS`
- `ENVIRONMENT`

#### Frontend (`frontend/.env.local`):
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_BASE_URL`

### B. Setup & Verification Commands

```bash
# 1. Backend Verification & Running (43 tests)
# From workspace root:
.\backend\.venv\Scripts\python.exe -m pytest backend/tests

# Run outfit generation & saved looks router test suite specifically (13 tests):
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_outfits_router.py

# Run FastAPI dev server:
.\backend\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000 --app-dir backend

# 2. Frontend Verification & Running
cd frontend
npm install
npm run dev

# Production build check & linter:
npm run build
npx oxlint
```

---

## 11. Legacy Next.js Deprecation & Proposed Cleanup List

The legacy Next.js app remains at the workspace root to ensure business continuity during migration review. The following files and dependencies are legacy-only and proposed for removal upon formal cutover:

### Proposed Files for Deletion:
```text
# Next.js App Router Pages & APIs
app/Scene3D.tsx
app/about/page.tsx
app/admin/add-product/page.tsx
app/admin/analytics/page.tsx
app/admin/page.tsx
app/ai/page.tsx
app/api/admin/products/route.ts
app/api/admin/stats/route.ts
app/api/chat/route.ts
app/api/products/[id]/route.ts
app/api/products/route.ts
app/auth/callback/route.ts
app/cart/page.tsx
app/globals.css
app/layout.tsx
app/login/page.tsx
app/page.tsx
app/product/[id]/page.tsx
app/shop/[id]/page.tsx
app/shop/page.tsx

# Legacy Next.js Components & Contexts
components/ai-chatbot.tsx
components/cookie-consent-banner.tsx
components/cookie-settings-dialog.tsx
components/footer.tsx
components/navigation.tsx
components/product-card.tsx
components/theme-provider.tsx
components/ui/                         # (All Radix-based UI wrappers)
contexts/cart-context.tsx
contexts/cookie-consent-context.tsx
contexts/theme-context.tsx

# Legacy Next.js Libraries & Helpers
lib/api/
lib/hooks/
lib/supabase/
lib/tracking.ts
lib/utils.ts
styles/globals.css

# Legacy Next.js Configuration & Build Files
next.config.mjs
next-env.d.ts
postcss.config.mjs
tailwind.config.js
components.json
tsconfig.json                          # (Root tsconfig)
.next/                                 # (Build cache)
```

### Proposed Unused Dependencies in Root `package.json`:
- `next`
- `@supabase/auth-helpers-nextjs`
- `@supabase/ssr`
- `next-themes`
- `@radix-ui/*` (all 25+ packages)
- `@react-three/drei`, `@react-three/fiber`, `three`
- `expo`, `expo-asset`, `expo-file-system`, `expo-gl`, `react-native`
- `cmdk`, `date-fns`, `embla-carousel-react`, `input-otp`, `recharts`, `sonner`, `vaul`, `geist`

---

## 12. Recommendation Engine, Catalog Completion & Saved Looks Architecture (Phases 1–4 Review Specification)

This section provides the complete engineering specification of the architectural overhaul completed in October 2026 across four sequential phases, resolving recommendation bugs, implementing deterministic generation, automatic catalog shortfall filling, and saved outfit tag taxonomy.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        OUTFIT RECOMMENDATION & SAVED LOOKS PIPELINE                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  [User Request] ──────────────────────────────────────────────────────────┐            │
│       │                                                                   │            │
│       ▼                                                                   ▼            │
│  [Content Fingerprint]                                           ["Use Only My Rack"]  │
│  (SHA-256 over garments, catalog, occasion, season, DNA)         (Default: False)      │
│       │                                                                   │            │
│       ├─────────────────────────────────┬─────────────────────────────────┤            │
│       ▼                                 ▼                                              │
│  [Normal Generation]             [Shuffle Mode]                                        │
│  - seed derived deterministically - seed rotated with shuffle_index                    │
│  - is_stochastic = False          - is_stochastic = True                               │
│  - score jitter = 0.0             - score jitter = [-0.015, 0.015]                     │
│  - top candidate anchor           - random top-3 anchor                                │
│       │                           - excludes previous-screen core signatures           │
│       └─────────────────────────────────┬──────────────────────────────────────────────┘
│                                         │
│                                         ▼
│                        [1. Pure Engine Garment Skeletons]
│                        - Stable identity: str(_value(item, "id", ""))
│                        - Core signatures: (slot, item_id) for top/bottom/dress/saree
│                        - MMR core diversity: Prioritizes distinct core combinations
│                                         │
│                                         ▼
│                        [2. Wardrobe-Only Candidate Evaluation]
│                        - Filters candidates with score >= min_quality_threshold (0.65)
│                        - Let W = count of distinct above-threshold wardrobe looks
│                                         │
│                    ┌────────────────────┴────────────────────┐
│                    │ W >= limit                              │ W < limit (Shortfall K)
│                    ▼                                         ▼
│         [Return W Wardrobe Looks]               [Is wardrobe_only == True?]
│                                                      │                │
│                                              Yes ────┘                └─── No (Allowed)
│                                               │                             │
│                                               ▼                             ▼
│                                    [Return W Looks]             [Query Eligible Catalog Items]
│                                    (partial_results)            - Matches completing slot
│                                                                 - Occasion & season match
│                                                                 - Budget <= budget_max
│                                                                 - Audience: unisex / all
│                                                                             │
│                                                                             ▼
│                                                                 [Generate Mixed Candidates]
│                                                                 - Exactly 1 catalog item
│                                                                 - >= 1 wardrobe items
│                                                                 - Full constraint pipeline
│                                                                             │
│                                                         ┌───────────────────┴───────────────────┐
│                                                         │ Mixed looks fill K                    │ Mixed looks < K
│                                                         ▼                                       ▼
│                                              [Wardrobe + Mixed Looks]             [Shortfall Remains]
│                                                                                                 │
│                                                                                                 ▼
│                                                                                   [Evaluate Below-Threshold]
│                                                                                   - Hard-rule-valid wardrobe
│                                                                                   - Flags quality warnings
│                                                                                                 │
│                                                                                                 ▼
│                                                                                   [Return Structured Looks]
│                                                                                   - status: "partial_results"
│                                                                                   - quality_warning_outfit_ids
│                                                                                   - banner warning message
│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 12.1 Defect Taxonomy & Root Causes Resolved

Prior to this implementation, an architectural audit identified three root defects:
1. **Garment Memory Identity Bug (P0)**:
   - `OutfitCandidate.item_ids` was evaluated as `getattr(item, "id", id(item))`.
   - Items loaded from Supabase are Python `dict`s. Since dictionaries do not have an `id` attribute, `getattr` failed and defaulted to `id(item)`, returning CPython memory address integers (e.g. `140293819283`).
   - Consequently, IDs changed between runs, core equality checks failed, and catalog fallback detection `catalog_item_id in cand.item_ids` never matched a string UUID, causing catalog fallback to drop 100% of mixed looks.
2. **Forced Randomization of Normal Generation (P0)**:
   - The frontend's "PULL LOOKS" button generated `Math.floor(Math.random() * 10000000)` on every click.
   - The backend interpreted any non-zero seed as stochastic mode, injecting random score jitter and randomly choosing an anchor outfit from the top 3, destroying repeatability.
3. **Broken Catalog Fallback & Repetitive Looks (P0/P1)**:
   - MMR only checked whole-set Jaccard distance and silhouette tags. Users frequently received looks with the exact same shirt and pants, varying only by shoes.
   - When a wardrobe was missing required slots or could not produce the requested look count, catalog fallback failed silently and returned empty lists or errors.

---

### 12.2 Phase 1: Pure Engine Garment Identity & MMR Core Diversification

Implemented in `backend/app/styling/skeletons.py` and `backend/app/styling/generator.py`:

#### 1. Stable Business Identity Extraction
- Uniformly extracts garment IDs from dictionaries and objects without using CPython memory addresses:
  ```python
  def _get_item_id(item: Any) -> str:
      if isinstance(item, dict):
          return str(item.get("id", ""))
      return str(getattr(item, "id", ""))
  ```
- `OutfitCandidate.item_ids` resolves to a tuple of string IDs (e.g., `("w-top-1", "w-btm-2", "w-shoe-1")`).

#### 2. Core vs. Peripheral Slots & Signatures
- Defines authoritative slot sets:
  ```python
  CORE_SLOTS = frozenset({"top", "bottom", "ethnic_bottom", "dress", "ethnic_set", "saree"})
  PERIPHERAL_SLOTS = frozenset({"shoes", "layer", "bag", "jewelry", "dupatta"})
  ```
- `OutfitCandidate.core_signature`:
  - Formed as a sorted tuple of `(slot, item_id)` pairs:
    `tuple(sorted((slot, _get_item_id(item)) for slot, item in self.slots.items() if slot in CORE_SLOTS and _get_item_id(item)))`
  - Encoding slot identity with garment ID prevents cross-slot collisions (e.g. unisex pieces in different positions) and enforces stable comparisons.

#### 3. Deterministic MMR Diversification & Core Penalty
- `_mmr_diversify` in `generator.py`:
  - **Normal Generation (`is_stochastic = False`)**:
    - Top candidate `ranked_candidates[0]` is selected as the anchor deterministically.
    - Score jitter is strictly `0.0`.
    - Guarantees: Identical inputs produce the exact same ranked looks every time.
  - **Core Combination Priority**:
    - When selecting the next candidate, any candidate sharing a `core_signature` with already-selected looks incurs a `CORE_REPEAT_PENALTY` (0.45).
    - Ensures all distinct valid top+bottom or dress combinations are recommended before repeating a core with alternative shoes or layers.
    - Boundary behavior: When distinct cores are exhausted, remaining unique valid variations are returned up to the requested limit without padding fake duplicates.
  - **Shuffle Mode (`is_stochastic = True`)**:
    - Accepts `exclude_core_signatures: set[tuple[tuple[str, str], ...]]`.
    - Filters out candidate cores that were displayed on the immediately preceding screen.
    - If all valid alternatives are exhausted, restores the candidates and returns the best available results with an exhaustion notice.

---

### 12.3 Phase 2: Router & Schema Hardening (Catalog Fallback & Persistence Safety)

Implemented in `backend/app/schemas/outfit.py`, `backend/app/routers/outfits.py`, and database migrations:

#### 1. In-Memory Content Fingerprinting
- Database timestamps are insufficient because `public.products` lacks an `updated_at` column and `wardrobe_items` lacks auto-updating triggers.
- `compute_recommendation_fingerprint(...)` hashes the styling-relevant attributes of:
  - Active user wardrobe items (`id`, `category`, `slot`, `primary_color`, `formality`, `occasions`, `seasons`, `fit`).
  - Active catalog products.
  - User style preferences and body guidance.
  - Occasion, season, vibe, budget, and affinity fingerprint.
- Normal generation sets:
  `seed = int(fingerprint[:8], 16) % 10_000_000`

#### 2. Automatic Shortfall Catalog Completion Policy
- **Control**: "Use only my rack" (`wardrobe_only = True`) is a strict opt-out. By default (`wardrobe_only = False`), catalog completion is enabled.
- **Evaluation Order**:
  1. Generate wardrobe-only candidates. Filter those meeting `score >= min_quality_threshold` (0.65). Let this count be $W$.
  2. If $W < \text{limit}$ and `not wardrobe_only`, calculate shortfall $K = \text{limit} - W$.
  3. Query eligible catalog products completing required or unlockable skeleton slots (`gap_slots`).
  4. Eligibility constraints:
     - `audience`: Validated against user profile or restricted to `unisex` and `all`.
     - `slot`: Matches valid skeleton completion slot.
     - `occasions`: Must match occasion taxonomy.
     - `seasons`: Must match requested season, compatible aliases, or `all_season`.
     - `price_cents`: Must satisfy `price_cents <= budget_max * 100` (if budget specified).
  5. **1-Store-Item Rule**: Every mixed candidate must contain $\ge 1$ wardrobe items and **exactly 1** catalog store piece.
  6. Complete mixed candidates run through the full styling pipeline (skeleton validation, formality scoring, color harmony, occasion matching, anti-clash rules).
  7. Deduplicate mixed looks against wardrobe looks and other mixed looks; rank and select up to $K$.

#### 3. Below-Threshold Wardrobe Fallback & Partial Results
- If catalog pieces cannot fill the shortfall, include remaining unique, hard-rule-valid wardrobe looks with scores below the quality threshold.
- Flag each look in `quality_warning_outfit_ids` and include a prominent summary notice in `message`.
- If fewer than `limit` total valid looks exist, return `status: "partial_results"`. The UI treats this as an informative, successful recommendation, never an error.

#### 4. Persistence Safety & Atomic Transactions
- Created `public.save_outfit_with_items` function in `scripts/migrations/2026-10-21_save_outfit_rpc.sql` running under `security invoker` RLS.
- Strict Atomic RPC Persistence: `_persist_outfit_and_items` exclusively uses `save_outfit_with_items` within a single PostgreSQL ACID transaction. Non-atomic multi-step REST fallbacks and non-guaranteed compensating deletes are strictly refused to prevent orphaned outfit rows.
- Deployment Requirement: `scripts/migrations/2026-10-21_save_outfit_rpc.sql` must be applied to the target database. If the RPC is unavailable or fails, generation fails clearly (`OUTFIT_PERSISTENCE_ERROR`) without creating or leaving partial outfit data.
- Guarantees: **An outfit and its items are either both persisted or neither is. Zero unpersisted or orphaned outfit rows are returned to clients.**

---

### 12.4 Phase 3: Frontend Integration ("Use Only My Rack" & Transparent UI)

Implemented in `frontend/src/pages/OutfitsPage.tsx`, `frontend/src/lib/api.ts`, and `frontend/src/pages/OutfitsPage.css`:

#### 1. Unified Control
- Replaced ambiguous dual switches with a single toggle:
  - **"Use only my rack"** (`wardrobeOnly: boolean`, default `false`).
  - When unchecked, store pieces automatically fill any wardrobe shortfall.
  - Displays budget input and explanatory caption: *"The shop can fill the gap if your rack cannot make enough looks."*

#### 2. Request Mode Wire-Up
- Normal "PULL LOOKS" sends `shuffle: false`, `seed: 0`.
- "SHUFFLE ALTERNATIVES" sends `shuffle: true`, incremented `shuffle_index`, and previous screen's core keys (`exclude_core_keys`).

#### 3. Transparent Result Badges & Banners
- **Partial Results Banner**: Informative amber banner: *"Found W looks from your rack and M shop-completed styles. We couldn't find enough matching pieces in the shop to reach N looks."*
- **Quality Warning Badge**: Placed on any below-threshold fallback card: *"Alternative Look — wardrobe items have lower formality/occasion match"*.
- **Store Piece Badges**: Catalog items clearly display a store chip, price (e.g. `₹1,299`), slot completed (`"Completes: shoes"`), and a direct "View in Shop" link.

---

### 12.5 Phase 4: Saved Outfits & Canonical Tag System

Implemented in `backend/app/schemas/outfit.py`, `backend/app/routers/outfits.py`, `scripts/migrations/2026-10-21_add_outfit_tags.sql`, `frontend/src/lib/api.ts`, and `frontend/src/pages/OutfitsPage.tsx`:

#### 1. Database Schema
- Migration `scripts/migrations/2026-10-21_add_outfit_tags.sql`:
  ```sql
  ALTER TABLE public.outfits
    ADD COLUMN IF NOT EXISTS tags text[] NOT NULL DEFAULT '{}';

  CREATE INDEX IF NOT EXISTS idx_outfits_user_saved_tags
    ON public.outfits USING gin (tags);
  ```
- Forward-only, additive, non-breaking, and covered by existing `public.outfits` RLS policies.

#### 2. Canonical Tag Taxonomy
- Predefined canonical tags:
  ```python
  APPROVED_OUTFIT_TAGS = ["Work", "Date Night", "Wedding", "Vacation", "Try Later"]
  ```
- Normalization via `normalize_outfit_tags(tags: list[str])`:
  - Trims whitespace.
  - Matches case-insensitively to the canonical capitalization.
  - Discards unrecognized tags.
  - Preserves order and deduplicates.
  - Defaults to `["Try Later"]` if empty or all invalid.

#### 3. Idempotency & Style DNA Protection
- Saving an outfit (`POST /api/v1/outfits/{id}/save`):
  - Checks if outfit was already marked `is_saved == True` or if a `save` event was already logged in `outfit_events`.
  - **Fail-Closed Consistency**: On first save, records the `outfit_events` row (`event_type: "save"`, Style DNA weight `+2.0`) before marking `is_saved = True`. If event recording fails, returns HTTP 500 (`SAVE_EVENT_ERROR`) and leaves `is_saved = False`.
  - **Catalog Metadata Integration**: Extracts metadata across both wardrobe items and catalog products (`color_tags`, `colors`, `style_tags`, `category`, `subtype`) without fabricating wardrobe attributes.
  - Subsequent tag edits or re-saves update `outfits.tags` without inflating Style DNA scores or creating duplicate `outfit_events`.

#### 4. Interaction Semantics
| Action | Endpoint | Event Type | Style DNA Weight | Side Effects on `public.outfits` |
|---|---|---|---|---|
| **Save for Later** | `POST /outfits/{id}/save` | `"save"` | `+2.0` | `is_saved = True`, `tags = [...]`. First save only logs event. |
| **Update Tags** | `PUT /outfits/{id}/tags` | None | None | Updates `tags = [...]` under user RLS. |
| **Keep / Like** | `POST /outfits/{id}/events` | `"like"` | `+0.6` | Preserves saved state; reinforces style preferences. |
| **Wore It** | `POST /outfits/{id}/events` | `"wear"` | `+1.0` | Records real-life validation event. |
| **Not For Me** | `POST /outfits/{id}/events` | `"dislike"` | `-0.8` | Sets `is_saved = False`, resets `tags = '{}'`. Preserves event audit row. |
| **Unsave** | `DELETE /outfits/{id}/save` | None | None | Sets `is_saved = False`, resets `tags = '{}'`. Preserves event audit row. |
| **Skip** | `POST /outfits/{id}/events` | `"skip"` | `-0.2` | Negative feedback signal. |

#### 5. Frontend Saved Looks Experience
- **Tag Selection Modal**: Opens upon clicking "Save for Later", allowing single or multi-tag selection from canonical chips with a default "Try Later".
- **Dynamic Tag Filter Bar**: Horizontal filter bar in the Saved Looks tab displaying `"All"` plus each tag the user has actually used (`available_tags`).
- **Card Tag Badges & Inline Editing**: Cards render tag chips and an "Edit Tags" action that opens the tag modal pre-populated with current tags.
- **Action Error Banner**: Shows actionable error alerts if network or persistence fails; reverts optimistic UI state immediately.

---

### 12.6 Comprehensive Verification Matrix (43 Passing Tests)

All 43 unit and integration tests execute cleanly in under 15 seconds:

| Test Module | Tests | Focus Areas Verified |
|---|---|---|
| `backend/tests/test_outfits_router.py` | 13 | Saved looks tag defaults, canonical normalization, idempotent +2.0 Style DNA logging, tag updates, tag filtering with array containment, unsave, dislike event resetting saved state/tags, catalog completion shortfall filling, persistence rollback compensation on item insert failure. |
| `backend/tests/test_outfit_generator.py` | 10 | Dict string UUID extraction (never memory addresses), deterministic repeatability with identical inputs and seed=0, core garment repetition penalty (CORE_REPEAT_PENALTY=0.45), small wardrobe boundary handling (no duplicate padding), MMR silhouette diversity, shuffle core exclusion. |
| `backend/tests/test_outfit_skeletons.py` | 4 | Western, Ethnic, and Fusion slot skeletons, shoe-optional 1-piece and 2-piece valid look generation. |
| `backend/tests/test_outfit_rules.py` | 3 | Occasion clustering, seasonal weather constraints, anti-clash rules (e.g. sneakers with ethnic formal). |
| `backend/tests/test_gap_analysis.py` | 3 | Wardrobe gap analysis, counterfactual outfit unlock counts, catalog suggestion links. |
| `backend/tests/test_body_guidance.py` | 4 | Neutral mathematical derived body guidance, ephemeral memory calculations, zero external leakage. |
| `backend/tests/test_style_dna.py` | 3 | Bounded affinity updates (+1.0 wear, +0.6 like/save, -0.8 dislike, -0.2 skip), affinity reset action. |
| `backend/tests/test_wardrobe_service.py` | 3 | Pillow image sanitization, EXIF stripping, batch signed URL generation. |

#### Verification Execution Commands
```bash
# 1. Run all 43 backend tests:
.\backend\.venv\Scripts\python.exe -m pytest backend/tests

# 2. Run outfit router test suite specifically:
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_outfits_router.py

# 3. Run outfit generator test suite specifically:
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_outfit_generator.py

# 4. Frontend production typecheck and bundle build:
cd frontend && npm run build

# 5. Frontend fast linter:
cd frontend && npx oxlint
```

---

### 12.7 Peer-Review Checklist for External Agents

When reviewing this codebase with another agent, use the following audit checklist:

1. **Garment Identity Check**:
   - Inspect [`backend/app/styling/skeletons.py`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/styling/skeletons.py). Verify that `_get_item_id` checks `item.get("id")` and `getattr(item, "id")`, and never falls back to `id(item)`.
2. **Core Signature Format**:
   - Inspect `OutfitCandidate.core_signature`. Confirm that it uses `(slot, item_id)` pairs sorted by slot, preserving slot semantics.
3. **Deterministic MMR Ranking**:
   - Inspect `_mmr_diversify` in [`backend/app/styling/generator.py`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/styling/generator.py). Confirm that for normal requests (`is_stochastic = False`), the top item is popped as anchor deterministically, jitter is `0.0`, and `CORE_REPEAT_PENALTY` penalizes repeated cores.
4. **Catalog Completion & Sparse Wardrobe Logic**:
   - Inspect `generate_outfits` in [`backend/app/routers/outfits.py`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/routers/outfits.py). Confirm that wardrobe looks are evaluated first, `wardrobe_only = True` strictly prevents catalog queries, mixed looks require exactly one catalog item and at least one wardrobe item.
   - For sparse wardrobes (2–3 garments), verify that catalog completion automatically fills missing slots without showing hard errors.
   - Confirm that otherwise valid wardrobe and mixed looks falling below preferred quality thresholds are included as last-resort alternatives with `is_below_threshold = True` and clear warnings rather than being hidden or causing false errors.
   - Confirm that empty responses preserve `budget_status`, `no_products_in_budget`, and `cheapest_alternative` when catalog completion was attempted.
5. **Persistence Rollback & RPC**:
   - Confirm that `save_outfit_with_items` atomic PostgreSQL RPC is mandatory and non-atomic fallbacks are refused.
6. **Tag Model & Feedback Semantics**:
   - Inspect [`backend/app/schemas/outfit.py`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/schemas/outfit.py) for `APPROVED_OUTFIT_TAGS` and `normalize_outfit_tags()`.
   - Inspect `save_outfit`, `update_outfit_tags`, `get_saved_outfits`, and `record_outfit_event` in [`backend/app/routers/outfits.py`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/backend/app/routers/outfits.py).
   - Verify that `dislike` sets `is_saved = False` and `tags = []`.
   - Verify that re-saving or updating tags does not insert duplicate `save` events in `outfit_events`.
   - Verify Option A fail-closed consistency: save fails with 500 `SAVE_EVENT_ERROR` if the learning event write fails, leaving `is_saved = False`.
7. **Frontend State & Error Handling**:
   - Inspect [`frontend/src/pages/OutfitsPage.tsx`](file:///c:/Users/bruhdweiser1/Desktop/everything/i_bleedcode/FlashFit_AI/Flashfits-AI/frontend/src/pages/OutfitsPage.tsx). Confirm that single toggle "Use only my rack" defaults to `false`, tag modal opens on save/edit, tag filter bar calls `loadSavedOutfits(tag)`, and failed actions revert optimistic state and display `.outfits-action-error-banner`.
8. **Recommendation Redundancy & Result-Count Reporting**:
   - Inspect candidate selection in `generate_outfit_recommendations`. Confirm two-pass core-priority shortfall filling: Pass 1 selects candidates with unseen core signatures first; Pass 2 permits reusing core signatures with distinct completion items (e.g., alternate shoes or layers) only when distinct cores are exhausted.
   - Confirm canonical deduplication across all selection passes via `tuple(sorted(cand.item_ids)) in chosen_item_sets`.
   - Verify that whenever `status = "partial_results"`, the response message truthfully reports exact counts (e.g. `Found X of Y requested...`) without falsely claiming or implying that the requested count was met.
9. **Integration Audit & Verification**:
   - Confirm that all acceptance criteria across Steps 1–6 are verified via automated test suites.
   - Run backend test suite (`pytest backend/tests`), frontend unit tests (`node --test tests/shuffle_signatures.test.mjs`), and frontend production build (`tsc -b && vite build`) to ensure cross-layer contract stability.


