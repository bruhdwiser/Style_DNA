# FlashFit FastAPI Backend

FastAPI backend foundation for the FlashFit fashion e-commerce application.

---

## 1. Quick Start (Local Development)

### 1.1 Prerequisites
- Python 3.10+ (tested with Python 3.14)
- A virtual environment (recommended)

### 1.2 Setup Virtual Environment & Install Dependencies

From the repository root or inside `backend/`:

```powershell
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux / macOS:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 1.3 Configure Environment Variables

Create `.env` inside `backend/` from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Fill in your Supabase project credentials in `backend/.env`:
- `SUPABASE_URL`: Your Supabase Project URL (`https://your-project.supabase.co`)
- `SUPABASE_ANON_KEY`: Your Supabase Public Anonymous API key
- `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase Service Role key (kept strictly on server)
- `SUPABASE_JWT_SECRET`: Optional; Supabase JWT Secret for local cryptographic verification
- `OPENROUTER_API_KEY`: Optional; OpenRouter API key for AI features

> **Note:** The backend configuration loader automatically checks `backend/.env` first, and will also look in parent `.env.local` for `NEXT_PUBLIC_SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` as seamless fallbacks during development.

### 1.4 Start the FastAPI Server

```powershell
uvicorn app.main:app --reload --port 8000
```

- **API Base URL:** `http://localhost:8000`
- **Interactive OpenAPI Docs:** `http://localhost:8000/docs`
- **Alternative ReDoc:** `http://localhost:8000/redoc`
- **Health Check Endpoint:** `http://localhost:8000/health` or `http://localhost:8000/api/v1/health`

---

## 2. Architecture & Design Principles

### 2.1 Supabase Token Verification (Zero Unverified JWTs)
Incoming Supabase user requests must include an HTTP Authorization header:
```http
Authorization: Bearer <supabase_access_token>
```

FastAPI verifies the token server-side via `app.core.security.verify_supabase_token`:
1. **Cryptographic Validation (Local):** If `SUPABASE_JWT_SECRET` is defined in `.env`, the token's HMAC-SHA256 signature, expiry (`exp`), and audience (`authenticated`) are validated locally via `pyjwt`.
2. **GoTrue Service Validation (Remote):** If no secret is configured, the token is verified against the official Supabase GoTrue endpoint (`GET ${SUPABASE_URL}/auth/v1/user`).

**Unverified decoded tokens are never accepted.** Any missing, malformed, or expired token immediately yields a standard `401 Unauthorized` response.

### 2.2 Preserving PostgreSQL Row Level Security (RLS)
To maintain user data isolation without bypassing database policies:
- User-scoped operations (e.g. Cart, Saved Looks, User Profile) initialize the Supabase client using `get_user_scoped_supabase_client(token)` from `app.core.supabase`.
- This client attaches the caller's verified bearer token to PostgREST HTTP calls.
- PostgREST evaluates Postgres policies with `auth.uid() = <user_id>` and role `authenticated`.
- Policies such as `auth.uid() = cart_user_id` are natively enforced.

### 2.3 Service-Role Key Isolation
- `SUPABASE_SERVICE_ROLE_KEY` bypasses all RLS and is restricted exclusively to `get_admin_supabase_client()`.
- It is only invoked after the request has passed the `require_admin` dependency, which verifies that the authenticated user exists in `public.admin_users`.
- It is never exposed to frontend code or client-facing configuration.

### 2.4 Consistent Error Response Format
All errors (custom application exceptions, validation errors, HTTP exceptions, and unhandled server errors) conform to a consistent envelope:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication token has expired",
    "details": null
  }
}
```

### 2.5 Vite Origin & CORS
The backend CORS middleware is configured out-of-the-box for:
- `http://localhost:5173` (Vite frontend default)
- `http://localhost:3000` / `http://localhost:3001` (Next.js storefront during migration)

---

## 3. API Route Surface & Authorization Rules

| Route | Method | Access Level | Description & Security Enforcement |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | Public | Service health check |
| `/api/v1/health` | `GET` | Public | Versioned health check |
| `/api/v1/auth/me` | `GET` | Authenticated | Token verification and returns authenticated user identity |
| `/api/v1/products` | `GET` | Public | Paginated product listing with search, category, and sorting |
| `/api/v1/products/{id}` | `GET` | Public | Product details by Supabase UUID |
| `/api/v1/products` | `POST` | **Admin Only** | Creates product; strictly guarded by `require_admin` |
| `/api/v1/products/{id}` | `DELETE` | **Admin Only** | Deletes product; strictly guarded by `require_admin` |
| `/api/v1/cart` | `GET` | Authenticated | Fetches user's cart; scoped to `auth.uid()`, enforces Postgres RLS |
| `/api/v1/cart` | `POST` | Authenticated | Adds/upserts item; validates catalog UUID; ignores client prices |
| `/api/v1/cart/{item_id}` | `PATCH` | Authenticated | Updates quantity of specific item in user's cart |
| `/api/v1/cart/{item_id}` | `DELETE` | Authenticated | Removes item from user's cart |
| `/api/v1/cart` | `DELETE` | Authenticated | Clears user's cart |
| `/api/v1/ai-chat` | `POST` | Public | Styling assistant; sanitizes links against catalog UUIDs; fallback |
| `/api/v1/analytics/track` | `POST` | Public/Auth | Records event and updates session |
| `/api/v1/analytics/stats` | `GET` | **Admin Only** | Store metrics; strictly guarded by `require_admin` |
| `/api/v1/admin/status` | `GET` | **Admin Only** | Safe operational status; strictly guarded by `require_admin` |

---

## 4. Intentional Security & Architecture Behavioral Changes

1. **Elimination of Client-Side Admin Password:**
   The Next.js analytics dashboard checked `password === 'admin123'` in `sessionStorage` and sent queries to an unprotected `/api/analytics/stats`. In FastAPI, `/api/v1/analytics/stats` strictly enforces `require_admin` (verifying either server-configured allowlist `ADMIN_EMAILS`/`ADMIN_USER_IDS` or `public.admin_users` role). Unauthenticated or ordinary user requests receive `401 Unauthorized` or `403 Forbidden`.

2. **Removal of Public Environment Debug Leak:**
   The Next.js `/api/debug` endpoint exposed key presence and length. In FastAPI, this public endpoint is eliminated and replaced by an admin-authenticated `/api/v1/admin/status` route disclosing only high-level operational booleans.

3. **Untrusted Model Output & Link Sanitization:**
   The AI Chat route post-processes all LLM generated markdown links against the real Supabase catalog. Any hallucinated product link is sanitized to plain text, preventing malicious or hallucinated URLs from routing users to 404s. The chat endpoint only performs read queries, never writes.

4. **Cart Price & Ownership Integrity:**
   The Next.js `/api/cart` route allowed inserting arbitrary products if `productId` was omitted. In FastAPI, `POST /api/v1/cart` strictly validates that the product exists in the authentic catalog, derives ownership exclusively from `auth.uid()`, and ignores any client-supplied prices.

