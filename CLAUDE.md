# CLAUDE.md — StyleSense AI (Flashfits) Engineering & Context Guide

> **Project:** StyleSense AI (formerly Flashfits AI)  
> **Brand Identity:** *StyleSense — Public Dressing Room* ("Get dressed. Go somewhere.")  
> **Current Date / Status:** October 2026 — Production-ready decoupled React 19 + Vite frontend and FastAPI microservice backend with pure Python styling engine.

---

## 1. Executive Summary & Architecture Overview

StyleSense AI is an opinionated, privacy-first fashion styling platform and boutique commerce experience. It provides deterministic outfit recommendations from a user's uploaded wardrobe, counterfactual wardrobe gap analysis to unlock new looks, transparent Style DNA learning, and an editorial commerce storefront.

### High-Level Architecture

```text
┌────────────────────────────────────────────────────────┐
│             React + Vite Frontend (Port 5173)         │
│  - React 19 + TypeScript + Vanilla CSS                │
│  - React Router DOM v7 (Client-Side SPA Routing)      │
│  - Public Dressing Room Editorial Design System       │
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
│  - Pure Python Styling Engine (Skeletons, Rules, MMR)  │
│  - Batch Signed Storage URL Generation                 │
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

## 2. What Has Been Done (Completed Work Inventory)

### A. Architectural Migration & Decoupling
- **Decoupled from Next.js**: Migrated from a monolithic Next.js root app to a dedicated React 19 + Vite SPA (`frontend/`) and FastAPI backend (`backend/`).
- **Legacy Preservation**: Legacy Next.js files remain at the repository root (`app/`, `components/`, `contexts/`, `lib/`) for reference and business continuity until formal cutover approval.

### B. Pure Python Styling Engine (`backend/app/styling/`)
- **Port of StyleSenseAI Rules**: Fully implemented in pure Python with 0 external black-box AI dependencies.
- **Slot Skeletons (`skeletons.py`)**:
  - Western (`top` + `bottom` + `shoes`), Dress (`dress` + `shoes`), Saree (`saree` + `shoes`), Ethnic Set (`ethnic_set` + `shoes`), and layered variations.
  - **Shoe-Optional Fallback**: Gracefully generates valid 1-piece and 2-piece looks even when the user hasn't uploaded shoes yet.
- **Color Wheel Harmonies (`color.py`)**:
  - Monochromatic, complementary, analogous, triadic, and neutral palettes with lightness contrast validation.
- **Rule Constraints & Occasion Matching (`rules.py`)**:
  - Formality scoring, seasonal match, and weather constraints.
  - Occasion clustering (`casual`, `college`, `lounge`, `work`, `formal`, `festive`, `wedding`, `party`, `date`).
  - Strict anti-clash rules (`no_sneakers_with_ethnic_formal`, `no_formal_shoes_for_lounge`).
- **Diversity & Ranking (`generator.py`)**:
  - Maximal Marginal Relevance (MMR) ranking incorporating silhouette similarity penalties and exact silhouette counting to ensure visually distinct recommendations.
  - Stochastic jitter for organic diversity on repeated generations.
  - Added support for `date` / `date_night` occasion and `romantic` vibe.
- **Wardrobe Gap Analysis (`gaps.py`)**:
  - Counterfactual analysis: calculates which missing slot or catalog garment unlocks the maximum number of new viable outfits from existing closet items.
- **Style DNA Learning (`learning.py`)**:
  - Bounded heuristic scoring (+1.0 for wear, +0.6 for save/like, -0.8 for dislike, -0.2 for skip) bounded between `[-5.0, +5.0]`. Outfit validity rules always dominate affinities.

### C. FastAPI Backend Endpoints (`backend/app/routers/`)
- `products.py`: Public catalog browsing, category filtering, search, and admin inventory CRUD.
- `cart.py`: Shopping bag CRUD with item quantities and color/size variant support.
- `wardrobe.py`: Digital closet items, slot coverage (`tops`, `bottoms`, `layers`, `shoes`, `sarees`), image uploads to private Supabase Storage, and batch URL signing (`_batch_build_signed_view_urls`) to eliminate sequential latency and 404s.
- `outfits.py`: Occasion-based outfit generation, saved looks, and feedback event recording (`like`, `dislike`, `save`, `wear`, `skip`).
- `gaps.py`: Real-time gap analysis paired with store catalog recommendations.
- `style_dna.py`: User affinity scores breakdown and one-click affinity reset.
- `style_profile.py`: User style onboarding, preferences, derived neutral body shape guidance, and consent management.
- `ai_chat.py`: Stylist chat with OpenRouter LLM support, reasoning effort control (`effort: none` for Nemotron models), strict catalog grounding, and robust deterministic fallback using semantic fashion concept matching.
- `auth.py`: User profile, GDPR data export bundle (`GET /api/v1/me/export`), and complete account deletion cascade (`DELETE /api/v1/me/account`).
- `admin.py` & `analytics.py`: Telemetry tracking, inventory stats, and sales overview guarded by `AdminGuard` / `ADMIN_EMAILS`.

### D. "Public Dressing Room" Editorial Design System (`frontend/`)
- **Design Philosophy (`frontend/DESIGN_SYSTEM.md`)**:
  - Fashion desk / backstage fitting room aesthetic. "Get dressed. Go somewhere."
  - **Non-negotiables**: No soft SaaS gradients, no floating glass blobs, no emojis in UI, no pill buttons, 0px border-radius everywhere (2px on inputs only), sharp 1px borders, no box-shadows.
  - **Tokens (`index.css`)**:
    - `--paper` (`#F4F0E8`), `--paper-strong` (`#E7E1D5`)
    - `--ink` (`#181716`), `--ink-soft` (`#5E5A54`)
    - `--line` (`#C9C2B6`)
    - `--acid` (`#DFFF00`) for active states and selected filters
    - `--cobalt` (`#234BFF`) for links/info
    - `--signal` (`#E33B1E`) for destructive actions
  - **Typography**: System fonts only (Baskerville/Georgia serif display, Helvetica/Arial interface sans, Consolas/SF Mono uppercase metadata). Zero remote font delay.
  - **Editorial Masthead**: `STYLESENSE / ISSUE 01` with paper/ink contrast, responsive mobile index overlay.
  - **Colophon Footer**: Compact newspaper colophon with newsletter, support, privacy, Instagram, copyright.
- **Pages Implemented (All 14 Routes)**:
  - `HomePage.tsx`: Editorial cover, campaign typography, featured items.
  - `ShopPage.tsx` & `ShopProductDetailPage.tsx`: Filterable catalog, unified detail view.
  - `CartPage.tsx`: Editorial bag table, quantity steppers, checkout preview.
  - `LoginPage.tsx` & `AuthCallbackPage.tsx`: Supabase email/password & OAuth login.
  - `WardrobePage.tsx`: Digital rack, slot coverage, direct image uploads, AI tag modal with consent check.
  - `OutfitsPage.tsx`: Occasion generator, contact-sheet look tiles, "Why this works", feedback buttons (`KEEP`, `NOT FOR ME`, `WORE IT`), gaps tab.
  - `StyleDnaPage.tsx`: Visual affinity bars and affinity reset.
  - `StyleOnboardingPage.tsx`: Step-by-step style profile wizard.
  - `AiStylistPage.tsx`: Dedicated fashion stylist studio with catalog grounding.
  - `SettingsPage.tsx`: Privacy dashboard, consents, body guidance deletion, GDPR export, account purge.
  - `AboutPage.tsx`: Platform story, mission, and styling philosophy.
  - `AdminPage.tsx` & `AdminAnalyticsPage.tsx`: Inventory CRUD and real-time telemetry.

### E. Security, Privacy & AI Guardrails
- **Zero Body Data Leakage**: Body measurements and shapes are NEVER sent to OpenRouter or external LLMs.
- **Explicit Photo Consent**: Photos are only processed by vision APIs if user consent (`wardrobe_photo_analysis`) is verified.
- **Pillow Sanitization**: Images stripped of EXIF metadata and resized before upload or analysis.
- **Caller-Scoped Supabase Client**: User requests execute under `auth.uid() = user_id` Row-Level Security.
- **Grounded Catalog Recommendations**: Catalog UUIDs suggested by chat or fallbacks are checked against `public.products`, discarding hallucinated links.

### F. Quality Assurance & Testing
- **Backend Tests**: 24 passing unit tests in `backend/tests/` covering body guidance, gap analysis, outfit generation, rules, skeletons, style DNA learning, and wardrobe storage/sanitization.
- **Frontend Build**: 100% clean production build (`tsc -b && vite build`) producing optimized bundles with 0 TypeScript errors.

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
│   │   │   ├── outfits.py          # Outfit generation & saved looks
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
│   │   │   ├── rules.py            # Formality, seasonal, occasion matching
│   │   │   ├── skeletons.py        # Slot templates (Western, Ethnic, Fusion)
│   │   │   ├── taxonomy.py         # Canonical categories, fits & occasions
│   │   │   └── variations.py       # Minor outfit variation generator
│   │   └── main.py                 # FastAPI application factory & CORS setup
│   ├── tests/                      # 24 Passing Pytest Test Cases
│   │   ├── conftest.py             # Test fixtures & Supabase mocks
│   │   ├── test_body_guidance.py   # Neutral body guidance tests
│   │   ├── test_gap_analysis.py    # Gap analysis & catalog unlocks
│   │   ├── test_outfit_generator.py# Outfit generation & ranking
│   │   ├── test_outfit_rules.py    # Occasion, seasonal & formality rules
│   │   ├── test_outfit_skeletons.py# Skeletons & shoe-optional tests
│   │   ├── test_style_dna.py       # Affinity learning & reset
│   │   └── test_wardrobe_service.py# Image processing & batch URL signing
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
│   │   │   ├── HomePage.tsx        # Editorial cover & featured picks
│   │   │   ├── LoginPage.tsx       # Supabase email/password & OAuth sign-in
│   │   │   ├── OutfitsPage.tsx     # Occasion generator, feedback & gap analysis
│   │   │   ├── SettingsPage.tsx    # Privacy, consents, GDPR export & account purge
│   │   │   ├── ShopPage.tsx        # Catalog search, filter, and pagination
│   │   │   ├── ShopProductDetailPage.tsx # Modern product detail view (/shop/:id)
│   │   │   ├── StyleDnaPage.tsx    # Style DNA affinities & affinity reset
│   │   │   ├── StyleOnboardingPage.tsx # Style profile wizard & editor
│   │   │   └── WardrobePage.tsx    # Digital closet, uploads, AI tags & coverage
│   │   ├── App.tsx                 # Route declarations & route guards
│   │   ├── main.tsx                # Bootstrap with Auth & Cart Providers
│   │   └── index.css               # Editorial design tokens, reset, components
│   ├── DESIGN_SYSTEM.md            # "Public Dressing Room" Design Specification
│   ├── package.json                # Frontend dependencies
│   ├── tsconfig.app.json           # TypeScript configuration with @/* path alias
│   ├── vite.config.ts              # Vite server, Tailwind v4 plugin & /api/v1 proxy
│   └── .env.example                # Browser-safe environment template
│
├── scripts/                         # Database schema & SQL migrations
│   ├── schema.sql                  # Base database schema
│   ├── seed-styling-products.sql   # Idempotent seed data for styling catalog
│   ├── make-admin.sql              # Promote user to admin
│   ├── make-tanishq-admin.sql      # Admin promotion script
│   ├── debug-admin-setup.sql       # Admin verification helper
│   └── migrations/                 # Forward-only database migrations
│
├── PROJECT_DOCUMENTATION.md        # Comprehensive system documentation
├── README.md                       # Quickstart & setup guide
└── CLAUDE.md                       # This file (LLM & Developer context guide)
```

---

## 4. Key Developer Commands

### Backend Commands (from workspace root or `backend/`)

```bash
# Using the existing virtual environment in backend/.venv:
# On Windows:
.\backend\.venv\Scripts\python.exe -m pytest backend/tests

# Run FastAPI dev server:
.\backend\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000 --app-dir backend

# Check syntax / compilation:
.\backend\.venv\Scripts\python.exe -m compileall backend/app
```

### Frontend Commands (from `frontend/`)

```bash
cd frontend

# Install dependencies:
npm install

# Run dev server (http://localhost:5173):
npm run dev

# Typecheck and build production bundle:
npm run build

# Preview production build:
npm run preview
```

---

## 5. Critical Engineering Rules & Non-Negotiables

### A. Privacy & Security
1. **Never send body data to external LLMs**: Measurements, derived shapes, or body profiles must never leave ephemeral backend execution.
2. **Explicit Consent**: Photo analysis via OpenRouter requires explicit user consent in `user_consents` table (`wardrobe_photo_analysis`).
3. **Pillow Sanitization**: Always strip EXIF and downsample images before vision transmission.
4. **Row-Level Security**: Always use `get_user_scoped_supabase_client(token)` for user data operations. Never bypass RLS with service role key for user requests.
5. **Admin Guarding**: Admin endpoints require both email allowlist (`ADMIN_EMAILS`) and DB table verification (`admin_users`).

### B. Styling Engine
1. **Deterministic First**: Outfits are generated by deterministic rules, color harmonies, and skeletons. It is NOT a neural network.
2. **Bounded Affinity**: Style DNA adjustments are bounded within `[-5.0, +5.0]`. Hard rules always take precedence.
3. **Shoe Flexibility**: Skeletons must support shoe-less combinations if the closet has no shoes.
4. **Silhouette Diversity**: Always apply MMR silhouette similarity penalties to avoid recommending 3 visually identical outfits.

### C. Design System ("Public Dressing Room")
1. **No Gradients, Blobs, or Shimmer**: Background is flat warm paper (`#F4F0E8`), text is carbon ink (`#181716`), active accents are acid yellow (`#DFFF00`).
2. **Zero Border Radius**: Cards, buttons, and tiles must have `border-radius: 0` (2px permitted only on text inputs).
3. **No Stock Emojis or Icons as Primary Nav**: Use text words, counts, and typographic marks (`+`, `×`, `→`).
4. **System Fonts Only**: Serif display (Baskerville / Georgia), interface sans (Helvetica / Arial), metadata (Consolas / SF Mono).
5. **No AI Marketing Hype**: Say "a suggestion", "a match", "a second opinion", or "Why this works". Never say "powered by advanced AI".

---

## 6. Environment Variables Reference

### Backend (`backend/.env`):
- `SUPABASE_URL`: Supabase project URL (https://xyz.supabase.co)
- `SUPABASE_ANON_KEY`: Supabase anon public key
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key (admin only)
- `SUPABASE_JWT_SECRET`: JWT signing secret
- `ADMIN_EMAILS`: Comma-separated admin email addresses
- `ADMIN_USER_IDS`: Optional comma-separated UUIDs
- `OPENROUTER_API_KEY`: Optional OpenRouter API key
- `OPENROUTER_MODEL`: Model ID (e.g., `nvidia/nemotron-3.5-lightning:free`, `meta-llama/llama-3.3-70b-instruct`)
- `CORS_ORIGINS`: Allowed origins (e.g. `http://localhost:5173,http://localhost:3000`)
- `ENVIRONMENT`: `development` or `production`

### Frontend (`frontend/.env.local`):
- `VITE_SUPABASE_URL`: Supabase URL
- `VITE_SUPABASE_ANON_KEY`: Supabase anon public key
- `VITE_API_BASE_URL`: Backend URL (defaults to `http://localhost:8000/api/v1` or proxied via `/api/v1`)
