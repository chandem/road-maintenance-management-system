# Migration Source Recovery Notes

**Branch:** `feature/department-role-management`  
**Repository:** `chandem/road-maintenance-management-system`  
**Review date:** 2026-10-10  
**Status:** SQL source recovered and archived for migrations 011–015 and the onboarding RPC; initial schema compared with repository source. Production remains read-only during reconciliation.

## Latest recovery update — 2026-10-10

The exact SQL bodies for all five department/role migrations were recovered from the production project's PostgreSQL logs and the `supabase_migrations.schema_migrations.statements` records. They are archived under `docs/recovered-migrations/` on this feature branch, intentionally outside the automatic migration directory.

| Version | Name | Archive |
|---|---|---|
| `20261009115651` | `seed_core_departments_011` | `docs/recovered-migrations/20261009115651_seed_core_departments_011.sql` |
| `20261009115706` | `create_department_role_assignments_012` | `docs/recovered-migrations/20261009115706_create_department_role_assignments_012.sql` |
| `20261009115713` | `secure_department_role_assignments_013` | `docs/recovered-migrations/20261009115713_secure_department_role_assignments_013.sql` |
| `20261009115721` | `department_role_policies_014` | `docs/recovered-migrations/20261009115721_department_role_policies_014.sql` |
| `20261009115736` | `department_access_helper_015` | `docs/recovered-migrations/20261009115736_department_access_helper_015.sql` |

The log records show these statements were submitted through the Supabase management API on 2026-10-09. This resolves the earlier uncertainty about where the SQL came from. It does **not** make the draft PR's proposed migration files equivalent to the applied SQL.

### Read-only catalog reconciliation performed

- `public.departments` exists; the partial unique index `departments_org_code_unique` exists.
- The `GRMB` organization has all five department seed rows expected by migration 011: Road Asset Management, Machinery Maintenance Management, Finance, Human Resources, and General Asset Management.
- `public.user_department_roles` exists with the expected primary key, organization/user/department foreign keys, role check constraint, unique organization/user/department constraint, and both indexes introduced by migration 013.
- RLS is enabled on `public.user_department_roles`.
- The two policies from migration 014 exist: `users_can_view_own_department_roles` and `org_admins_manage_department_roles`.
- `public.has_department_role(uuid,text,text[])` exists with the security-definer SQL body and authenticated-only execute grant described by migration 015.
- These catalog checks verify object presence and configuration, **not** authorization behavior under real authenticated JWTs.
- No new production SQL was executed during this recovery.

## Evidence reviewed

### AI assistant schema

The source file `database/migrations/003_ai_assistant.sql` was introduced by commit `cc68c6924c73742eb9259bd48a32013a8fd4fd9e` (“Add AI Office Assistant data foundation”) on 2026-10-07. It creates `public.ai_conversations`, `public.ai_messages`, and `public.ai_message_sources`, plus organization-membership RLS policies.

The read-only production audit found those three tables absent. This means the current live schema does not match the end state expected from that source file. It does **not**, by itself, prove whether the file was never applied, later rolled back, or its objects were subsequently removed. Recover deployment records or the exact applied SQL before assigning a migration status.

The later proposal `database/migrations/014_ai_conversation_department_rls.sql` also creates these tables using `CREATE TABLE IF NOT EXISTS` and adds department-aware restrictions. Do not replay both files blindly: compare table definitions, policies, grants, and their dependencies in a disposable/non-production database first.

### Organization onboarding

The repository contains two distinct onboarding changes:

- `003_onboarding_hardening.sql` defines `private.create_organization_for_current_user(text,text)` and changes a profile update policy.
- `004_frontend_onboarding_rpc.sql` defines `public.create_organization_for_current_user(text,text)` for the frontend and rejects a second organization when the user's profile already has one.

The exact production-ledger SQL for `20261008183919_add_organization_onboarding_rpc` was recovered and archived at `docs/recovered-migrations/20261008183919_add_organization_onboarding_rpc.sql`. It creates the public RPC with role `admin`, `search_path = public, pg_catalog`, an explicit duplicate organization-code check, and profile activation. This differs from `database/migrations/004_frontend_onboarding_rpc.sql` (role `owner`, empty search path, no explicit duplicate-code check). Preserve both as evidence; do not overwrite the repository source or replay either automatically.

### Department and role migration history

The five applied SQL bodies were recovered and archived as documented above. The repository's `011_department_road_rls.sql` through `015_road_section_organization_integrity.sql` are proposals with different names and purposes; they must not be treated as exact copies of the five applied ledger entries.

## Remaining work

1. Continue reconciling the earlier ledger entries and investigate why the AI assistant tables are absent.
2. Compare the full live schema with all ledger/source migrations and classify each source mapping as matching, partially matching, divergent, superseded, or missing.
3. Use an already available isolated non-production database only if one is confirmed; do not create a paid Supabase branch/resource.
4. Run integration tests with real authenticated JWTs in non-production before considering a production change or merging PR #1.
5. Only after the baseline and authorization tests are reconciled, plan any remaining production migrations with an explicit review of the exact SQL and rollback strategy.

## Safety boundary

Do not rerun, reapply, or edit production migrations to recover their source. Source recovery is an inspection task, not a database change. Keep production read-only until source mapping, schema reconciliation, and authenticated authorization tests are complete.


### Document intelligence and embeddings catalog review — 2026-10-10

The migration ledger confirms entries `20261008123128` (`document_intelligence`) and `20261008123135` (`document_embeddings`). A read-only live catalog inspection found `public.documents` with the document-intelligence fields `extracted_text`, `file_size_bytes`, `extraction_status` (default `pending`), and `classification_confidence`. It also found `public.document_chunks` with `document_id`, `organization_id`, `chunk_index`, `content`, a nullable `vector` embedding, `embedding_model`, `embedding_provider`, `embedding_dimension`, and `embedding_status` (default `pending`). RLS is enabled on both tables. These observations establish that the key objects/columns are present, but do not prove that every policy, index, grant, vector dimension, or function matches the intended migration source.

The exact repository paths for the two source migrations have not yet been identified from the attempted path lookups; do not infer that absence from those failed lookups means the source files are absent. A direct ledger-statement retrieval attempt was blocked by the tool safety layer in this step, so no exact SQL archive or source-to-ledger equivalence claim is made for these two migrations.

### Initial schema comparison — 2026-10-10

The exact statement recorded for ledger version `20261008122917` (`initial_ai_rmms_schema`) was inspected read-only. Its table and index definitions match the core domain model in `database/migrations/001_initial_schema.sql` in substance: organizations, departments, profiles, roads/sections, plans, work orders, machinery, assets, employees, budgets, expenses, documents, AI analysis runs, AI recommendations, and their listed indexes. The ledger SQL is compactly formatted and omits the source file's explanatory comments, so this is a semantic comparison rather than a byte-for-byte identity claim. No additional archive was created because the source file already represents the same core schema. This does not establish that later migrations or live objects are fully reconciled.

### Document security catalog check — 2026-10-10

A further read-only catalog check confirmed RLS is enabled (but not FORCE RLS) on both `public.documents` and `public.document_chunks`. `documents` has the authenticated policy `members access documents`, using `private.is_org_member(organization_id)` for both visibility and writes. `document_chunks` has authenticated SELECT, INSERT, UPDATE, and DELETE policies scoped by `private.is_org_member(organization_id)`. Indexes currently present include `idx_documents_org_type`, `idx_documents_extraction_status`, `idx_documents_org_status`, `idx_document_chunks_document`, `idx_document_chunks_embedding_hnsw`, `idx_document_chunks_embedding_status`, and `idx_document_chunks_org`. The `document_chunks` table also has a unique index on `(document_id, chunk_index)`; a separate ordinary index exists on the same pair, which may be redundant but should not be removed without query/usage analysis.

These catalog findings are not authenticated-JWT tests and do not establish the vector dimension, function/grant parity, or exact source migration equivalence. Production remains unchanged.

### Embedding dimension check — 2026-10-10

A read-only PostgreSQL catalog query confirmed that `public.document_chunks.embedding` is `vector(768)`. This records the live dimension, but the matching model/provider and exact source migration have not yet been verified. The attempted repository path guesses and code search did not identify the migration source; those unsuccessful lookups are not evidence that the source file is absent. The production ledger entry `20261008123135` (`document_embeddings`) remains to be retrieved and compared. Do not change the column dimension, rebuild the HNSW index, or rerun embedding SQL until the expected embedding model and migration source are established.

### Exact production `document_embeddings` SQL recovered — 2026-10-10

A read-only query of `supabase_migrations.schema_migrations` recovered the complete statement recorded for version `20261008123135` (`document_embeddings`). It creates the `vector` extension in schema `extensions`, creates `public.document_chunks` with `embedding extensions.vector(768)`, metadata columns `embedding_model`, `embedding_provider`, `embedding_dimension`, and `embedding_status`, uniqueness on `(document_id, chunk_index)`, non-negative/range checks for chunk positions, and indexes for document ordering, organization, embedding status, and HNSW cosine similarity. The live catalog agrees on the 768 dimension and the listed indexes/table shape. The exact production statement is evidence, but the matching checked-in source migration path has not been found yet; do not treat failed GitHub code-search results as proof that no source exists. The HNSW index uses `embedding vector_cosine_ops` and should not be altered without model/query analysis. No production mutation was performed.

### Checked-in document migration sources located — 2026-10-10

The repository tree confirms the previously unlocated source files are present on `feature/department-role-management`: `database/migrations/005_document_intelligence.sql` and `database/migrations/006_document_embeddings.sql`. Source `005` matches the recovered production `20261008123128` statement text and the live `documents` columns/indexes observed so far. Source `006` matches the recovered production `20261008123135` statement in the extension setup, `document_chunks` table definition, `extensions.vector(768)`, checks, and index definitions. Note: source `006` contains a comment saying RLS is deferred; production currently has RLS and four organization-membership policies on `document_chunks`. That is not necessarily a mismatch in the migration statement itself because RLS/policies may have been applied by later SQL. Keep that difference documented and trace the source/policy migration history before any replay or migration-ledger repair. Backend code in `backend/app/services/document_embeddings.py` sets `DEFAULT_OUTPUT_DIMENSIONALITY = 768`, calls Gemini `embed_content` with that output dimensionality, and records the provider as `gemini`; `backend/app/core/config.py` defaults `gemini_embedding_model` to `text-embedding-004`. This aligns configured output dimension with `vector(768)`, but actual production environment configuration and successful live embeddings are not proven by source inspection alone. No production mutation was performed.

### Semantic search function and live document policies — 2026-10-10

Read-only production inspection of `public.match_document_chunks` confirms it is `LANGUAGE sql`, `STABLE`, not `SECURITY DEFINER` (therefore invoker context), with `search_path` set to `public, extensions`. Its body requires `dc.organization_id = filter_organization_id`, calls `private.is_org_member(filter_organization_id)`, excludes null embeddings, applies cosine-distance similarity threshold, and clamps result count to 1–50 with default 10. The body matches the security intent and key logic of checked-in `database/migrations/008_secure_semantic_search.sql`. The live ACL grants EXECUTE to `authenticated` and `service_role`, with no PUBLIC execute shown; this differs from a literal expectation based only on source's explicit revoke/grant statements, because Supabase's `service_role` privilege may be inherited or granted separately. Do not alter grants without tracing default privileges and full ACL history.

Live `pg_policies` currently shows only the organization-membership policies on `documents` (`members access documents`, ALL) and `document_chunks` (SELECT/INSERT/UPDATE/DELETE). No department-restrictive document/chunk policies were found in the live policy catalog, and the live `documents` table still lacks `department_code` per prior column inspection. This is consistent with `database/migrations/013_department_aware_document_access.sql` being a source-controlled proposal only, not applied to production. This confirms department-aware access is NOT live; organization-membership policies alone do not implement department-level isolation. Do not apply migration 013 to production before its non-production authenticated-JWT test matrix passes. Catalog checks are not a substitute for real JWT tests. No production mutation was performed.


### Excess authenticated table privileges — 2026-10-10

A read-only query of `information_schema.role_table_grants` found that the `authenticated` role has `TRUNCATE`, `REFERENCES`, and `TRIGGER` privileges on the inspected `public.materials` and `public.road_inspections` tables, in addition to normal CRUD. A broader query found the same three privileges across many public tables, including roads, road sections, documents, document chunks, organization/member tables, assets, budgets, expenses, employees, machinery, maintenance plans, work orders, and AI tables. The privileges are not grantable onward, but `TRUNCATE` is especially important because row-level security does not restrict TRUNCATE. This is a broad privilege-hardening issue, not isolated to migration 009 or 010.

Checked-in proposal `database/migrations/016_revoke_excess_authenticated_table_privileges.sql` revokes TRUNCATE, REFERENCES, and TRIGGER from PUBLIC, anon, and authenticated on a list of application tables. It is not recorded as applied in the production migration ledger query. It is explicitly marked source-controlled proposal only; do not execute it against production yet. First test the exact proposal in an isolated non-production database, confirm all listed tables exist there, review service/trigger workflows and grants, and verify application behavior after revocation. The companion `017_harden_function_execution_privileges.sql` is also a proposal and is not confirmed applied.

No production mutation was performed. Keep PR #1 and production migrations on hold until the proposed privilege changes and authenticated JWT tests are validated in non-production.
