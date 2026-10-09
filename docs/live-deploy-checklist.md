# AI-RMMS live deploy checklist

Use this after pulling the latest `main` branch.

## 1. Supabase (AI-RMMS project)

1. Confirm project is **active** (not paused).
2. Apply migrations in order if not already applied:
   - `001` … `008` (foundation + semantic search)
   - `009_materials.sql`
   - `010_road_inspections.sql`
3. Verify tables exist: `roads`, `road_sections`, `work_orders`, `document_chunks`, `materials`, `road_inspections`.
4. Confirm RLS is enabled on operational tables.
5. Note **Project URL** and **anon/publishable key** for backend env.

## 2. Render (backend)

Environment variables (typical):

- `SUPABASE_URL`
- `SUPABASE_KEY` (or service role only if intentionally used server-side)
- `GEMINI_API_KEY`
- `GEMINI_EMBEDDING_MODEL` (if used)
- Port binding as required by Render

After deploy:

1. `GET /` → `status: running`
2. `GET /api/v1/health` (and DB check if available)
3. Sign in via frontend and call `GET /api/v1/dashboards/executive`

## 3. Vercel (frontend)

Environment:

- `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` (as configured in `frontend/src/lib/supabase.ts`)
- `VITE_API_BASE_URL_RMMS` → `https://<your-render-service>/api/v1`

Redeploy after frontend commits.

## 4. Smoke test (first release)

1. Sign in and create/join organization.
2. Create a road + section (API or SQL).
3. Create a work order; open ranking → scores appear.
4. Open executive dashboard → metrics load.
5. Upload a small maintenance PDF → chunks/embeddings reported.
6. Ask document Q&A → evidence or honest “not available”.
7. Ask office assistant a cross-module question.
8. (After 009/010) create a material and an inspection.

## 5. Principles to verify

- AI answers cite **evidence** or say data is missing.
- Scores come from **deterministic** logic, not free-form LLM invention.
- No AI path approves spend or contracts.
