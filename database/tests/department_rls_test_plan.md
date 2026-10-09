# Department-level RLS verification plan

Do not apply `011_department_road_rls.sql` to production until the checks below pass in a staging project.

## Preconditions

1. Use a staging Supabase project with the same schema/migrations as production.
2. Create or identify four real Auth users in one test organization:
   - organization owner/admin;
   - road_asset department_manager;
   - road_asset read_only user;
   - user assigned only to finance (or no department role).
3. Assign the roles through the admin API or authenticated admin UI. The target user must be an active organization member.
4. Confirm the active assignments:
   ```sql
   select om.user_id, om.role as organization_role, d.code as department_code,
          udr.role as department_role, udr.is_active
   from public.organization_members om
   left join public.user_department_roles udr
     on udr.organization_id = om.organization_id
    and udr.user_id = om.user_id
    and udr.is_active = true
   left join public.departments d
     on d.id = udr.department_id
    and d.organization_id = udr.organization_id
   where om.organization_id = '<STAGING_ORG_UUID>'::uuid
     and om.is_active = true;
   ```

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

For a denied SELECT, PostgREST may return HTTP 200 with an empty array because RLS filters rows; assert that no protected rows are returned, not just the HTTP status. For INSERT/UPDATE, assert no row is created/changed and inspect the response/error. Use a seeded test road owned by the staging organization.

## Additional checks

- Repeat GET/PATCH against `road_sections` and GET/INSERT/PATCH against `road_inspections`.
- Attempt to change a row's `organization_id` to another organization; it must fail.
- Call `/rest/v1/rpc/has_department_role` without a token; it must be rejected after the migration revokes anonymous execution.
- Confirm an authenticated caller can only learn the boolean for their own user because the helper binds authorization to `auth.uid()`.
- Confirm the backend endpoints enforce the same role matrix as the database policies.
- Run the Supabase Security Advisor after applying to staging and review remaining SECURITY DEFINER warnings individually.

## Current project state

The live tables `roads`, `road_sections`, and `road_inspections` currently have zero rows, and there are zero active department-role assignments. Applying the restrictive policies before assigning and verifying intended roles would deny normal users access. No production policy changes should be made until test users are assigned and the staging matrix passes.


## Function exposure verification after migration (staging only)

Run this read-only catalog query after applying the migration to staging. Expected:
- `public.has_department_role` exists and is **not** SECURITY DEFINER (it is the RPC wrapper).
- `private.has_department_role` exists and is SECURITY DEFINER.
- The private helper has EXECUTE for `authenticated` and `service_role`, but not `anon` or `PUBLIC`.

```sql
select n.nspname as schema_name,
       p.proname,
       p.prosecdef as security_definer,
       pg_get_function_identity_arguments(p.oid) as arguments,
       coalesce(array_to_string(p.proacl, ', '), '(default privileges)') as grants
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where p.proname = 'has_department_role'
order by n.nspname;
```

Then call `/rest/v1/rpc/has_department_role` with an authenticated test user's JWT and confirm it returns only the caller's own role membership result. An unauthenticated call must be rejected. Re-run Supabase Security Advisor; the exposed-schema SECURITY DEFINER warning for this helper should be gone.
