# AI-RMMS staging migration release runbook

Status: prepared; not executed. Use only an isolated non-production Supabase project. Never paste service-role keys into the frontend, chat, issue tracker, or test evidence.

## Gate 0 — environment

- [ ] Confirm the Supabase project URL and project ref are for staging, not production.
- [ ] Confirm the staging project can be discarded/reset and contains no real personal or operational data.
- [ ] Configure backend secrets only in the staging backend environment.
- [ ] Keep the production project unchanged. Do not create a paid branch or paid resource without explicit approval.
- [ ] Record the staging migration ledger and schema baseline before applying changes.

## Gate 1 — reconcile before applying

1. Run `database/tests/migration_release_preflight.sql` in the staging SQL editor.
2. Resolve all `BLOCKER` rows. Investigate every unexpected `PRESENT` result for the three AI conversation relations before migration 014.
3. Run `database/tests/road_section_organization_preflight.sql`. Test both empty and non-empty data cases; the current production table was empty, which is not sufficient evidence.
4. Compare each proposed migration with the actual staging schema, grants, policies, and function bodies. Do not replay a migration merely because its filename is numbered 011–018.
5. Confirm the onboarding RPC's exact signature and body. Do not overwrite it with the repository proposal just to make catalog checks pass.

## Gate 2 — apply only in staging

Use the reviewed proposal dependency order:

1. `011_department_road_rls.sql`
2. `012_department_module_rls.sql`
3. `013_department_aware_document_access.sql`
4. `014_ai_conversation_department_rls.sql`
5. `015_road_section_organization_integrity.sql`
6. `016_revoke_excess_authenticated_table_privileges.sql`
7. `017_harden_function_execution_privileges.sql`
8. `018_profile_and_role_privilege_hardening.sql`

After each migration, inspect the SQL editor result and key catalog changes. Stop immediately on any error; do not continue to later migrations. This order is a test proposal only, not an approved production execution plan.

## Gate 3 — catalog checks

- [ ] Run `database/tests/authorization_catalog_checks.sql` after all eight proposals in staging.
- [ ] Run the read-only release preflight again and investigate unexpected results.
- [ ] Confirm authenticated keeps only intended ordinary DML and column privileges.
- [ ] Confirm anon cannot read or mutate role assignments or execute protected helpers.
- [ ] Confirm function owners, SECURITY DEFINER settings, and empty search paths are as expected.
- [ ] Confirm all restrictive policies coexist correctly with existing permissive organization policies.

Catalog checks are necessary but not sufficient; they do not simulate PostgREST requests with real user JWTs.

## Gate 4 — seed disposable staging users and data

Create at least two organizations with fake data and actual Supabase Auth users:

- Organization A: owner/admin, road_asset department_manager, road_asset officer, road_asset read_only, machinery_maintenance manager, finance manager, human_resources manager, general_assets manager, ordinary member with no department assignment, and inactive member.
- Organization B: an owner/admin and a road_asset manager.
- Create roads and sections in each organization; include a valid section, a section with a null organization ID for backfill testing, and isolated test cases for missing parent and cross-organization mismatch. Do not keep deliberately invalid rows after testing.
- Create documents/chunks for each department, including one legacy document with `department_code IS NULL`.
- Create conversations/messages for two users, including an archived conversation.
- Keep all seed content synthetic and disposable.

## Gate 5 — authenticated JWT / Data API matrix

Use each test user's own access token against the Supabase Data API. Do not substitute a service-role key for user-authorization tests.

- [ ] Road manager/officer can perform permitted road writes; read_only can read but cannot write; non-road users and other-organization users cannot access the rows.
- [ ] Module data is department-isolated; users cannot change organization IDs or bypass active membership checks.
- [ ] Document listing, single-document reads, keyword search, semantic search, Q&A evidence, chunk reads/writes, and reindexing enforce department and tenant isolation.
- [ ] A legacy unclassified document is visible only to an organization admin.
- [ ] Semantic retrieval returns no unauthorized chunk text before it is passed to the LLM.
- [ ] Conversations are scoped by organization and ownership/role rules. read_only can read allowed history but cannot create conversations or post messages.
- [ ] Direct authenticated inserts of assistant/system messages fail; user messages must reference an accessible active conversation.
- [ ] Archived conversations reject new user messages.
- [ ] Anon cannot access `user_department_roles` or call protected department helpers.
- [ ] Profile INSERT is limited to `id, full_name`; UPDATE is limited to `full_name`; protected columns cannot be self-assigned.
- [ ] The live onboarding RPC creates an organization, an admin membership, and the profile organization ID transactionally; duplicate onboarding fails without leaving partial records.
- [ ] Road-section trigger derives organization from the parent road and rejects cross-org references. Changing a road's organization with sections is rejected.
- [ ] Service-role assistant-message persistence and conversation timestamp updates work, while the service key remains server-side.
- [ ] Existing ordinary CRUD operations that should remain available after 016/018 still work.

Record the HTTP status and a redacted result for each test. Never record JWTs, API secrets, or real document contents.

## Gate 6 — backend and UI smoke tests

- [ ] Sign in through the staging frontend.
- [ ] Create an organization using the existing UI onboarding path.
- [ ] Load dashboard, road inventory, inspections, documents, and conversations.
- [ ] Upload a small synthetic document; confirm extracted text and chunks are saved under the selected department.
- [ ] Ask a question and verify the response cites only authorized evidence.
- [ ] Create a conversation, send a user message, persist an assistant reply, refresh, and verify history.
- [ ] Verify failures fail closed if department checks or authorization lookups are unavailable.

## Gate 7 — release decision

- [ ] All catalog checks pass.
- [ ] All JWT/Data API tests pass.
- [ ] Backend/frontend smoke tests pass.
- [ ] Security Advisor findings are reviewed and documented.
- [ ] A production-specific migration reconciliation, backup plan, and recovery plan are reviewed separately.

If any item fails, stop, fix the proposal, and repeat staging from a clean baseline. Passing staging does not itself authorize production changes; production rollout requires a separate explicit decision.
