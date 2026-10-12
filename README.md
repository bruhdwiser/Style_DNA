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

## 📄 License
This project is licensed under the MIT License.
