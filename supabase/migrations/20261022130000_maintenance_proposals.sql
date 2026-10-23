-- Separate formal maintenance proposals from planning allowances.
create table if not exists public.maintenance_proposals (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  maintenance_plan_id uuid not null references public.maintenance_plans(id) on delete restrict,
  road_section_id uuid references public.road_sections(id) on delete restrict,
  title text not null check (length(trim(title)) between 1 and 255),
  work_scope text not null check (length(trim(work_scope)) between 1 and 8000),
  boq_items jsonb not null default '[]'::jsonb check (jsonb_typeof(boq_items) = 'array'),
  evidence_notes text,
  status text not null default 'draft'
    check (status in ('draft','submitted','under_review','approved','rejected','revision_required')),
  review_notes text,
  submitted_by uuid references auth.users(id) on delete set null,
  reviewed_by uuid references auth.users(id) on delete set null,
  submitted_at timestamptz,
  reviewed_at timestamptz,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists maintenance_proposals_org_created_idx
  on public.maintenance_proposals (organization_id, created_at desc);
create index if not exists maintenance_proposals_plan_idx
  on public.maintenance_proposals (organization_id, maintenance_plan_id);
alter table public.maintenance_proposals enable row level security;
drop policy if exists maintenance_proposals_select on public.maintenance_proposals;
create policy maintenance_proposals_select on public.maintenance_proposals for select
using (private.is_org_admin(organization_id) or has_department_role(organization_id, 'road_asset', array['department_manager','officer','read_only']));
drop policy if exists maintenance_proposals_insert on public.maintenance_proposals;
create policy maintenance_proposals_insert on public.maintenance_proposals for insert
with check (private.is_org_admin(organization_id) or has_department_role(organization_id, 'road_asset', array['department_manager','officer']));
drop policy if exists maintenance_proposals_update on public.maintenance_proposals;
create policy maintenance_proposals_update on public.maintenance_proposals for update
using (private.is_org_admin(organization_id) or has_department_role(organization_id, 'road_asset', array['department_manager','officer']))
with check (private.is_org_admin(organization_id) or has_department_role(organization_id, 'road_asset', array['department_manager','officer']));
comment on table public.maintenance_proposals is 'Formal, reviewable maintenance proposal linked to a saved maintenance plan, with BOQ and evidence; approval does not authorize expenditure.';
