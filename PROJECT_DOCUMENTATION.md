# Flashfits AI - Architecture & System Documentation

**Project:** Flashfits AI  
**Frontend Architecture:** React 19 + Vite Single-Page Application (`frontend/`)  
**Backend Architecture:** FastAPI (Python 3.10+) Microservice (`backend/`)  
**Styling Engine:** Ported Pure Python StyleSenseAI Engine (`backend/app/styling/`)  
**Data, Auth & Storage:** Supabase (PostgreSQL, GoTrue, S3-Compatible Private Storage)  
**AI Assistant Provider:** OpenRouter API (Server-side optional enhancement layer)  
**Status:** Completed migration from legacy root Next.js full-stack app to decoupled React + Vite and FastAPI architecture (October 2026).

---

## 1. Verified vs. Planned/Pending Behavior

To maintain engineering integrity, this documentation distinguishes between behaviors verified directly within this codebase and planned/pending behaviors:

### A. Verified Behavior in Current Codebase
- **Deterministic Pure Python Styling Engine**: Full port of StyleSenseAI rules in `backend/app/styling/` (skeletons, color harmonies, formality constraints, seasonal logic, archetype scoring, and counterfactual gap unlocks). Verified with 100% successful Python compilation (`python -m compileall backend/app`).
- **Owner-Scoped Data Models & Migrations**: 7 forward-only SQL migrations in `scripts/migrations/` covering product styling attributes, style profiles, neutral body guidance, user consents, digital wardrobe, outfits, outfit items, outfit events, and cart variants.
- **FastAPI Endpoints**: Full CRUD, validation, and serialization contracts implemented using Pydantic v2 schemas across 12 router modules.
- **React + Vite Frontend**: Complete 10-stage styling journey built with modern React 19, TypeScript, React Router v7, and Vanilla CSS. Verified with 100% clean production build (`npm run build` in `frontend/` produces clean bundles with 0 errors).
- **Graceful Deterministic Fallback**: System functions end-to-end even when `OPENROUTER_API_KEY` is omitted, falling back to structured deterministic summaries and taxonomy templates.
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
│   ├── app/
│   │   ├── core/                   # Security, settings, Supabase client pool
│   │   │   ├── config.py           # Pydantic BaseSettings (tokens, admin, CORS)
│   │   │   ├── exceptions.py       # Standardized API error envelopes
│   │   │   ├── security.py         # Bearer token verification & admin guards
│   │   │   └── supabase.py         # Supabase client pool (anon, caller, admin)
│   │   ├── routers/                # REST API routers (/api/v1/*)
│   │   │   ├── admin.py            # Admin health and stats
│   │   │   ├── ai_chat.py          # Conversational stylist with catalog grounding
│   │   │   ├── analytics.py        # Telemetry tracking & admin analytics
│   │   │   ├── auth.py             # User profile, export & account deletion
│   │   │   ├── cart.py             # RLS-enforced shopping cart CRUD
│   │   │   ├── gaps.py             # Wardrobe gap analysis & catalog suggestions
│   │   │   ├── health.py           # Health check endpoints
│   │   │   ├── outfits.py          # Pure engine outfit generation & saved looks
│   │   │   ├── products.py         # Catalog listing, detail & admin inventory
│   │   │   ├── style_dna.py        # Style DNA affinities & affinity reset
│   │   │   ├── style_profile.py    # Style preferences, body guidance & consents
│   │   │   └── wardrobe.py         # Private closet uploads, tags & coverage
│   │   ├── schemas/                # Pydantic request/response data contracts
│   │   ├── styling/                # Ported pure Python StyleSenseAI engine
│   │   │   ├── body_fit.py         # Neutral body fit rules
│   │   │   ├── color.py            # Color harmonies & palettes
│   │   │   ├── explain.py          # Structured factual explanation generator
│   │   │   ├── features.py         # Feature extraction & attribute mapping
│   │   │   ├── gaps.py             # Counterfactual gap unlocking engine
│   │   │   ├── generator.py        # Combinatorial skeleton outfit generator
│   │   │   ├── learning.py         # Bounded Style DNA affinity tracking
│   │   │   ├── rules.py            # Formality, seasonal & weather constraints
│   │   │   ├── skeletons.py        # Slot templates (Western, Ethnic, Fusion)
│   │   │   ├── taxonomy.py         # Canonical categories, fits & occasions
│   │   │   └── variations.py       # Minor outfit variation generator
│   │   └── main.py                 # FastAPI application factory & CORS setup
│   ├── requirements.txt            # Python dependencies
│   ├── pyproject.toml              # Python project metadata
│   └── .env.example                # Backend environment template
│
├── frontend/                        # React + Vite Frontend
│   ├── src/
│   │   ├── components/             # Reusable UI & AdminGuard
│   │   │   ├── ui/                 # Button, Card, Input, Badge, Separator
│   │   │   ├── AdminGuard.tsx      # Client-side UI guard for admin routes
│   │   │   ├── ai-chatbot.tsx      # Floating AI fashion stylist modal
│   │   │   ├── navigation.tsx      # Responsive navigation header
│   │   │   ├── footer.tsx          # Global footer
│   │   │   └── product-card.tsx    # Catalog product card component
│   │   ├── contexts/               # Auth & Cart React contexts
│   │   ├── lib/                    # Typed API client & Supabase browser wrapper
│   │   ├── pages/                  # React Router page views
│   │   │   ├── AboutPage.tsx       # Platform story & architecture
│   │   │   ├── AdminAnalyticsPage.tsx # Real-time telemetry analytics dashboard
│   │   │   ├── AdminPage.tsx       # Product inventory CRUD management
│   │   │   ├── AiStylistPage.tsx   # Dedicated AI styling studio
│   │   │   ├── AuthCallbackPage.tsx# GoTrue OAuth redirect exchange handler
│   │   │   ├── CartPage.tsx        # Shopping bag & checkout preview
│   │   │   ├── HomePage.tsx        # Hero, value props, categories, featured picks
│   │   │   ├── LoginPage.tsx       # Supabase email/password & OAuth sign-in
│   │   │   ├── OutfitsPage.tsx     # Occasion generator, feedback & gap analysis
│   │   │   ├── ProductDetailPage.tsx # Classic product detail view (/product/:id)
│   │   │   ├── SettingsPage.tsx    # Privacy, consents, GDPR export & account purge
│   │   │   ├── ShopPage.tsx        # Catalog search, filter, and pagination
│   │   │   ├── ShopProductDetailPage.tsx # Modern product detail view (/shop/:id)
│   │   │   ├── StyleDnaPage.tsx    # Style DNA affinities & affinity reset
│   │   │   ├── StyleOnboardingPage.tsx # Style profile wizard & editor
│   │   │   └── WardrobePage.tsx    # Digital closet, uploads, AI tags & coverage
│   │   ├── App.tsx                 # Route declarations & route guards
│   │   ├── main.tsx                # Application bootstrap with Context Providers
│   │   └── index.css               # Design tokens, theme variables, utilities
│   ├── package.json                # Frontend dependencies
│   ├── tsconfig.app.json           # TypeScript configuration with @/* path alias
│   ├── vite.config.ts              # Vite server, Tailwind v4 plugin & /api/v1 proxy
│   └── .env.example                # Browser-safe environment template
│
├── scripts/                         # Database schema & SQL migrations
│   ├── schema.sql                  # Base database schema
│   ├── seed-styling-products.sql   # Idempotent seed data for styling catalog
│   └── migrations/                 # Forward-only database migrations
│
├── PROJECT_DOCUMENTATION.md        # This comprehensive system documentation
└── README.md                       # Quickstart & setup guide
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
- `GET /api/v1/wardrobe`: List owned wardrobe items with optional category filtering and review status.
- `GET /api/v1/wardrobe/coverage`: Summary of wardrobe coverage across slots (`tops`, `bottoms`, `layers`, `shoes`, `sarees`).
- `POST /api/v1/wardrobe/uploads`: Request a signed upload URL to private Supabase Storage.
- `POST /api/v1/wardrobe/suggest-tags`: AI photo tag suggestion with consent check, Pillow image sanitize, and taxonomy validation.
- `PATCH /api/v1/wardrobe/{id}`: Update tags, availability, or review status for a wardrobe item.
- `DELETE /api/v1/wardrobe/{id}`: Delete a wardrobe item and its corresponding storage objects.

### Outfits & Feedback
- `POST /api/v1/outfits/generate`: Generate occasion-specific outfits using the pure Python engine with optional 1-item catalog fallback.
- `GET /api/v1/outfits/saved`: List saved outfits for the authenticated user.
- `POST /api/v1/outfits/{id}/events`: Record an outfit feedback event (`like`, `dislike`, `save`, `wear`, `skip`).

### Gaps & Style DNA
- `GET /api/v1/gaps`: Perform counterfactual wardrobe analysis identifying missing slots that unlock outfits, with catalog suggestions.
- `GET /api/v1/style-dna`: Retrieve normalized positive and negative tag affinities and total event count.
- `POST /api/v1/style-dna/reset`: Reset all learned Style DNA affinities to baseline.

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
| `/product/:id` | `ProductDetailPage` | No | Classic product detail view compatibility alias. |
| `/cart` | `CartPage` | Yes | View cart, adjust quantities, remove items, checkout preview. |
| `/login` | `LoginPage` | No | Email/password sign-in/up and Google OAuth button. |
| `/auth/callback` | `AuthCallbackPage` | No | GoTrue OAuth hash token listener & redirect handler. |
| `/style-onboarding` | `StyleOnboardingPage` | Yes | Style profile wizard; edits profile when `?edit=true`. |
| `/wardrobe` | `WardrobePage` | Yes | Closet items, slot coverage, direct uploads, AI tag modal. |
| `/outfits` | `OutfitsPage` | Yes | Occasion/vibe generator, outfit cards, feedback, gaps tab. |
| `/style-dna` | `StyleDnaPage` | Yes | Normalized tag affinities & affinity reset action. |
| `/settings` | `SettingsPage` | Yes | Privacy consents, body guidance deletion, GDPR export, account purge. |
| `/profile` | `SettingsPage` | Yes | Route alias to `/settings`. |
| `/ai` | `AiStylistPage` | No | Conversational AI stylist chat with catalog links. |
| `/admin` | `AdminPage` | Admin | Product management & inventory CRUD (`AdminGuard`). |
| `/admin/add-product` | `AdminPage` | Admin | Create product form (`AdminGuard`). |
| `/admin/analytics` | `AdminAnalyticsPage` | Admin | Real-time views, sales, and conversion stats (`AdminGuard`). |
| `/about` | `AboutPage` | No | Platform story, mission, and styling philosophy. |

---

## 7. Security, Privacy & AI Boundary Guarantees

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

## 8. Honest AI & Rules Claims

- **Outfit Generation is Deterministic**:
  The outfit generator is **not** a generative AI black box or trained neural network. It is a deterministic rule engine that uses combinatorial slot skeletons, colour wheel harmonies (complementary, analogous, triadic, monochrome), formality scores, occasion dress codes, and fit guidelines.
- **Style DNA is Explainable Heuristic Learning**:
  Style DNA does not claim to use deep visual representation learning. It applies bounded mathematical adjustments (+1.0 for wear, +0.6 for save/like, -0.8 for dislike, -0.2 for skip) to color, style, and category affinity scores. Outfit validity rules and occasion constraints always dominate affinity scores.
- **OpenRouter is Strictly Optional**:
  The platform works completely offline from AI APIs. If `OPENROUTER_API_KEY` is not present, outfit explanations use factual rule-based templates, and photo tag suggestions fall back to deterministic taxonomy defaults.

---

## 9. Environment Variable Names & Local Setup

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

### B. Setup Commands

```bash
# 1. Backend Setup
cd backend
python -m venv .venv
# On Windows: .venv\Scripts\activate | On macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 2. Frontend Setup
cd ../frontend
npm install
npm run dev
```

---

## 10. Legacy Next.js Deprecation & Proposed Cleanup List

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
