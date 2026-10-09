# AI-RMMS Development Roadmap

## Current status (2026-10-09)

The backend foundation for the **first useful release** is largely in place:

> Ask AI questions about actual road-maintenance data and organizational documents and receive evidence-based answers.

| Capability | Status |
|------------|--------|
| Auth-aware FastAPI + Supabase RLS | Done |
| Core domain APIs (roads, sections, plans, work orders) | Done (CRUD) |
| MMMS / Finance / HR / General Assets | Done (CRUD + summaries) |
| Deterministic road priority & ranking | Done |
| Document extract → classify → chunk → embed → Q&A | Done |
| Cross-module office assistant | Done |
| Executive & module dashboards + operational report | Done |
| Frontend product UI | In progress / next |
| Live production validation | Ongoing |
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

## Phase 7 — Predictive Intelligence
- [ ] Road deterioration forecasting
- [ ] Machinery failure risk
- [ ] Budget forecasting
- [ ] Material demand forecasting
- [ ] Workforce/resource forecasting

---

## Immediate next priorities

1. **Live validation** — confirm Render + Supabase env, migrations `001`–`008`, upload a real document, run ranking and office assistant.
2. **Frontend** — bind Vercel UI to dashboards, document upload, and AI endpoints.
3. **Operational depth** — inspections/defects, cost-by-road, materials module.
4. **Predictive phase** — only after reliable historical data is flowing.

## Design principle (unchanged)

**Verified data → engineering/scoring engine → evidence → AI explanation**  
AI remains decision-support; humans approve spend, contracts, and closures.
