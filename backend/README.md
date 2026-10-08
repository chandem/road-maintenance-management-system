# AI-RMMS Backend

FastAPI backend for the AI-Powered Road Maintenance Management System.

## Connect to the AI-RMMS Supabase project (Step 2)

1. Open the **AI-RMMS** Supabase project (eu-west-1, database `ai-rmms`).
2. Copy **Project URL** and **anon / publishable key** from Project Settings → API.
3. Create `backend/.env` from the example:

```bash
cp .env.example .env
```

4. Set at least:

```env
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=<anon-key>
SUPABASE_PROJECT_REF=<project-ref>
SUPABASE_REGION=eu-west-1
GEMINI_API_KEY=<key>
```

5. Apply database migrations in order (`001` … `008`) on this project if not already applied — especially `008_secure_semantic_search.sql`.

6. Verify:

```bash
uvicorn app.main:app --reload
curl http://127.0.0.1:8000/api/v1/health?check_db=true
curl http://127.0.0.1:8000/api/v1/system/config
```

- `health?check_db=true` probes Supabase reachability.
- `system/config` shows non-secret connection status (never returns keys).

### Auth model

- Browser / API clients send `Authorization: Bearer <user-access-token>`.
- Backend builds a **user-scoped** Supabase client so RLS and `private.is_org_member()` apply.
- Optional `SUPABASE_SERVICE_ROLE_KEY` is for controlled server jobs only (bypasses RLS).

### Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Tests

```bash
pytest -q
```

Keep all secrets in environment variables. Never commit real keys.
