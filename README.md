# Flashfits AI - Fashion Styling & E-Commerce Platform

A production-ready fashion styling and e-commerce platform built with a high-performance **React + Vite** frontend and a **FastAPI (Python)** backend, backed by **Supabase** (Postgres, GoTrue Auth, Storage) and an optional server-side **OpenRouter AI** enhancement layer.

---

## 🌟 Architecture & Capabilities

Flashfits AI unifies an end-to-end e-commerce store with an advanced, deterministic fashion styling engine ported from StyleSenseAI:

- **Storefront & Catalog**: Browse curated casual, formal, ethnic, and luxury garments. Filter by category, occasion, formality, and budget with INR price conventions.
- **Pure Python Styling Engine**: 100% deterministic outfit generation using slot skeletons (e.g. tops + bottoms + layers + shoes, saree + optional jewelry), color harmonies (monochrome, complementary, analogous), occasion rules, and body fit constraints.
- **Private Digital Wardrobe**: Secure, owner-scoped digital closet backed by private Supabase Storage buckets, image sanitization (EXIF stripping, resizing, thumbnail generation), and per-slot wardrobe coverage analysis.
- **Gaps & Catalog Fallback**: Counterfactual wardrobe analysis identifying missing slots that unlock the highest number of complete outfits, with grounded product recommendations and 1-click cart addition.
- **Transparent Style DNA**: Explainable preference learning via user feedback (`like`, `dislike`, `save`, `wear`, `skip`) with bounded influence that never overrides physical outfit validity or occasion dress codes.
- **Privacy & Consent Hub**: Explicit, revocable user consents (`body_guidance_storage`, `wardrobe_photo_analysis`), immediate derived body guidance deletion, GDPR data export (`GET /me/export`), and complete account & closet purge (`DELETE /me/account`).
- **Optional AI Boundary**: OpenRouter AI is strictly an optional enhancement layer for conversational phrasing and garment photo tag suggestions. Zero body measurements are ever sent to LLMs, and all product links are grounded against database UUIDs.

---

## 👗 Pure Python Outfit Engine Deep Dive

The core styling intelligence is implemented in pure, dependency-free Python (`backend/app/styling/`). It evaluates wardrobe items through a 3-stage deterministic generation pipeline:

```text
[Wardrobe / Catalog Items]
           │
           ▼
Stage 1: Skeleton Instantiation
  Instantiates valid garments into discrete slot templates:
  • Western 2-Piece:  Top + Bottom + Footwear (+ Layer)
  • Western 1-Piece:  Dress / Jumpsuit + Footwear (+ Layer)
  • Ethnic Set:       Kurti Set / Anarkali / Co-ord + Ethnic Footwear (+ Ethnic Layer)
  • Traditional:      Saree + Blouse + Ethnic Footwear / Lehenga + Blouse + Dupatta
           │
           ▼
Stage 2: Deterministic Rule Filtering
  Prunes incompatible combinations using physical constraints:
  • Occasion Compatibility: Checks dress codes for 10 occasions (casual, work, party, festive, wedding, etc.)
  • Formality Alignment: Strict formality variance bounds (Δ <= 1.0) between upper, lower, and outer pieces
  • Seasonal / Weather Feasibility: Excludes heavy wool in summer or open sandals in rain/snow
  • Body Fit Rules: Neutral silhouette balance (e.g. fitted top with relaxed bottoms, or structured layering)
           │
           ▼
Stage 3: Harmony Scoring & Style DNA Ranking
  Scores surviving outfits out of 100 points:
  • Color Harmonies: Evaluates monochrome, complementary, analogous, neutral balancing, and accent rules
  • Pattern Clashing: Penalizes conflicting dense prints; rewards print + solid pairing
  • Style DNA Modifiers: Applies bounded user affinity boosts (+/- 15 pts max) derived from like/save events
           │
           ▼
[Ranked Outfits with Factual Explanations]
```

---

## 🛠️ Technology Stack

| Layer | Technology | Responsibilities |
|---|---|---|
| **Frontend** | React 19, Vite, TypeScript, React Router v7, Lucide Icons | Responsive client-side SPA (`frontend/`), Vanilla CSS design system, direct storage uploads, auth session management. |
| **Backend** | FastAPI, Python 3.10+, Pydantic v2, Pillow, Uvicorn, HTTPX | REST API (`backend/app/`), deterministic styling engine (`backend/app/styling/`), JWT verification, image processing. |
| **Database & Auth** | Supabase (PostgreSQL, GoTrue, Private Storage) | Row-Level Security (RLS) data scoping, OAuth & email authentication, signed storage URLs. |
| **AI (Optional)** | OpenRouter API (Claude 3.5 Sonnet / Vision) | Optional conversational explanation rephrasing and garment photo tag suggestions. |

---

## 📁 Repository Structure

```text
Flashfits-AI/
├── backend/                         # FastAPI Python Backend
│   ├── app/
│   │   ├── core/                   # Security, settings, Supabase client pool
│   │   ├── routers/                # REST endpoints (/api/v1/*)
│   │   │   ├── admin.py            # Admin health and stats
│   │   │   ├── ai_chat.py          # AI styling chat with catalog grounding
│   │   │   ├── analytics.py        # Telemetry tracking & admin analytics
│   │   │   ├── auth.py             # User profile, export & account deletion
│   │   │   ├── cart.py             # RLS-enforced shopping cart CRUD
│   │   │   ├── gaps.py             # Wardrobe gap analysis & catalog suggestions
│   │   │   ├── health.py           # Health check endpoints
│   │   │   ├── outfits.py          # Pure engine outfit generation & saved looks
│   │   │   ├── products.py         # Catalog listing, detail & admin inventory
│   │   │   ├── style_dna.py        # Style DNA affinities & reset action
│   │   │   ├── style_profile.py    # Style preferences, body guidance & consents
│   │   │   └── wardrobe.py         # Private closet uploads, tags & coverage
│   │   ├── schemas/                # Pydantic data schemas
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
│   │   ├── contexts/               # Auth & Cart React contexts
│   │   ├── lib/                    # Typed API client & Supabase browser wrapper
│   │   ├── pages/                  # React Router page components
│   │   │   ├── AboutPage.tsx       # Platform story & architecture
│   │   │   ├── AdminAnalyticsPage.tsx # Admin sales & view analytics
│   │   │   ├── AdminPage.tsx       # Admin product management
│   │   │   ├── AiStylistPage.tsx   # Conversational AI stylist chat
│   │   │   ├── AuthCallbackPage.tsx# Supabase OAuth redirect handler
│   │   │   ├── CartPage.tsx        # Shopping bag & checkout summary
│   │   │   ├── HomePage.tsx        # Storefront hero & featured collections
│   │   │   ├── LoginPage.tsx       # Email/password & Google OAuth
│   │   │   ├── OutfitsPage.tsx     # Occasion generator, feedback & gap analysis
│   │   │   ├── ProductDetailPage.tsx # Classic product detail view
│   │   │   ├── SettingsPage.tsx    # Privacy, consents, GDPR export & account purge
│   │   │   ├── ShopPage.tsx        # Catalog search & faceted filtering
│   │   │   ├── ShopProductDetailPage.tsx # Modern product detail view
│   │   │   ├── StyleDnaPage.tsx    # Style DNA affinities & affinity reset
│   │   │   ├── StyleOnboardingPage.tsx # Style profile wizard & editor
│   │   │   └── WardrobePage.tsx    # Digital closet, uploads, AI tags & coverage
│   │   ├── App.tsx                 # Route mapping
│   │   └── index.css               # Design system & theme tokens
│   ├── package.json                # Frontend dependencies
│   ├── vite.config.ts              # Vite server & backend proxy configuration
│   └── .env.example                # Frontend environment template
│
├── scripts/                         # Database schema & SQL migrations
│   ├── schema.sql                  # Base database schema
│   ├── seed-styling-products.sql   # Idempotent seed data for styling catalog
│   └── migrations/                 # Forward-only database migrations
│
├── PROJECT_DOCUMENTATION.md        # Comprehensive system documentation
└── README.md                       # Quickstart & setup guide
```

---

## 🚀 Getting Started Locally

### 1. Prerequisites
- **Node.js** (v18 or later) & **npm**
- **Python** (3.10 or later) & **pip**
- A **Supabase** account & project (or local Supabase CLI)

---

### 2. Configure Environment Variables

#### A. Backend Setup (`backend/.env`)
Create `backend/.env` based on `backend/.env.example`:
```bash
cd backend
cp .env.example .env
```
Populate the environment variable names:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
SUPABASE_JWT_SECRET=your_optional_jwt_secret_for_fast_local_hmac
ADMIN_EMAILS=["admin@flashfit.ai"]
ADMIN_USER_IDS=[]
OPENROUTER_API_KEY=your_optional_openrouter_api_key
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
ENVIRONMENT=development
```

#### B. Frontend Setup (`frontend/.env.local`)
Create `frontend/.env.local` based on `frontend/.env.example`:
```bash
cd ../frontend
cp .env.example .env.local
```
Populate the browser-safe variables:
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_BASE_URL=/api/v1
```

---

### 3. Database & Supabase Migrations

Apply the database schema and forward-only additive migrations in order via the Supabase SQL Editor:

1. **`scripts/schema.sql`**: Base commerce tables (`products`, `cart_items`, `analytics_events`, `admin_users`) with RLS.
2. **`scripts/migrations/2026-10-12_add-cart-item-variants.sql`**: Variant persistence (`selected_color`, `selected_size`).
3. **`scripts/migrations/2026-10-12_add-product-styling-attributes.sql`**: Product taxonomy attributes (`audience`, `slot`, `subtype`, `color_tags`, `formality`, `style_tags`, `occasions`, `seasons`, `fit`, `pattern`, `seed_key`).
4. **`scripts/migrations/2026-10-12_add-style-profiles-and-consents.sql`**: User style preferences (`style_profiles`), neutral body guidance (`body_profiles`), and privacy consents (`user_consents`) with RLS.
5. **`scripts/migrations/2026-10-12_add-wardrobe-items-and-storage.sql`**: Digital wardrobe table (`wardrobe_items`), RLS, and private storage bucket (`wardrobe`) policies.
6. **`scripts/migrations/2026-10-12_add-outfits-and-saved-looks.sql`**: Generated outfits (`outfits`) and outfit items (`outfit_items`) with owner-scoped RLS.
7. **`scripts/migrations/2026-10-12_add-outfit-events-and-style-dna.sql`**: Authenticated feedback events (`outfit_events`) for Style DNA.
8. **`scripts/seed-styling-products.sql`**: Idempotent styling catalog seed items.

---

### 3.1 Wardrobe Manifest & Bulk Ingestion Tool

The repository includes a production-grade wardrobe manifest importer (`scripts/import_manifest_wardrobe.py`) designed to safely populate a user's closet from the clothing catalog (`backend/tests/fixtures/test_wardrobe_manifest.csv`) and corresponding imagery (`Outfits/Images manifest/`).

Key characteristics:
- **Dynamic Auth User Resolution**: Resolves user UUID via Supabase Admin API (`auth.admin.list_users()`) by email address without creating dummy users or assuming hardcoded IDs.
- **Automated Image Processing**: Strips dangerous EXIF/GPS metadata, auto-rotates orientations, re-encodes images to standardized display JPEGs, and generates 320px thumbnails via Pillow.
- **Private Storage Upload**: Concurrently streams display and thumbnail images to the user's private folder in the `wardrobe` bucket (`{user_id}/{filename_stem}.jpg`).
- **Formality Normalization**: Clamps manifest formality ratings (`0..5`) to the database check constraint (`0..3`) while preserving raw manifest formality in JSONB `metadata`.
- **Rerun Idempotency**: Detects existing items by storage path, piece ID, or manifest filename, making repeated executions completely safe.

**CLI Usage**:
```bash
# Dry run to preview matches and skips without uploading:
python scripts/import_manifest_wardrobe.py --email user@example.com --dry-run

# Live import targeting a specific user:
python scripts/import_manifest_wardrobe.py --email user@example.com
```

---

### 4. Running the Development Servers

#### Terminal 1: FastAPI Backend
```bash
cd backend
# Windows:
python -m venv .venv
.venv\Scripts\activate
# Linux/macOS:
# python3 -m venv .venv && source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive API Docs (Swagger UI): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

#### Terminal 2: React + Vite Frontend
```bash
cd frontend
npm install
npm run dev
```
- Web Application: [http://localhost:5173](http://localhost:5173)

---

## 📡 Core REST API Reference

The backend provides authenticated endpoints under `/api/v1/*` with interactive OpenAPI docs available at `/docs`:

| Area | Method & Route | Description |
|---|---|---|
| **Outfits** | `POST /api/v1/outfits/generate` | Generates candidate outfits from wardrobe & catalog with physical rules & explanations. |
| **Outfits** | `POST /api/v1/outfits/events` | Records user feedback (`like`, `save`, `wear`, `dislike`) to adjust Style DNA affinities. |
| **Wardrobe** | `POST /api/v1/wardrobe/upload-url` | Issues a signed direct upload URL for the private `wardrobe` storage bucket. |
| **Wardrobe** | `POST /api/v1/wardrobe/finalize-upload` | Strips EXIF, generates thumbnail, derives taxonomy tags, and registers the item. |
| **Wardrobe** | `GET /api/v1/wardrobe/coverage` | Computes per-slot wardrobe depth and flags bottleneck missing pieces. |
| **Gaps** | `POST /api/v1/gaps/analyze` | Counterfactual gap discovery finding items that maximize complete outfit unlocks. |
| **Cart** | `POST /api/v1/cart/items` | RLS-scoped cart addition with color, size, and quantity validation. |
| **Style DNA**| `GET /api/v1/style-dna/profile` | Returns explainable affinity weights across colors, patterns, and categories. |
| **Consents** | `GET /api/v1/me/export` | GDPR-compliant JSON data export of all user profile, wardrobe, and event data. |

---

## 🧪 Testing & Verification Suite

Flashfits AI enforces comprehensive test coverage across both unit logic and integration boundaries:

```bash
# Run all backend tests with pytest:
cd backend
pytest -v

# Run styling engine unit tests:
pytest tests/unit/test_engine_rules.py tests/unit/test_color_harmonies.py -v

# Run wardrobe manifest fixture validation:
pytest tests/unit/test_wardrobe_manifest.py -v

# Run frontend production build check:
cd ../frontend
npm run build
```

---

## 🔒 Security & Privacy Guarantees

1. **Authentication & Token Verification**: Handled in the browser via Supabase GoTrue. On protected requests, the frontend sends the user's JWT access token as an `Authorization: Bearer <token>` header. FastAPI verifies the token cryptographically before processing.
2. **Postgres Row-Level Security (RLS)**: User-scoped Supabase client instances pass the verified caller token directly, ensuring queries for carts, wardrobes, outfits, events, and profiles are constrained by `auth.uid() = user_id`.
3. **Private Storage Isolation**: Garment photos reside in a private Supabase Storage bucket (`wardrobe`). Browser clients upload directly using signed upload URLs scoped to `user_id/{filename}`.
4. **Zero Body Data Sent to AI**: Neither body measurements nor body shapes are ever sent to OpenRouter or external LLMs.
5. **Mandatory User Tag Confirmation**: AI-suggested garment tags are validated against the internal taxonomy and require explicit user review before saving.
6. **Strict Product UUID Grounding**: AI responses are scanned and sanitized against real database catalog UUIDs, stripping hallucinated links or phantom prices.

---

## ⚖️ Honest AI & Rules Claims

- **Outfit Generation is Deterministic**: Flashfits AI generates outfits using pure Python rules (slot templates, color wheel harmonies, weather/season rules, formality matching, and archetype scoring). It does **not** rely on a black-box neural recommendation model for outfit validity.
- **Style DNA is Explainable Preference Tracking**: Feedback (`like`, `dislike`, `save`, `wear`, `skip`) applies bounded mathematical weight shifts to color, style, and category affinities. It is **not** an opaque deep-learning model and never overrides physical dress codes or occasion constraints.
- **OpenRouter is Optional**: If `OPENROUTER_API_KEY` is not provided, the entire styling journey continues to function seamlessly using deterministic explanation templates.

---

## 🚢 Deployment & Operational Troubleshooting Guide

### Production Readiness Checklist
1. **Secrets Management**: Ensure `SUPABASE_SERVICE_ROLE_KEY` is kept strictly server-side and never exposed in client bundles or public endpoints.
2. **CORS Allowlist**: Set `CORS_ORIGINS` in `backend/.env` to include your production frontend domain (e.g., `["https://app.flashfits.ai"]`).
3. **Storage Bucket Policies**: Verify the `wardrobe` bucket in Supabase has RLS enabled with owner-scoped `SELECT`, `INSERT`, and `DELETE` policies (`auth.uid()::text = (storage.foldername(name))[1]`).
4. **Health Check Probes**:
   - Liveness Probe: `GET /health` returns HTTP 200 `{"status": "healthy"}`
   - Service Readiness: `GET /api/v1/health` verifies Supabase client connectivity and service availability

### Common Operational Scenarios & Fixes

| Symptom | Root Cause | Resolution |
|---|---|---|
| `Failed to fetch` / Cloudflare Error 521 | Supabase paused or database containers booting | Go to Supabase dashboard and unpause project; wait 60 seconds for GoTrue and Postgres containers to reach healthy status. |
| Wardrobe upload returns 415 `invalid_mime_type` | Uploading unsupported image extension or raw text | Images must be JPEG, PNG, or WebP. The backend sanitization pipeline automatically normalizes display uploads to standardized `image/jpeg`. |
| DB insert fails with `wardrobe_items_formality_check` | Raw manifest formality > 3 | Database check constraint enforces `formality BETWEEN 0 AND 3`. Clamped automatically by `import_manifest_wardrobe.py` while preserving raw value in `metadata`. |
| 403 `Storage path does not belong to user` | Attempting to access or upload to a foreign user's prefix | Storage paths in the `wardrobe` bucket must strictly begin with `{auth.uid()}/`. The backend verifies path ownership before finalization. |

---

## 📄 License
This project is licensed under the MIT License.
