-- AI-RMMS materials inventory for maintenance operations
-- Apply in Supabase SQL editor after 008_secure_semantic_search.sql

create table if not exists materials (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  material_code text not null,
  name text not null,
  category text,
  unit text not null default 'unit',
  quantity_on_hand numeric(18,3) not null default 0,
  reorder_level numeric(18,3),
  unit_cost numeric(18,2),
  location text,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, material_code),
  check (quantity_on_hand >= 0)
);

create index if not exists idx_materials_org_status on materials(organization_id, status);
create index if not exists idx_materials_org_category on materials(organization_id, category);

alter table materials enable row level security;

-- Read: org members
drop policy if exists materials_select_member on materials;
create policy materials_select_member on materials
  for select to authenticated
  using (
    organization_id in (
      select organization_id from user_profiles where id = auth.uid()
    )
  );

-- Insert: org members
drop policy if exists materials_insert_member on materials;
create policy materials_insert_member on materials
  for insert to authenticated
  with check (
    organization_id in (
      select organization_id from user_profiles where id = auth.uid()
    )
  );

-- Update: org members
drop policy if exists materials_update_member on materials;
create policy materials_update_member on materials
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

-- Delete: org members (optional; keep soft-delete via status preferred)
drop policy if exists materials_delete_member on materials;
create policy materials_delete_member on materials
  for delete to authenticated
  using (
    organization_id in (
      select organization_id from user_profiles where id = auth.uid()
    )
  );
