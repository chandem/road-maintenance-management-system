# AI-RMMS Development Roadmap

## Current status (2026-10-11)

**Product line (`main`):** first-release backend + Materials/Inspections UI foundation.

**Security line (`feature/department-role-management`, draft PR #1):** department roles, department-aware RLS, conversation policies, privilege hardening.

Disposable local Supabase **security gates are green** (catalog, RLS behavior, real Auth-issued JWT PostgREST, release preflight). Production migration apply and PR merge remain **blocked** pending owner sign-off (`docs/production-migration-checklist.md`, `docs/security-gate-status.md`).

| Capability | Status |
|------------|--------|
| Auth-aware FastAPI + Supabase RLS | Done on main; department hardening on feature branch |
| Core domain APIs (roads, sections, plans, work orders) | Done (CRUD) |
| MMMS / Finance / HR / General Assets / Materials / Inspections | Done (CRUD + summaries where applicable) |
| Deterministic road priority & ranking | Done |
| Document extract → classify → chunk → embed → Q&A | Done |
| Cross-module office assistant | Done |
| Executive & module dashboards + operational report | Done |
| Department role + RLS proposals | Feature branch; CI security gates pass; prod apply held |
| Frontend product UI | Partial (dashboards, docs, materials, inspections) |
| Live production validation of new RLS | Not started (held) |
| Predictive intelligence | Not started |

---

## Phase 1 — Foundation
- [x] Repository architecture
- [x] Frontend scaffold
- [x] FastAPI backend scaffold
- [x] Environment configuration
- [x] Database migration structure

## Phase 2 — Data Foundation
- [x] Organization / departments / membership
- [x] Users and profiles
- [x] Roads and road sections
- [x] Maintenance plans
- [x] Work orders
- [x] Machinery
- [x] Employees
- [x] Finance (budgets, expenses)
- [x] General assets
- [x] Documents
- [x] Materials / road inspections (module APIs)

## Phase 3 — AI Core
- [x] AI provider abstraction (Gemini)
- [x] Conversation API foundation
- [x] Deterministic scoring + AI explanation
- [x] AI audit logging (`ai_analysis_runs`)
- [ ] Full AI tool registry (structured tools beyond assistant)

## Phase 4 — Document Intelligence
- [x] PDF / Excel / Word / text extraction
- [x] Document classification
- [x] Chunking + embeddings (768-dim)
- [x] pgvector semantic search RPC + RLS
- [x] Evidence-based document Q&A
- [ ] Storage-backed file archive (optional hardening)

## Phase 5 — System Integration
- [x] RAMS APIs integrated with AI ranking/priority
- [x] MMMS / Finance / HR / Assets readable by office assistant
- [x] Cross-module context service
- [ ] Deeper GIS / PostGIS map workflows

## Phase 6 — Operational Intelligence
- [x] Road prioritization (deterministic)
- [x] Rule-based dashboard alerts
- [x] Budget utilization views
- [x] Operational report endpoint
- [ ] Cost analysis by road / activity (deeper)
- [ ] Resource optimization recommendations

## Phase 7 — Authorization hardening (current feature branch)
- [x] Recovered production department-role ledger SQL into `docs/recovered-migrations/`
- [x] Repository proposals for department RLS, documents, conversations, privileges
- [x] Disposable CI: catalog + RLS behavior + Auth-issued JWT PostgREST + preflight
- [ ] Owner ledger reconciliation sign-off
- [ ] Optional approved non-production replay
- [ ] Production timestamped apply (only after sign-off)
- [ ] Merge PR #1 to `main`

## Phase 8 — Predictive Intelligence
- [ ] Road deterioration forecasting
- [ ] Machinery failure risk
- [ ] Budget forecasting
- [ ] Material demand forecasting
- [ ] Workforce/resource forecasting

---

## Immediate next priorities

1. **Owner decision on department RLS rollout** — complete `docs/production-migration-checklist.md`; keep production frozen until then.
2. **Live validation on current main capabilities** — Render + Supabase env, document upload, ranking, office assistant.
3. **Frontend** — complete department-aware UX only after RLS is approved for the target environment.
4. **Predictive phase** — only after reliable historical data is flowing.

## Design principle (unchanged)

**Verified data → engineering/scoring engine → evidence → AI explanation**  
AI remains decision-support; humans approve spend, contracts, and closures.
