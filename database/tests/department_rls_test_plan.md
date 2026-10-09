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
