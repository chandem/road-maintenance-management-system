-- RECOVERY ARTIFACT: exact SQL statement recovered from production
-- Supabase project: firzbqzbezuecvplsibi
-- Ledger version: 20261009115736
-- Ledger name: department_access_helper_015
-- Recovered 2026-10-10 from supabase_migrations.schema_migrations.statements and PostgreSQL logs.
-- Evidence archive only; do not replay against production as part of source recovery.

create or replace function public.has_department_role(p_organization_id uuid, p_department_code text, p_allowed_roles text[] default null) returns boolean language sql stable security definer set search_path = '' as $function$ select exists (select 1 from public.user_department_roles udr join public.departments d on d.id = udr.department_id and d.organization_id = udr.organization_id join public.organization_members om on om.organization_id = udr.organization_id and om.user_id = udr.user_id and om.is_active = true where udr.organization_id = p_organization_id and udr.user_id = (select auth.uid()) and udr.is_active = true and d.code = p_department_code and (p_allowed_roles is null or udr.role = any(p_allowed_roles))); $function$; revoke all on function public.has_department_role(uuid,text,text[]) from public; grant execute on function public.has_department_role(uuid,text,text[]) to authenticated;
