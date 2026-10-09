-- AI-RMMS road inspections / condition history
-- Apply after 009_materials.sql

create table if not exists road_inspections (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  road_section_id uuid not null references road_sections(id) on delete cascade,
  inspection_date date not null,
  inspector_name text,
  condition_rating numeric(5,2),
  surface_condition text,
  defects_summary text,
  recommended_action text,
  weather_notes text,
  status text not null default 'recorded',
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (condition_rating is null or (condition_rating >= 0 and condition_rating <= 5))
);

create index if not exists idx_inspections_org_date
  on road_inspections(organization_id, inspection_date desc);
create index if not exists idx_inspections_section
  on road_inspections(road_section_id, inspection_date desc);

alter table road_inspections enable row level security;

drop policy if exists road_inspections_select_member on road_inspections;
create policy road_inspections_select_member on road_inspections
  for select to authenticated
  using (
    organization_id in (
      select organization_id from user_profiles where id = auth.uid()
    )
  );

drop policy if exists road_inspections_insert_member on road_inspections;
create policy road_inspections_insert_member on road_inspections
  for insert to authenticated
  with check (
    organization_id in (
      select organization_id from user_profiles where id = auth.uid()
    )
  );

drop policy if exists road_inspections_update_member on road_inspections;
create policy road_inspections_update_member on road_inspections
  for update to authenticated
  using (
    organization_id in (
      select organization_id from user_profiles where id = auth.uid()
    )
  )
  with check (
    organization_id in (
      select organization_id from user_profiles where id = auth.uid()
    )
  );

drop policy if exists road_inspections_delete_member on road_inspections;
create policy road_inspections_delete_member on road_inspections
  for delete to authenticated
  using (
    organization_id in (
      select organization_id from user_profiles where id = auth.uid()
    )
  );
