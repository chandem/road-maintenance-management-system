-- AI-RMMS initial database foundation
-- PostgreSQL / Supabase
-- This migration establishes the core domain model.
-- Authorization policies will be added after the organization/auth model is verified.

create extension if not exists pgcrypto;

create table if not exists organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  code text unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists departments (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  name text not null,
  code text,
  created_at timestamptz not null default now(),
  unique (organization_id, name)
);

create table if not exists user_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  organization_id uuid references organizations(id) on delete set null,
  department_id uuid references departments(id) on delete set null,
  full_name text,
  employee_code text,
  job_title text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists roads (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  road_code text not null,
  name text not null,
  start_location text,
  end_location text,
  total_length_km numeric(12,3),
  road_class text,
  surface_type text,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, road_code)
);

create table if not exists road_sections (
  id uuid primary key default gen_random_uuid(),
  road_id uuid not null references roads(id) on delete cascade,
  section_code text not null,
  start_chainage_km numeric(12,3) not null,
  end_chainage_km numeric(12,3) not null,
  length_km numeric(12,3),
  condition_rating numeric(5,2),
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (road_id, section_code),
  check (end_chainage_km >= start_chainage_km)
);

create table if not exists maintenance_plans (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  name text not null,
  fiscal_year text,
  plan_type text,
  status text not null default 'draft',
  budget_amount numeric(18,2),
  start_date date,
  end_date date,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists work_orders (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  road_section_id uuid references road_sections(id) on delete set null,
  maintenance_plan_id uuid references maintenance_plans(id) on delete set null,
  work_order_no text not null,
  title text not null,
  maintenance_type text,
  priority text,
  status text not null default 'planned',
  planned_cost numeric(18,2),
  actual_cost numeric(18,2),
  planned_start date,
  planned_end date,
  actual_start date,
  actual_end date,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, work_order_no)
);

create table if not exists machinery (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  asset_code text not null,
  name text not null,
  machinery_type text,
  make text,
  model text,
  serial_number text,
  status text not null default 'available',
  purchase_date date,
  purchase_cost numeric(18,2),
  current_hours numeric(14,2),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, asset_code)
);

create table if not exists assets (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  asset_code text not null,
  name text not null,
  category text,
  location text,
  status text not null default 'active',
  acquisition_date date,
  acquisition_cost numeric(18,2),
  current_value numeric(18,2),
  assigned_to uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, asset_code)
);

create table if not exists employees (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  employee_code text not null,
  full_name text not null,
  department_id uuid references departments(id) on delete set null,
  job_title text,
  employment_type text,
  hire_date date,
  status text not null default 'active',
  phone text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, employee_code)
);

create table if not exists budgets (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  fiscal_year text not null,
  budget_code text,
  category text,
  allocated_amount numeric(18,2) not null default 0,
  spent_amount numeric(18,2) not null default 0,
  committed_amount numeric(18,2) not null default 0,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists expenses (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  budget_id uuid references budgets(id) on delete set null,
  work_order_id uuid references work_orders(id) on delete set null,
  expense_date date not null,
  description text not null,
  category text,
  amount numeric(18,2) not null,
  reference_no text,
  status text not null default 'recorded',
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now()
);

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  title text not null,
  document_type text,
  storage_path text,
  mime_type text,
  status text not null default 'uploaded',
  document_date date,
  uploaded_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists ai_analysis_runs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  analysis_type text not null,
  entity_type text,
  entity_id uuid,
  input_reference text,
  status text not null default 'queued',
  confidence numeric(5,4),
  result jsonb,
  evidence jsonb,
  error_message text,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists ai_recommendations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  recommendation_type text not null,
  title text not null,
  description text not null,
  priority text,
  confidence numeric(5,4),
  evidence jsonb,
  status text not null default 'pending',
  reviewed_by uuid references auth.users(id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_roads_org on roads(organization_id);
create index if not exists idx_sections_road on road_sections(road_id);
create index if not exists idx_work_orders_org_status on work_orders(organization_id, status);
create index if not exists idx_machinery_org_status on machinery(organization_id, status);
create index if not exists idx_assets_org_status on assets(organization_id, status);
create index if not exists idx_employees_org_status on employees(organization_id, status);
create index if not exists idx_expenses_org_date on expenses(organization_id, expense_date);
create index if not exists idx_documents_org_status on documents(organization_id, status);
create index if not exists idx_ai_runs_org_status on ai_analysis_runs(organization_id, status);
create index if not exists idx_ai_recommendations_org_status on ai_recommendations(organization_id, status);

-- Security note:
-- RLS policies are intentionally introduced in a later migration after
-- organization membership and authorization functions are finalized.
-- Do not expose these tables through an unprotected Data API in production.
