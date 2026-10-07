-- AI-RMMS authorization foundation
-- Organization membership is isolated from business-table policies to avoid
-- recursive RLS evaluation.

create schema if not exists private;

create table if not exists organization_members (
  organization_id uuid not null references organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'member',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  primary key (organization_id, user_id)
);

create index if not exists idx_org_members_user
  on organization_members(user_id);

create index if not exists idx_user_profiles_org
  on user_profiles(organization_id);

-- Road sections receive their tenant key directly so RLS does not need to
-- join through roads, which keeps authorization simple and non-recursive.
alter table road_sections
  add column if not exists organization_id uuid references organizations(id) on delete cascade;

update road_sections rs
set organization_id = r.organization_id
from roads r
where rs.road_id = r.id
  and rs.organization_id is null;

create index if not exists idx_sections_org
  on road_sections(organization_id);

create or replace function private.is_org_member(p_org_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.organization_members om
    where om.organization_id = p_org_id
      and om.user_id = (select auth.uid())
      and om.is_active = true
  );
$$;

create or replace function private.is_org_admin(p_org_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.organization_members om
    where om.organization_id = p_org_id
      and om.user_id = (select auth.uid())
      and om.is_active = true
      and om.role in ('owner', 'admin')
  );
$$;

revoke execute on function private.is_org_member(uuid) from public;
revoke execute on function private.is_org_admin(uuid) from public;
grant usage on schema private to authenticated;
grant execute on function private.is_org_member(uuid) to authenticated;
grant execute on function private.is_org_admin(uuid) to authenticated;

-- Enable RLS on every current public business table.
alter table organizations enable row level security;
alter table departments enable row level security;
alter table user_profiles enable row level security;
alter table organization_members enable row level security;
alter table roads enable row level security;
alter table road_sections enable row level security;
alter table maintenance_plans enable row level security;
alter table work_orders enable row level security;
alter table machinery enable row level security;
alter table assets enable row level security;
alter table employees enable row level security;
alter table budgets enable row level security;
alter table expenses enable row level security;
alter table documents enable row level security;
alter table ai_analysis_runs enable row level security;
alter table ai_recommendations enable row level security;

-- Restrict Data API roles; policies below provide authenticated access.
revoke all on organizations, departments, user_profiles, organization_members,
  roads, road_sections, maintenance_plans, work_orders, machinery, assets,
  employees, budgets, expenses, documents, ai_analysis_runs, ai_recommendations
from anon;

grant select, insert, update, delete on organizations, departments, user_profiles,
  organization_members, roads, road_sections, maintenance_plans, work_orders,
  machinery, assets, employees, budgets, expenses, documents, ai_analysis_runs,
  ai_recommendations to authenticated;

-- Organization membership: membership rows are visible to members.
create policy "org members can view membership"
on organization_members for select
to authenticated
using ((select private.is_org_member(organization_id)));

create policy "org admins can manage membership"
on organization_members for all
to authenticated
using ((select private.is_org_admin(organization_id)))
with check ((select private.is_org_admin(organization_id)));

-- Organization record: members can read; owners/admins can manage.
create policy "members can view organizations"
on organizations for select
to authenticated
using ((select private.is_org_member(id)));

create policy "admins can manage organizations"
on organizations for update
to authenticated
using ((select private.is_org_admin(id)))
with check ((select private.is_org_admin(id)));

-- Department data.
create policy "members can view departments"
on departments for select
to authenticated
using ((select private.is_org_member(organization_id)));

create policy "admins can manage departments"
on departments for all
to authenticated
using ((select private.is_org_admin(organization_id)))
with check ((select private.is_org_admin(organization_id)));

-- User profiles are organization-scoped.
create policy "members can view profiles"
on user_profiles for select
to authenticated
using (
  id = (select auth.uid())
  or (organization_id is not null and (select private.is_org_member(organization_id)))
);

create policy "users can create own profile"
on user_profiles for insert
to authenticated
with check (id = (select auth.uid()));

create policy "users can update own profile"
on user_profiles for update
to authenticated
using (id = (select auth.uid()))
with check (id = (select auth.uid()));

-- Business-domain tables use the same non-recursive organization check.
create policy "members access roads"
on roads for all
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

create policy "members access road sections"
on road_sections for all
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

create policy "members access maintenance plans"
on maintenance_plans for all
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

create policy "members access work orders"
on work_orders for all
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

create policy "members access machinery"
on machinery for all
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

create policy "members access assets"
on assets for all
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

create policy "members access employees"
on employees for all
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

create policy "members access budgets"
on budgets for all
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

create policy "members access expenses"
on expenses for all
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

create policy "members access documents"
on documents for all
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

create policy "members access ai analysis"
on ai_analysis_runs for all
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

create policy "members access ai recommendations"
on ai_recommendations for all
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

-- Seeded memberships must be created by an administrative onboarding flow.
-- No self-service organization creation is exposed by these policies.
