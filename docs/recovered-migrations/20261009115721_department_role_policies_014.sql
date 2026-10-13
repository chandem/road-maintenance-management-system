-- RECOVERY ARTIFACT: exact SQL statement recovered from production
-- Supabase project: firzbqzbezuecvplsibi
-- Ledger version: 20261009115721
-- Ledger name: department_role_policies_014
-- Recovered 2026-10-10 from supabase_migrations.schema_migrations.statements and PostgreSQL logs.
-- Evidence archive only; do not replay against production as part of source recovery.

create policy users_can_view_own_department_roles on public.user_department_roles for select to authenticated using (user_id = (select auth.uid()) or private.is_org_admin(organization_id)); create policy org_admins_manage_department_roles on public.user_department_roles for all to authenticated using (private.is_org_admin(organization_id)) with check (private.is_org_admin(organization_id) and exists (select 1 from public.departments d where d.id = department_id and d.organization_id = user_department_roles.organization_id) and exists (select 1 from public.organization_members om where om.organization_id = user_department_roles.organization_id and om.user_id = user_department_roles.user_id and om.is_active = true));
