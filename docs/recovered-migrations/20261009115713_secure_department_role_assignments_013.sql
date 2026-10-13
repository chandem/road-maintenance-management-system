-- RECOVERY ARTIFACT: exact SQL statement recovered from production
-- Supabase project: firzbqzbezuecvplsibi
-- Ledger version: 20261009115713
-- Ledger name: secure_department_role_assignments_013
-- Recovered 2026-10-10 from supabase_migrations.schema_migrations.statements and PostgreSQL logs.
-- Evidence archive only; do not replay against production as part of source recovery.

create index if not exists user_department_roles_user_org_idx on public.user_department_roles (user_id,organization_id,is_active); create index if not exists user_department_roles_department_idx on public.user_department_roles (department_id,is_active); alter table public.user_department_roles enable row level security;
