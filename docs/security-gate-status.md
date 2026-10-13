# Security gate status — department role management

**Branch:** `feature/department-role-management`  
**PR:** [#1](https://github.com/chandem/road-maintenance-management-system/pull/1) (draft)  
**As of:** 2026-10-11  
**HEAD reference:** `6655350` (docs) / JWT fix `b8fe659`

## Disposable local Supabase CI (required)

| Check | Result | Notes |
|-------|--------|--------|
| Repository migrations apply | Pass | Clean install sequence on GitHub-hosted runner |
| Authorization catalog checks | Pass | `authorization_catalog_checks.sql` |
| Department RLS behavior | Pass | Synthetic JWT claims in SQL |
| Auth Admin user provision | Pass | `signed_jwt_provision_auth_users.py` |
| Password-grant JWT + PostgREST | Pass | `signed_jwt_postgrest_smoke.py` |
| Release preflight | Pass | `migration_release_preflight.sql` |
| Backend unit tests | Pass | PR workflow |
| Frontend build | Pass | PR workflow |
| SQL syntax workflow | Pass | PR workflow |

Green integration examples:

- Push/PR on `b8fe659` — Auth Admin provisioning fix  
- PR workflow #96 on `6655350` — still green after docs updates  

## What the JWT smoke proves

With **genuine local Auth-issued access tokens**:

- Org admin / road manager / read-only read org A roads as designed
- Finance-only and other-org users cannot see org A roads
- Road manager can create roads; read-only cannot
- Document and chunk visibility is department-scoped
- Conversation ownership, user-message append rules, archived write denial, and forged assistant/system roles behave as policy requires

## What it does not prove

- Live production catalog matches every proposal line-for-line
- Render/Vercel runtime paths with service role
- Non-empty road-section integrity on real historical data
- Owner-approved staging project validation

## Production posture

- **Do not merge** PR #1 without checklist sign-off
- **Do not apply** repo proposals `011`–`018` to production by filename
- **Do not replay** recovered ledger SQL under `docs/recovered-migrations/`
- Full mapping: `docs/production-ledger-proposal-map.md`
- Full rollout steps: `docs/production-migration-checklist.md`

## Next owner decisions

1. Review ledger↔proposal map (name collisions are the highest operational risk)
2. Optionally authorize a **free/existing** non-production validation target (no paid branch without explicit approval)
3. Only then schedule production timestamps + cutover
