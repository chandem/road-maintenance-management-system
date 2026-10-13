-- RECOVERY ARTIFACT: exact SQL statement recovered from production
-- Supabase project: firzbqzbezuecvplsibi
-- Ledger version: 20261009115651
-- Ledger name: seed_core_departments_011
-- Recovered 2026-10-10 from supabase_migrations.schema_migrations.statements and PostgreSQL logs.
-- Evidence archive only; do not replay against production as part of source recovery.

create unique index if not exists departments_org_code_unique on public.departments (organization_id, code) where code is not null; insert into public.departments (organization_id, name, code) select o.id, v.name, v.code from public.organizations o cross join (values ('Road Asset Management','road_asset'),('Machinery Maintenance Management','machinery_maintenance'),('Finance','finance'),('Human Resources','human_resources'),('General Asset Management','general_assets')) as v(name,code) where o.code='GRMB' on conflict (organization_id, code) where code is not null do update set name=excluded.name;
