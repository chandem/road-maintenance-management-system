# Production ledger ↔ repository proposal map

**Branch:** `feature/department-role-management`  
**As of:** 2026-10-12  
**Purpose:** Prevent accidental re-application of already-applied SQL and clarify what remains to ship.

**Safety:** Recovered files under `docs/recovered-migrations/` are **evidence only**. Do not replay them against production.

---

## 1. Name collision warning

Production ledger **names** end in `_011` … `_015`. Repository proposal **filenames** also start at `011_…`.  
**They are not the same migrations.**

| Production ledger (applied) | Repository proposal (not applied) |
|-----------------------------|-----------------------------------|
| `seed_core_departments_011` | `011_department_road_rls.sql` |
| `create_department_role_assignments_012` | `012_department_module_rls.sql` |
| `secure_department_role_assignments_013` | `013_department_aware_document_access.sql` |
| `department_role_policies_014` | `014_ai_conversation_department_rls.sql` |
| `department_access_helper_015` | `015_road_section_organization_integrity.sql` |

Any production apply of repository `011`–`018` must use **new unique timestamps after** `20261009115736`, and only after approval and non-production validation.

---

## 2. Applied production ledger

The live Supabase migration ledger was checked on 2026-10-12. It contains 13 entries; its current tip is `20261009115736_department_access_helper_015`.

| Ledger version | Ledger name |
|----------------|-------------|
| `20261008122917` | `initial_ai_rmms_schema` |
| `20261008123128` | `document_intelligence` |
| `20261008123135` | `document_embeddings` |
| `20261008140938` | `authorization_foundation` |
| `20261008141032` | `secure_semantic_search` |
| `20261008183919` | `add_organization_onboarding_rpc` |
| `20261009092658` | `materials_inventory_009` |
| `20261009092727` | `road_inspections_010` |
| `20261009115651` | `seed_core_departments_011` |
| `20261009115706` | `create_department_role_assignments_012` |
| `20261009115713` | `secure_department_role_assignments_013` |
| `20261009115721` | `department_role_policies_014` |
| `20261009115736` | `department_access_helper_015` |

Recovered files under `docs/recovered-migrations/` are evidence for the applied history, not runnable migrations.

---

## 3. Live catalog facts verified 2026-10-12

Read-only queries against production confirmed:

- `public.documents.department_code` exists (type `text`).
- `public.ai_conversations`, `public.ai_messages`, and `public.ai_message_sources` all exist.
- `public.roads` and `public.road_sections` exist.
- RLS is enabled on `documents`, all three AI conversation tables, `roads`, and `road_sections`; FORCE RLS is false on those tables.
- The four document/conversation tables have 15 policies in total: documents 5, conversations 4, messages 4, message sources 2.
- The department-specific policies on those four tables are marked **RESTRICTIVE**; the older organization-member policies are **PERMISSIVE**. PostgreSQL combines restrictive policies with the applicable permissive policies, so review must account for both sets rather than judging a policy by name alone.
- `public.has_department_role(uuid,text,text[])` is **SECURITY INVOKER** (not SECURITY DEFINER), has `search_path = ''`, is executable by `authenticated`, and is not executable by `anon` or `service_role` according to `has_function_privilege`.

These are catalog facts only. They do not replace behavior tests with real Auth-issued JWTs against an owner-approved non-production environment, nor do they prove Render/Vercel runtime behavior or data integrity over non-empty historical road-section rows.

---

## 4. Repository proposals still to reconcile

| Repo file | Intent | Status / caution |
|-----------|--------|------------------|
| `010_department_role_foundation.sql` | Foundation for clean installs | Clean-install CI sequence only; do not replay as a production migration by filename |
| `011_department_road_rls.sql` | Road/section/inspection department RLS and helper arrangement | Must be compared against the live catalog and tested before any release |
| `012_department_module_rls.sql` | Module-specific RLS | Compare against live policies/grants before scheduling |
| `013_department_aware_document_access.sql` | Department-aware document access | Live `department_code` and department policies already exist; inspect for exact semantic differences before applying anything |
| `014_ai_conversation_department_rls.sql` | AI conversation ownership and department policies | The three AI tables already exist in production; inspect differences, do not treat this as table creation from scratch |
| `015_road_section_organization_integrity.sql` | Road-section organization integrity | Verify live constraints/triggers and non-empty historical rows before any change |
| `016_revoke_excess_authenticated_table_privileges.sql` | Revoke excess table privileges | Confirm current grants and app behavior first |
| `017_harden_function_execution_privileges.sql` | Function ACL and search-path hardening | Compare exact live function definitions/ACLs; onboarding compatibility must be tested |
| `018_profile_and_role_privilege_hardening.sql` | Profile/role privilege hardening | Test onboarding and role assignment flows before release |

**Clean-install CI** applies the repository sequence to a disposable database. This validates the proposal sequence, not the identity or safety of those files for production.

---

## 5. CI and validation boundary

The repository security-gate report records passing disposable local Supabase checks for migration apply, authorization catalog checks, department RLS behavior, Auth Admin provisioning, password-grant JWT/PostgREST smoke tests, release preflight, backend tests, frontend build, and SQL syntax.

Those checks do **not** prove:
- exact production behavior under every real-user role;
- Render/Vercel service-role runtime paths;
- integrity of non-empty historical road-section data;
- owner-approved staging validation.

The existing RAMS Supabase project is paused, and restoring it requires a paid upgrade. Do not restore or pay for it without explicit approval. Do not create a paid branch/project without explicit approval.

---

## 6. Recommended next steps

1. Keep production migration apply on hold.
2. Keep PR #1 in draft; do not merge until the release checklist is signed off.
3. Complete a policy/grant/function diff between live production and each proposal file.
4. Use the existing free disposable CI database for repeatable authorization tests; clearly label this as CI, not staging.
5. If a genuinely separate non-production Supabase target becomes available at no cost, run Auth-issued JWT/PostgREST behavior tests there.
6. Verify road-section integrity against non-empty data before any related migration.
7. Only after all gates pass and explicit approval, prepare uniquely timestamped release SQL after `20261009115736`, backup/PITR checks, and a rollback plan.

**Do not** apply proposals `011`–`018` to production by filename, replay recovered migration SQL, merge PR #1, or pay for staging without explicit approval.
