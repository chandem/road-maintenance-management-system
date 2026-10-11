# AI-RMMS live deploy checklist (`main`)

Use this for the **current product line** on `main` (roads, documents, AI ranking/assistant, materials, inspections).

**Not covered here:** department-role RLS proposals on `feature/department-role-management` (draft PR #1). Those stay unapplied until the production migration checklist is signed off.

---

## 1. Supabase (AI-RMMS project)

1. Confirm the dedicated AI-RMMS project is **active** (not paused). Region expected: `eu-west-1`.
2. Confirm foundation migrations are live (through materials + inspections as applicable):
   - Core schema, auth, documents, embeddings, semantic search
   - `009_materials` / `010_road_inspections` if those modules are in use
3. Verify tables exist: `roads`, `road_sections`, `work_orders`, `document_chunks`, `materials`, `road_inspections`.
4. Confirm RLS is enabled on operational tables (org-membership policies on `main`; department-restrictive policies are **not** required for this checklist).
5. Collect for backend/frontend env (never commit secrets):
   - Project URL
   - **Publishable** (anon) key
   - **Service role** key (backend only, if used)

---

## 2. Render (backend)

Environment variables must match `backend/app/core/config.py`:

| Variable | Required | Notes |
|----------|----------|--------|
| `SUPABASE_URL` | Yes | AI-RMMS project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Yes | Publishable/anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Optional | Server-only paths (e.g. some AI message writes) |
| `GEMINI_API_KEY` | For NL AI | Ranking/assistant still return deterministic evidence without it |
| `GEMINI_MODEL` | Optional | Default `gemini-2.0-flash` |
| `GEMINI_EMBEDDING_MODEL` | Optional | Default `text-embedding-004` (768-dim) |
| `SUPABASE_PROJECT_REF` | Optional | Ops label |
| `SUPABASE_REGION` | Optional | Default `eu-west-1` |

After deploy:

1. `GET /` → `status: running`
2. `GET /api/v1/health` → `status: ok`
3. `GET /api/v1/health?check_db=true` → `database.reachable: true` (or investigate env/network)

CORS allows localhost Vite ports and `*.vercel.app`.

---

## 3. Vercel (frontend)

| Variable | Required |
|----------|----------|
| `VITE_SUPABASE_URL` | Yes |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Yes |
| API base URL used by the UI (if configured in the app) | Point at `https://<render-service>/api/v1` |

Redeploy after env or frontend changes.

---

## 4. Operator smoke test (first release / regression)

Use a real signed-in user JWT (browser session or API `Authorization: Bearer <access_token>`).

### A. Platform

| Step | Call / action | Pass criteria |
|------|---------------|---------------|
| A1 | `GET /` | `status: running` |
| A2 | `GET /api/v1/health?check_db=true` | `status: ok` and DB reachable |

### B. Core RAMS data

| Step | Action | Pass criteria |
|------|--------|---------------|
| B1 | Sign in; create/join organization if needed | Profile has `organization_id` |
| B2 | Create road (`POST /api/v1/roads`) | 200/201 with id |
| B3 | Create section (`POST /api/v1/road-sections`) | Linked to road; condition set |
| B4 | Create work order | Visible on list |

### C. AI / scoring

| Step | Call | Pass criteria |
|------|------|---------------|
| C1 | `GET /api/v1/ai/road-ranking?limit=10` | Scores/ranks present; methodology mentions deterministic scoring |
| C2 | `POST /api/v1/ai/road-priority` with a section id | Score + evidence; no invented costs |
| C3 | `POST /api/v1/ai/office-assistant` with a simple ops question | Answer is advisory; modules_consulted listed |

### D. Documents

| Step | Action | Pass criteria |
|------|--------|---------------|
| D1 | Upload a small maintenance PDF/text | Document row + extraction status progresses |
| D2 | Trigger ingest/reindex if required | Chunks stored |
| D3 | Document Q&A / semantic search | Evidence snippets **or** honest “not available” |

### E. Dashboards

| Step | Call | Pass criteria |
|------|------|---------------|
| E1 | `GET /api/v1/dashboards/executive` | Metrics load without 5xx |
| E2 | `GET /api/v1/dashboards/maintenance` | Counts consistent with data |
| E3 | `GET /api/v1/dashboards/report/operational` | Structured report + advisory note |

### F. Materials & inspections (`main` modules)

| Step | Action | Pass criteria |
|------|--------|---------------|
| F1 | Create material via API or UI | Persists and lists |
| F2 | Create road inspection | Persists; section condition may update |

---

## 5. Principles to verify on every smoke

- AI answers cite **evidence** or say data is missing.
- Priority **scores** come from deterministic logic; LLM only explains.
- No AI path approves spend, contracts, or work closures.
- Service-role key never appears in the browser or frontend env.

---

## 6. If something fails

| Symptom | Likely cause |
|---------|----------------|
| Health DB not reachable | Wrong `SUPABASE_URL` / publishable key, or project paused |
| 401 on API | Missing/expired user JWT |
| Ranking empty | No `road_sections` visible under RLS for this user |
| Assistant without prose | Missing `GEMINI_API_KEY` (evidence summary still OK) |
| Embeddings fail | Gemini key/model or dimension mismatch vs `vector(768)` |
| CORS errors from custom domain | Add origin or use `*.vercel.app` deploy URL |

---

## 7. Relationship to department RLS work

| Track | Branch | Status |
|-------|--------|--------|
| Product / live ops | `main` | Use this checklist |
| Department RLS + privilege hardening | `feature/department-role-management` | Draft PR #1; disposable CI green; **production apply held** |

Do **not** apply feature-branch migrations `011`–`018` while validating `main` with this runbook.
