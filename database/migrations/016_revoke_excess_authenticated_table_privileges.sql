-- Remove table privileges that bypass row-level security or are not needed
-- by normal authenticated Data API clients.
-- Source-controlled proposal only: review and test in isolated staging before
-- applying to any production database.
--
-- RLS does not apply to TRUNCATE. REFERENCES and TRIGGER are also unnecessary
-- for ordinary application users. Existing SELECT/INSERT/UPDATE/DELETE grants
-- remain unchanged and continue to be narrowed by the RLS policies in 011-015.
--
-- Include all relations found in the read-only production privilege audit,
-- not only the business tables covered by department-aware RLS. The AI
-- conversation relations are created by migration 014 before this migration.
REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLE
  public.roads,
  public.road_sections,
  public.road_inspections,
  public.materials,
  public.maintenance_plans,
  public.work_orders,
  public.machinery,
  public.assets,
  public.budgets,
  public.expenses,
  public.employees,
  public.documents,
  public.document_chunks,
  public.ai_analysis_runs,
  public.ai_recommendations,
  public.ai_conversations,
  public.ai_messages,
  public.ai_message_sources,
  public.departments,
  public.organization_members,
  public.organizations,
  public.user_department_roles,
  public.user_profiles
FROM PUBLIC, anon, authenticated;
