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

## Gate 8 — backup, failure handling, and recovery

This is a preparation checklist, not evidence that a backup or restore has been performed. Complete it separately for staging and again for production.

### Before each migration batch

- [ ] Record the exact project ref, database version, current migration ledger, current branch/commit, and the migration file checksum or reviewed commit.
- [ ] Confirm a recoverable database backup or provider-supported restore point exists and record its timestamp. Confirm the responsible operator has permission to restore it.
- [ ] Export or capture the relevant pre-change catalog state: affected table columns, constraints, indexes, RLS flags/policies, grants, function definitions/owners/configuration, and trigger definitions.
- [ ] Record baseline row counts and stable identifiers for affected tables; do not export real document contents or secrets into the repository.
- [ ] Agree on a stop condition and recovery owner. Do not begin if a restore path is unverified.

### If a migration errors or a verification fails

1. Stop immediately. Do not run the remaining migrations and do not blindly rerun the failed file.
2. Save the exact error, migration name, SQL editor output, migration ledger, and a redacted catalog snapshot.
3. Determine whether the statement or earlier statements in that file committed. Do not assume the whole file was atomic unless it was explicitly executed in a transaction and PostgreSQL confirms rollback.
4. Compare actual catalog/data state with the pre-migration snapshot. Identify completed statements, partial DDL, backfills, and any changed grants or policies.
5. Prefer a reviewed, forward-only corrective migration when it is safe and data-preserving. If the state cannot be safely reconciled, restore to the approved recovery point under the recovery owner's direction.
6. After recovery, rerun the read-only preflight, catalog checks, and affected JWT/Data API tests. Record the outcome before resuming.

### Rollback limitations and data safety

- Do not treat deleting a migration-ledger row as rollback; it does not reverse schema or data changes.
- Do not use `DROP`, broad `REVOKE`, policy replacement, or table recreation as an improvised rollback.
- A schema rollback may not restore data changed by backfills, triggers, or application writes. Review data-loss risk and application compatibility before any reverse operation.
- For production, use the provider's approved point-in-time recovery/restore procedure if required; confirm the impact on writes made after the restore point before proceeding.
- Do not restore production over staging or use staging fixtures in production.
- No recovery action is authorized by a CI pass. Production recovery and migration application require an explicit, separately reviewed decision.

### Recovery evidence to retain

- [ ] Start/end timestamps and operator.
- [ ] Project ref and database version (never keys or tokens).
- [ ] Backup/restore-point identifier and restore verification result.
- [ ] Failed migration and exact error, with secrets and personal data redacted.
- [ ] Before/after migration ledger and catalog checks.
- [ ] Corrective migration or restore reference, if any.
- [ ] Results of preflight, catalog checks, JWT/Data API tests, and UI smoke tests.
- [ ] Explicit go/no-go decision and outstanding risks.

## Automated real-JWT smoke workflow (manual, read-only)

The GitHub Actions workflow `.github/workflows/supabase-migration-integration.yml` now has an opt-in `workflow_dispatch` input named `run_staging_jwt_smoke`. It defaults to false. The real-JWT job runs only when manually requested with that input set to true; it does not run on ordinary pull requests or pushes.

Before enabling the input, configure these repository Actions secrets with values from a verified disposable staging project only:

- `STAGING_SUPABASE_URL`
- `STAGING_SUPABASE_ANON_KEY` (publishable/anon key for staging; never the service-role key)
- `STAGING_ROAD_ID` (a seeded road that should be visible to admin, road manager, and road read-only identities)
- `TOKEN_ORG_ADMIN`
- `TOKEN_ROAD_MANAGER`
- `TOKEN_ROAD_READ_ONLY`
- `TOKEN_FINANCE_MANAGER`
- `TOKEN_NO_DEPARTMENT_ROLE`
- `TOKEN_INACTIVE_MEMBER`
- `TOKEN_OTHER_ORG`

Use short-lived, staging-only user access tokens and rotate/reissue them when expired. Do not commit tokens, put them in workflow logs, or use production tokens. The job refuses the known production project ref and fails if any required value is missing.

To run: open GitHub Actions, select **Isolated Supabase migration integration test**, choose **Run workflow**, select the feature branch, set `run_staging_jwt_smoke=true`, and start the run. Review the job result and ensure the staging URL and seeded identities are correct before running it.

**Coverage boundary:** this automated real-JWT smoke test currently checks road-row SELECT visibility for seven identities and denial of anonymous execution of `has_department_role`. It does not yet cover writes, document/chunk policies, AI conversations, profile column grants, onboarding, or road-section triggers. Those remain separate staging release gates in this runbook. A skipped or unconfigured job is not a passing real-JWT test.

