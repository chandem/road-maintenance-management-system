# Department-level RLS verification plan

Do not apply migrations 011, 012, or 013 to production until the checks below pass in a staging project.

## Preconditions

1. Use a staging Supabase project with the same schema/migrations as production.
2. Create or identify real Auth users in one test organization:
   - organization owner/admin;
   - road_asset department_manager and read_only user;
   - machinery_maintenance department_manager;
   - finance department_manager;
   - human_resources department_manager;
   - general_assets department_manager;
   - a member with no department role;
   - a user from another organization.
3. Assign roles through the admin API or authenticated admin UI. Every target user must be an active organization member.
4. Seed one document and chunks for each department, plus one legacy document with department_code NULL. Use fake/non-sensitive content only.
5. Confirm active assignments using a read-only query joining organization_members, user_department_roles, and departments, filtered to the staging organization and active members.

## Execute through the Data API

Use each test user's own access token and the Supabase REST/Data API. Do not use the service-role key; it bypasses RLS and invalidates the test.

| Test identity | GET roads | POST road | PATCH road | Expected |
|---|---:|---:|---:|---|
| Organization owner/admin | allowed | allowed | allowed | organization admin retains access |
| road_asset department_manager | allowed | allowed | allowed | department manager has read/write |
| road_asset officer | allowed | allowed | allowed | officer has read/write |
| road_asset read_only | allowed | denied | denied | read-only is non-mutating |
| finance-only user | denied/empty | denied | denied | other department cannot access road data |
| no department role | denied/empty | denied | denied | unassigned member cannot access road data |
| inactive org member | denied | denied | denied | inactive membership cannot access |
| user from another organization | denied | denied | denied | tenant isolation is preserved |

For denied SELECT requests, PostgREST may return HTTP 200 with an empty array because RLS filters rows; assert no protected rows are returned. For INSERT/UPDATE, assert no row is created/changed and inspect the response/error. Use seeded staging records.

## Document and AI retrieval matrix (migration 013)

Test directly through the Data API using authenticated JWTs, not the service role.

| Test identity | Department document SELECT | Keyword search | Semantic/RPC search | Insert/update/delete |
|---|---|---|---|---|
| Organization owner/admin | all departments + legacy NULL | all departments + legacy NULL | all departments + legacy NULL | allowed |
| Manager/officer for the document's department | own department only | own department only | own department only | allowed |
| Read-only for the document's department | own department only | own department only | own department only | denied |
| User from another department | no rows for that department | no snippets/evidence | no chunks/evidence | denied |
| Member with no department role | no department-owned rows | no snippets/evidence | no chunks/evidence | denied |
| Any non-admin | legacy documents with NULL department are invisible | no legacy snippets/evidence | no legacy chunks/evidence | denied |
| User from another organization | no rows | no snippets/evidence | no chunks/evidence | denied |

Also verify:
- Keyword search filters are enforced by document RLS before extracted_text is returned.
- match_document_chunks remains SECURITY INVOKER and chunk RLS filters results inside the database before content can reach application code or an LLM prompt.
- A user cannot insert a document under a department they do not hold a write role for.
- A user cannot insert/update chunks linked to a document in another department or organization.
- Read-only users cannot DELETE (test explicitly; a broad FOR ALL policy could accidentally allow this).
- A document with NULL/invalid department classification remains admin-only.
- The backend API now requires department scope for non-admin list, keyword search, semantic search, and Q&A; document GET/reindex authorize against the stored department; upload requires an explicit department_code and write permission. Verify these routes with real JWTs. The SQL migration remains required so direct Data API access and the semantic RPC enforce the same policy.
- Existing documents are not auto-classified from title, filename, or document_type.
- Cross-department AI assistant and dashboards remain admin-only until their complete retrieval pipeline has equivalent authorization.

## Other RLS and function checks

- Repeat GET/PATCH against road_sections and GET/INSERT/PATCH against road_inspections.
- Attempt to change organization_id to another organization; it must fail.
- Call /rest/v1/rpc/has_department_role without a token; it must be rejected.
- Confirm the exposed public helper is SECURITY INVOKER and the private helper has no EXECUTE for anon/PUBLIC.
- Run the Supabase Security Advisor after applying to staging and review remaining SECURITY DEFINER warnings individually.

## Current project state

The live project has zero active department-role assignments. Existing document and chunk rows must remain admin-only until explicitly classified. The proposed migrations are source-controlled only; no production schema or policy has been changed. Do not apply these policies until role assignments exist and the complete staging matrix passes.


## Read-only production preflight findings (2026-10-09)

These findings came from catalog/schema queries only. No production DDL or policy changes were executed.

- Migrations 011–013 are not recorded in the live migration history.
- The live `public.documents` table does not yet have `department_code`; migration 013 is required before document-department policies can work.
- The live project currently has zero rows in `public.user_department_roles`, so a role-based test cannot pass meaningfully until test assignments exist.
- The live `public.has_department_role(uuid,text,text[])` function is currently SECURITY DEFINER and executable by `anon`, `authenticated`, and `service_role`. Migration 011 is intended to harden this, but its schema move and wrapper must be tested before production use.
- The live `public.match_document_chunks` function is SECURITY INVOKER, but currently checks organization membership only. Department-level chunk RLS is still required before semantic results can be trusted for non-admin users.
- `storage.objects` and `storage.buckets` have RLS enabled but no policies were returned by the catalog query. Before introducing private file uploads/downloads, define and test object policies or document a strictly server-mediated access design; never assume database row policies protect service-role storage calls.
- The backend conversation routes reference `public.ai_conversations` and `public.ai_messages`, but those tables were not present in the live public-table inventory. Reconcile this schema/code mismatch before treating conversation authorization as complete. If these tables are added, they need explicit organization + road-department/owner RLS policies, including parent-conversation checks for messages.
- Existing public-table organization policies are permissive. The proposed restrictive policies depend on those baseline policies and must be tested together; a policy review alone is not runtime validation.

## Additional release gates

- [ ] Reconcile every table referenced by backend routes with the live/migration-managed schema, including `ai_conversations` and `ai_messages`.
- [ ] Decide whether document binaries are stored in Supabase Storage. If yes, test authenticated object read/write/delete authorization and ensure object paths cannot be used to bypass document department ACLs. If files remain server-mediated, verify each download endpoint authorizes the parent document before using any service-role client.
- [ ] Add test users and department assignments in a non-production environment without copying sensitive production data.
- [ ] Execute the role and document matrix with each user's own JWT; capture expected and actual HTTP results.
- [ ] Run the Supabase Security Advisor after staging migrations and resolve any newly introduced warnings.


## AI conversation authorization (migration 014)

Use each test user's own authenticated JWT against the Data API and the API endpoints.

| Test identity | Read own conversation/messages | Read another user's conversation | Create conversation | Insert message |
|---|---|---|---|---|
| Organization owner/admin | allowed | allowed within their organization | allowed | allowed only in a conversation they created |
| Road department manager/officer | allowed | denied | allowed | allowed only in own active conversation |
| Road department read-only | allowed | denied | denied | denied |
| Other department only | denied | denied | denied | denied |
| No department role / inactive member | denied | denied | denied | denied |
| User from another organization | denied | denied | denied | denied |

Also verify direct Data API access, not just FastAPI dependency checks. Messages must inherit access from their parent conversation; guessing a conversation UUID must not reveal messages. Confirm read-only users cannot mutate either table and cannot post a user- or assistant-role message directly.

## Migration-history reconciliation (required before apply)

The live Supabase migration history uses timestamp-based versions and currently contains entries through `20261009115736`, while the repository uses numbered SQL filenames (001–014). These are not proven to be a one-to-one mapping. Do not apply files based only on their filename or assume that migrations 011–014 are new to the live database. Compare every repository migration with the live migration history and catalog state, then prepare a timestamped, forward-only deployment plan. No migration in this branch has been applied to production.


## AI conversations and message authorization (migration 014)

The live-schema preflight found that `ai_conversations`, `ai_messages`, and `ai_message_sources` are referenced by backend routes but absent from the live public schema. Migration 014 creates them idempotently and adds restrictive department/ownership policies. Do not apply until tested in staging.

- A road department manager/officer can create and update their own conversations and post messages.
- A road department read-only user can read their own conversation and messages but cannot create a conversation, post a message, or update conversation state.
- A non-admin cannot read another user's conversation or messages, even when both users belong to the same organization.
- An organization owner/admin can read conversations and messages across their organization, and can create their own conversations. Even admins may insert user-role messages only into conversations they created; this prevents them from impersonating another conversation owner. Assistant/system messages remain trusted-backend-only.
- A finance-only, unassigned, inactive, or cross-organization user cannot read road conversations, messages, or message sources.
- A caller cannot attach a message or source to another user's conversation.
- The Data API must reject anonymous access. Authenticated users may SELECT/INSERT/UPDATE conversations subject to RLS, but messages are SELECT/INSERT only (append-only) and `ai_message_sources` is SELECT-only. Trusted backend source insertion is not implemented yet.
- Verify backend behavior: conversation creation and message posting require manager/officer; list and message-read routes permit read_only for the caller's own conversation.

Migration 014 is a source-controlled proposal and has not been applied to production.

- Non-admin road conversation source rows are restricted to `road`, `road_section`, `maintenance_plan`, and `work_order`. `other`, finance, employee, asset, machinery, expense, budget, and document source types must remain unavailable to non-admin users until each type has a matching record-level authorization check.


## Road-section organization integrity (migration 015)

Migration 015 is a source-controlled proposal. It backfills legacy `road_sections.organization_id` from the parent road, makes the field non-null, and adds a trigger that derives the organization from the parent road and rejects cross-organization references. It intentionally aborts if existing orphaned sections or organization mismatches are found; resolve those records in staging rather than silently reassigning them.

Staging checks:
- [ ] Preflight detects and reports orphaned sections, NULL parent organization, or a section/road organization mismatch without modifying rows.
- [ ] A valid section insert with matching organization succeeds for an authorized user.
- [ ] A section insert omitting organization_id derives the parent road's organization before RLS checks.
- [ ] A section insert specifying another organization's ID is rejected.
- [ ] Updating an existing section to reference a road in another organization is rejected.
- [ ] Updating organization_id to a different organization is rejected.
- [ ] Read-only and unauthorized users remain blocked by RLS even when the trigger derives a valid organization.
- [ ] Existing section counts and IDs are unchanged by the backfill; only NULL organization IDs are populated.
- [ ] Confirm trigger behavior with authenticated JWTs because the trigger function is SECURITY DEFINER, uses an empty search_path, and is revoked from API roles for direct execution.

Migration order for a full staging run: 011 (role helper and road RLS), 012 (module RLS), 013 (document ACL), 014 (conversation schema/RLS), 015 (road-section organization integrity). Validate dependencies and existing policies before executing this sequence in any environment.


## Automated catalog regression check

After applying migrations 011-015 to an isolated staging database, run
`database/tests/authorization_catalog_checks.sql` as a database administrator.
It is read-only and verifies that required tables exist, RLS is enabled, authenticated
policies are present, the department-role helper has the intended security modes,
document department classification exists, the road-section integrity trigger exists,
and semantic search remains SECURITY INVOKER.

A successful catalog check is only a structural check. It does not prove the policies
permit or deny the correct rows. Run the JWT/Data API matrix above as well.

## Additional AI message integrity gate

The original implementation inserted both `role='user'` and `role='assistant'` messages
using the caller's user-scoped JWT. That made assistant-message forgery possible unless
both the row policy and table grants prevented it. The feature branch now separates the
write paths and removes authenticated UPDATE/DELETE privileges on messages.

Implemented on the feature branch:
- Direct authenticated inserts into `ai_messages` are restricted to `role='user'`.
- The FastAPI route verifies conversation access with the caller's JWT, saves the user
  message through that JWT client, and persists the assistant response with the
  server-only trusted client.
- If the trusted client is unavailable, the route fails before inserting the user
  message.
- `ai_message_sources` is SELECT-only for authenticated users; clients cannot
  fabricate evidence-source rows.

Automated unit tests cover client separation and missing trusted-client configuration.
Still required in isolated staging: real-JWT Data API tests proving direct assistant and
system inserts fail, legitimate backend assistant persistence succeeds, and a user
cannot read or write another user's conversation. Never expose the service-role key
to the frontend.

The source-type restrictions for non-admin AI evidence are limited to
`road`, `road_section`, `maintenance_plan`, and `work_order`. Other source types
must remain unavailable to non-admin users until record-level authorization is
implemented for them.


## Road-section migration 015 preflight script

Before testing migration 015 in an isolated non-production database, run
`database/tests/road_section_organization_preflight.sql` using a read-only
database role where catalog access permits. It returns:
- a summary count of orphaned sections, sections whose parent road lacks an
  organization, organization mismatches, NULL section organization IDs eligible
  for backfill, and total sections;
- the exact rows that would cause migration 015 to abort; and
- the NULL organization IDs eligible for backfill from a valid parent road.

Expected blockers are zero. Review and record the candidate backfill IDs/count
before applying migration 015, then verify section IDs/counts remain unchanged
and the backfilled rows match their parent roads afterward. The preflight itself
does not update data and is not a substitute for the authenticated-JWT trigger
tests listed above.


## Function execution and excess table privilege checks (migrations 016–017)

Migrations 016–017 are source-controlled proposals only. Validate in isolated staging after the prerequisite migrations and before any production deployment.

### Migration 016 — table grants
- [ ] As an administrator, run `database/tests/authorization_catalog_checks.sql`; confirm authenticated has no TRUNCATE, REFERENCES, or TRIGGER privilege on each protected table.
- [ ] Confirm normal SELECT/INSERT/UPDATE/DELETE grants remain as designed; migration 016 must not be treated as a replacement for RLS.
- [ ] Confirm service-role backend operations still work in the trusted server environment; never use the service-role key in browser tests.

### Migration 017 — function grants and name resolution
- [ ] Confirm `public.has_department_role(uuid,text,text[])` is SECURITY INVOKER with an empty search_path.
- [ ] Confirm `private.has_department_role(uuid,text,text[])` is SECURITY DEFINER with an empty search_path, executable by authenticated only (not anon or service_role).
- [ ] Confirm `public.create_organization_for_current_user(text,text)` is SECURITY DEFINER with an empty search_path and executable by authenticated, but not anon or service_role.
- [ ] Verify organization creation succeeds for a valid authenticated caller and fails for an anonymous caller.
- [ ] Confirm function bodies schema-qualify application tables and remain functional with an empty search_path; built-ins should resolve through pg_catalog.
- [ ] Run the catalog test after the migration sequence, then run authenticated-JWT integration tests. GitHub CI does not execute this SQL catalog script unless a dedicated database test job is configured.

Do not apply migrations 016–017 to production based solely on CI success or catalog review. Record the staging database version, migration order, test identities, and observed outcomes first.
