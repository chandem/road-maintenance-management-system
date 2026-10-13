-- RECOVERY ARTIFACT: exact SQL statement recovered from production
-- Supabase project: firzbqzbezuecvplsibi
-- Ledger version: 20261009115706
-- Ledger name: create_department_role_assignments_012
-- Recovered 2026-10-10 from supabase_migrations.schema_migrations.statements and PostgreSQL logs.
-- Evidence archive only; do not replay against production as part of source recovery.

create table public.user_department_roles (id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.organizations(id) on delete cascade, user_id uuid not null references auth.users(id) on delete cascade, department_id uuid not null references public.departments(id) on delete cascade, role text not null default 'officer' check (role in ('department_manager','officer','read_only')), is_active boolean not null default true, assigned_by uuid references auth.users(id) on delete set null, created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique (organization_id,user_id,department_id));
