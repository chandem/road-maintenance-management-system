# Production reconciliation — Step 37

Date: 2026-10-10  
Repository branch: `feature/department-role-management`  
Production project: `firzbqzbezuecvplsibi`  
Status: read-only source/catalog review; **no production changes made**

## Scope completed

- Re-read proposed migrations 011–018 and the staging release runbook.
- Compared required relations in the proposals with the live production `public` relation inventory.
- Retrieved the live definitions and ACLs for the department-role helper, organization-onboarding RPC, organization membership helpers, and semantic document search.
- Checked the dependency order and recorded remaining release gates.

## Live schema reconciliation

The live production relation inventory contains all 20 core business/authorization tables expected by the release preflight, including `maintenance_plans`, `work_orders`, `machinery`, `assets`, `budgets`, `expenses`, `employees`, `ai_analysis_runs`, and `ai_recommendations`.

The following are still absent from production and are only proposed by migration 014:
- `public.ai_conversations`
- `public.ai_messages`
- `public.ai_message_sources`

The `public.documents.department_code` column is absent and is proposed by migration 013. The current `public.road_sections.organization_id` is nullable. The latest read-only production count found no road sections, so this empty-table state is not sufficient to prove migration 015's backfill, trigger, or cross-organization rejection behavior.

## Function reconciliation

### `public.create_organization_for_current_user(text,text)`

Live production definition:
- `SECURITY DEFINER`, owned by `postgres`.
- Current search path is `public, pg_catalog`.
- Application relations in the body are explicitly schema-qualified.
- The body calls `auth.uid()` and uses built-ins such as `btrim`, `nullif`, and `now`.
- Current ACL includes `authenticated` and `service_role`.

Migration 017 proposes an empty search path and revokes execution from `PUBLIC`, `anon`, and `service_role`, leaving `authenticated`. The source review did not find an obvious unqualified application-table reference, but only a real authenticated onboarding test can establish that organization creation, admin membership creation, and profile update still work transactionally after this change. The repository proposal must not overwrite the live function body without exact reconciliation.

### `public.has_department_role(uuid,text,text[])`

Live production definition is currently `SECURITY DEFINER` with an empty search path. Its ACL currently includes `anon`, `authenticated`, and `service_role`. Migration 011 moves the privileged implementation to `private` and creates a `SECURITY INVOKER` public wrapper. PostgREST resolution, schema usage, policy evaluation, and the role matrix still require isolated staging tests.

### `public.match_document_chunks(...)`

Live production function is `SECURITY INVOKER`, but its query currently checks organization membership and organization ID rather than document department ownership itself. Department restrictions therefore depend on the proposed RLS policies on `documents` and `document_chunks`, plus caller-JWT retrieval. The JWT test must prove that unauthorized chunk text never reaches the API response or LLM prompt.

## Dependency review

The proposed sequence remains:

1. 011 — department road RLS and helper conversion
2. 012 — department restrictions for module tables
3. 013 — document department classification and parent-linked chunk policies
4. 014 — AI conversation/message/source schema and RLS
5. 015 — road-section organization integrity
6. 016 — revoke excess table-level structural privileges
7. 017 — function execution/search-path hardening
8. 018 — profile and department-role privilege hardening

This is a **staging test order only**, not production authorization.

## Release gate status

| Gate | Status | Evidence / reason |
|---|---|---|
| Repository migrations reviewed | Completed as source review | Migrations 011–018 and runbook reread |
| Production schema inventory reconciled | Partial/completed for required relation existence | All 20 core relations exist; 3 conversation tables and document department column are expected additions |
| Live privileged function definitions inspected | Completed read-only | Onboarding RPC and department/search helpers inspected |
| Road-section data/trigger behavior | Blocked | Production sections are empty; non-empty fixtures required |
| Isolated staging database | Blocked | No isolated staging project is available in the current workflow; no paid branch/resource is to be created without explicit approval |
| Migration execution in staging | Not run | Requires isolated staging |
| Catalog regression test after migrations | Not run against staging | Requires migrations applied in staging |
| Real authenticated JWT/Data API matrix | Not run | Requires disposable staging users, assignments, documents, roads, and conversations |
| Backend/frontend smoke tests against staged schema | Not run | Requires staging deployment/configuration |
| Production migration rollout | **On hold** | Must remain unchanged until all prior gates pass and production rollout is explicitly approved |

## Next required action

Provision or identify an already available **non-production** Supabase project (do not create a paid resource without permission), capture its baseline, and run the read-only preflight and road-section preflight there. Then apply the proposal sequence only in staging, stop on any SQL error, run catalog checks, and complete the real-JWT/API and backend/UI matrix. Passing source review or CI alone is not sufficient.

No production DDL/DML, migration replay, seed data, or production assignment changes were made during this step.
