# Production apply runbook — department RLS proposals

**Owner authorization recorded:** 2026-10-11 (chat request: “Apply to production”).  
**Branch:** `feature/department-role-management`  
**Executor:** Human operator in the AI-RMMS Supabase project (this agent cannot open your production database).

---

## Critical rules

1. **Do not** re-run anything under `docs/recovered-migrations/`.
2. **Do not** apply `010_department_role_foundation.sql` to production (role foundation already live via ledger `011`–`015`).
3. **Do not** use repository filenames `011_`…`018_` as Supabase migration **version names** if they collide with history — use the **new timestamps below**.
4. Apply **only** these eight proposal bodies, in order, as **new** ledger versions after tip `20261009115736` (re-check tip first).
5. Take a backup / confirm PITR before step 1.

---

## Pre-flight (5 minutes, SQL editor, read-only)

```sql
-- 1) Ledger tip
SELECT version, name, inserted_at
FROM supabase_migrations.schema_migrations
ORDER BY version DESC
LIMIT 15;

-- 2) Helper shape
SELECT n.nspname, p.proname, p.prosecdef, p.proconfig
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE p.proname = 'has_department_role';

-- 3) Gaps these proposals close
SELECT EXISTS (
  SELECT 1 FROM information_schema.columns
  WHERE table_schema = 'public' AND table_name = 'documents' AND column_name = 'department_code'
) AS has_department_code;

SELECT to_regclass('public.ai_conversations') AS ai_conversations,
       to_regclass('public.ai_messages') AS ai_messages,
       to_regclass('public.ai_message_sources') AS ai_message_sources;
```

**Expected before apply:** tip ≥ `20261009115736`; `has_department_role` in `public` DEFINER; `department_code` false; AI conversation tables null.

If the tip is **newer** than `20261009115736`, stop and reconcile — do not assume the sequence below is still first.

---

## Apply order (new production versions)

Copy each file’s SQL from the branch path, run in the Supabase SQL editor **one file at a time**, then record the version in your ops log (or use Supabase CLI migration with these version ids).

| Order | New version id | Source file on branch |
|------:|----------------|------------------------|
| 1 | `20261011140001` | `database/migrations/011_department_road_rls.sql` |
| 2 | `20261011140002` | `database/migrations/012_department_module_rls.sql` |
| 3 | `20261011140003` | `database/migrations/013_department_aware_document_access.sql` |
| 4 | `20261011140004` | `database/migrations/014_ai_conversation_department_rls.sql` |
| 5 | `20261011140005` | `database/migrations/015_road_section_organization_integrity.sql` |
| 6 | `20261011140006` | `database/migrations/016_revoke_excess_authenticated_table_privileges.sql` |
| 7 | `20261011140007` | `database/migrations/017_harden_function_execution_privileges.sql` |
| 8 | `20261011140008` | `database/migrations/018_profile_and_role_privilege_hardening.sql` |

Suggested names when inserting into `schema_migrations` (if your process records them):

- `department_road_rls_prod`
- `department_module_rls_prod`
- `department_aware_document_access_prod`
- `ai_conversation_department_rls_prod`
- `road_section_organization_integrity_prod`
- `revoke_excess_authenticated_table_privileges_prod`
- `harden_function_execution_privileges_prod`
- `profile_and_role_privilege_hardening_prod`

If the SQL editor does not auto-record migrations, after each successful apply:

```sql
INSERT INTO supabase_migrations.schema_migrations (version, name, statements)
VALUES (
  '20261011140001',  -- change per step
  'department_road_rls_prod',
  ARRAY['<<optional: store statement text or omit per your process>>']
);
```

(Only if that matches how your project already records history — some teams rely solely on the CLI.)

---

## After each step — quick check

**After 1 (011):**

```sql
SELECT n.nspname, p.proname, p.prosecdef
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE p.proname = 'has_department_role';
-- Expect private DEFINER body + public INVOKER wrapper
```

**After 3 (013):**

```sql
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'documents' AND column_name = 'department_code';
```

**After 4 (014):**

```sql
SELECT to_regclass('public.ai_conversations'),
       to_regclass('public.ai_messages'),
       to_regclass('public.ai_message_sources');
```

**After 7–8:** create a test org via the real onboarding RPC from an authenticated user session (frontend or Data API) — must still succeed.

---

## Post-apply product smoke

1. Org admin: read roads / executive dashboard  
2. Road manager JWT: read/create road; cannot see other org  
3. Read-only road role: read roads; cannot insert  
4. Finance role: no road-asset rows  
5. Document upload with `department_code`  
6. Office assistant + ranking still respond  

---

## Rollback posture

- Prefer **PITR** to pre-apply recovery point if a step fails mid-way.  
- Do not “undo” by replaying recovered ledger SQL.  
- If only 011 applied and PostgREST breaks on `has_department_role`, restore from backup rather than inventing ad-hoc fixes under pressure.

---

## What this agent cannot do

- Connect to project `firzbqzbezuecvplsibi` or any production URL  
- Run the SQL editor for you  
- Hold or use your service-role key  

You (or an operator with Supabase dashboard/CLI access) must execute the eight steps above.

---

## Status after this doc

| Item | Status |
|------|--------|
| Owner asked to apply to production | Yes (2026-10-11) |
| Production SQL executed by agent | **No** |
| Operator runbook ready | Yes |
| PR #1 merged | No (still draft unless you merge separately) |
