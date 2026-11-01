# SyllabusSync AI — Production Vercel & Supabase Deployment Guide

This guide details the step-by-step procedure to deploy SyllabusSync AI to Vercel with a Supabase PostgreSQL backend database.

---

## 1. Supabase Configuration

- **Project:** `syllabussync-ai`
- **Project Ref:** `qdlnupgdtgmhvkknjmlv`
- **Region:** `ap-northeast-1` (Tokyo)
- **Supabase URL:** `https://qdlnupgdtgmhvkknjmlv.supabase.co`

### Database Connection Mode
Always use the **Supabase Transaction Pooler (Supavisor / PgBouncer)** on port `6543`:
- **Host:** `aws-0-ap-northeast-1.pooler.supabase.com`
- **Port:** `6543`
- **Database:** `postgres`
- **User:** `postgres.qdlnupgdtgmhvkknjmlv`
- **Mode:** Transaction pooling (`prepare_threshold=None` in `psycopg` to avoid prepared statement conflicts across transactions)
- **SSL Mode:** `require`

### Applying Row Level Security (RLS)
The RLS definitions have been prepared in:
`supabase/rls_policies.sql`

To apply RLS to your Supabase project:
1. Open the Supabase Dashboard: `https://supabase.com/dashboard/project/qdlnupgdtgmhvkknjmlv/sql`
2. Navigate to **SQL Editor** -> **New query**.
3. Paste the contents of `supabase/rls_policies.sql` and click **Run**.
4. Confirm that all 13 tables now display **RLS enabled** in **Table Editor**.

> [!IMPORTANT]
> The direct PostgreSQL connection via the pooler authenticates as the database owner (`postgres`), which possesses PostgreSQL `BYPASSRLS` privileges. Consequently, the FastAPI backend's verified JWT ownership checks are the primary enforcement boundary, while RLS secures direct PostgREST and client-side requests.

---

## 2. Environment Variables Configuration

Configure the following environment variables in your Vercel Project Settings (**Settings** -> **Environment Variables**):

| Variable Name | Environment | Description / Example |
| :--- | :--- | :--- |
| `APP_ENV` | Production | `production` (enforces strict JWT token validation) |
| `DATABASE_URL` | Production | `postgresql://postgres.qdlnupgdtgmhvkknjmlv:[PASSWORD]@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require` |
| `SUPABASE_PROJECT_URL` | Production | `https://qdlnupgdtgmhvkknjmlv.supabase.co` |
| `SUPABASE_JWT_SECRET` | Production | *(Optional if JWKS is used)* Your Supabase JWT secret |
| `ADMIN_API_KEY` | Production | Strong random token for accessing `/api/diagnostics` |
| `CORS_ORIGINS` | Production | `["https://your-vercel-domain.vercel.app"]` |
| `ALLOW_DEV_FALLBACK_ANALYSIS` | Production | `true` (enables fallback if Bedrock credentials not set) |
| `ALLOW_DEV_FALLBACK_YOUTUBE` | Production | `true` (enables fallback if YouTube API key not set) |
| `MAX_UPLOAD_SIZE_MB` | Production | `10` |

---

## 3. Vercel Project Configuration

The project includes a root `vercel.json` configured with:
1. **Frontend Builder:** `@vercel/static-build` targeting `frontend/package.json` with output directory `dist`.
2. **Backend Serverless Runtime:** `@vercel/python` targeting `api/index.py`.

### Project Settings in Vercel Dashboard:
- **Framework Preset:** Vite
- **Root Directory:** `./` (repository root)
- **Build Command:** `npm --prefix frontend run build`
- **Output Directory:** `frontend/dist`
- **Install Command:** `npm --prefix frontend install`

---

## 4. Build Commands

Locally verify frontend and backend build artifacts:

```bash
# Frontend build
npm --prefix frontend run build

# Python dependency check
python -m py_compile api/index.py backend/app/main.py
```

---

## 5. Backend Routing & Architecture

- All requests matching `/api/(.*)` route to `api/index.py` (FastAPI).
- Requests for `/assets/(.*)` and static files route directly to Vite build outputs.
- All non-API client routes fall back to `frontend/dist/index.html` (SPA routing).
- API routes will **never** accidentally resolve to the frontend index HTML.

---

## 6. Database Connectivity Checks

Verify the database connectivity using the diagnostic endpoint:

```bash
curl -H "X-Admin-Key: YOUR_ADMIN_API_KEY" https://your-vercel-domain.vercel.app/api/diagnostics
```

Expected response payload:
```json
{
  "status": "success",
  "database": {
    "status": "connected",
    "engine": "PostgreSQL",
    "tables_count": 13,
    "tables": [
      "course_assessments",
      "courses",
      "modules",
      "rejected_channels",
      "study_plans",
      "study_tasks",
      "syllabi",
      "syllabus_coverage_summary",
      "topic_resources",
      "topics",
      "user_settings",
      "video_resources",
      "youtube_search_cache"
    ]
  }
}
```

---

## 7. Authentication Verification

In production (`APP_ENV=production`):
1. **Unauthenticated requests** to protected endpoints (`/api/courses`, `/api/study-plan/*`, etc.) return `HTTP 401 Unauthorized`.
2. **Development header simulation** (`X-User-Id`) is **strictly rejected**.
3. **Bearer tokens** signed by Supabase (ES256 / HS256) are validated against Supabase's JWKS endpoint (`https://qdlnupgdtgmhvkknjmlv.supabase.co/auth/v1/.well-known/jwks.json`).
4. **Spoofed owner IDs** passed in request JSON bodies are discarded; ownership is exclusively assigned from the verified token `sub` claim.

---

## 8. Production Smoke-Test Procedure

After deploying to Vercel:

1. **Visit Domain:** Navigate to `https://your-vercel-app.vercel.app`. Verify that the dark navy theme renders without console errors.
2. **Google OAuth Sign In:** Click "Sign in with Google". Complete authentication and verify that user identity is displayed in the navigation header.
3. **Course Creation:** Create a new course (e.g. "Computer Networks - CSE3001"). Verify that the course card appears in the dashboard.
4. **Syllabus Upload:** Upload `CSE3016_syllabus.pdf`. Verify that all 6 Module 1 topics are extracted.
5. **Video Library:** Confirm topic-matched educational video lectures.
6. **Study Plan:** Generate an adaptive study plan and toggle one task complete. Reload the page and ensure the completion state persists in Supabase PostgreSQL.

---

## 9. Common Errors and Solutions

| Symptom / Error | Root Cause | Solution |
| :--- | :--- | :--- |
| `prepared statement does not exist` | Prepared statements on port 6543 | `prepare_threshold=None` is enforced in `database.py`. Ensure port 6543 is used. |
| `operator does not exist: text = uuid` | Comparing TEXT column with UUID `auth.uid()` | In SQL/RLS, cast `(auth.uid())::text`. |
| `relation "sqlite_master" does not exist` | SQLite query executed on PostgreSQL | Handled: `diagnostics.py` uses `information_schema.tables` when `is_postgres()`. |
| `TypeError: the JSON object must be str...` | Calling `json.loads` on pre-parsed JSONB | Handled: `_safe_json_loads()` gracefully accepts dicts and lists. |
| `HTTP 401: Invalid token signature` | Mismatched JWT secret or key format | Verify `SUPABASE_PROJECT_URL` matches the Supabase project reference `qdlnupgdtgmhvkknjmlv`. |

---

## 10. Rollback Guidance

If an issue occurs in production:
1. **Vercel Instant Rollback:** In the Vercel Dashboard, go to **Deployments**, locate the previous stable deployment, click the three dots (`...`), and select **Promote to Production**.
2. **Local Development Fallback:** Local development remains 100% on SQLite. If Supabase is unreachable locally, setting `DATABASE_URL=sqlite:///./syllabus_sync.db` in `backend/.env` immediately activates the local SQLite database.
