-- Maintenance plan activity-level scope, quantities, and cost tracking.
-- Apply through the approved Supabase migration workflow; do not run from app startup.

create table if not exists public.maintenance_plan_activities (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  maintenance_plan_id uuid not null references public.maintenance_plans(id) on delete cascade,
  road_section_id uuid references public.road_sections(id) on delete restrict,
  activity_name text not null check (length(trim(activity_name)) between 1 and 255),
  description text,
  unit text not null check (length(trim(unit)) between 1 and 40),
  planned_quantity numeric(16,3) not null check (planned_quantity >= 0),
  unit_rate numeric(16,2) not null check (unit_rate >= 0),
  planned_cost numeric(18,2) generated always as (round(planned_quantity * unit_rate, 2)) stored,
  actual_quantity numeric(16,3) check (actual_quantity is null or actual_quantity >= 0),
  actual_cost numeric(18,2) check (actual_cost is null or actual_cost >= 0),
  status text not null default 'planned'
    check (status in ('planned', 'in_progress', 'completed', 'cancelled')),
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists maintenance_plan_activities_org_plan_idx
  on public.maintenance_plan_activities (organization_id, maintenance_plan_id);
create index if not exists maintenance_plan_activities_section_idx
  on public.maintenance_plan_activities (organization_id, road_section_id);

alter table public.maintenance_plan_activities enable row level security;

drop policy if exists maintenance_plan_activities_select on public.maintenance_plan_activities;
create policy maintenance_plan_activities_select
  on public.maintenance_plan_activities for select
  using (
    private.is_org_admin(organization_id)
    or has_department_role(organization_id, 'road_asset', array['department_manager','officer','read_only'])
  );

drop policy if exists maintenance_plan_activities_insert on public.maintenance_plan_activities;
create policy maintenance_plan_activities_insert
  on public.maintenance_plan_activities for insert
  with check (
    private.is_org_admin(organization_id)
    or has_department_role(organization_id, 'road_asset', array['department_manager','officer'])
  );

drop policy if exists maintenance_plan_activities_update on public.maintenance_plan_activities;
create policy maintenance_plan_activities_update
  on public.maintenance_plan_activities for update
  using (
    private.is_org_admin(organization_id)
    or has_department_role(organization_id, 'road_asset', array['department_manager','officer'])
  )
  with check (
    private.is_org_admin(organization_id)
    or has_department_role(organization_id, 'road_asset', array['department_manager','officer'])
  );

drop policy if exists maintenance_plan_activities_delete on public.maintenance_plan_activities;
create policy maintenance_plan_activities_delete
  on public.maintenance_plan_activities for delete
  using (
    private.is_org_admin(organization_id)
    or has_department_role(organization_id, 'road_asset', array['department_manager','officer'])
  );

comment on table public.maintenance_plan_activities is
  'Activity-level scope, quantities, estimated unit costs, and execution tracking for road maintenance plans.';
