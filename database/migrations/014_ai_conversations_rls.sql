-- AI conversation persistence with department-scoped database authorization.
-- Source-controlled proposal only. Do not apply to production until migration
-- history is reconciled and the JWT-based RLS matrix passes in non-production.
--
-- The backend uses these exact table names. Read-only users may read their own
-- conversations/messages but cannot create conversations or post messages.

CREATE TABLE IF NOT EXISTS public.ai_conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  created_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title text,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'archived', 'closed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.ai_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES public.ai_conversations(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'assistant')),
  content text NOT NULL CHECK (length(content) <= 20000),
  model text,
  confidence double precision,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_conversations_org_creator_updated
  ON public.ai_conversations (organization_id, created_by, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation_created
  ON public.ai_messages (conversation_id, created_at);

ALTER TABLE public.ai_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_messages ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.ai_conversations FROM anon, PUBLIC;
REVOKE ALL ON TABLE public.ai_messages FROM anon, PUBLIC;
GRANT SELECT, INSERT, UPDATE ON TABLE public.ai_conversations TO authenticated;
GRANT SELECT, INSERT ON TABLE public.ai_messages TO authenticated;

DROP POLICY IF EXISTS ai_conversations_select_scoped ON public.ai_conversations;
CREATE POLICY ai_conversations_select_scoped
  ON public.ai_conversations FOR SELECT TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR (
      created_by = (SELECT auth.uid())
      AND public.has_department_role(
        organization_id, 'road_asset',
        ARRAY['department_manager', 'officer', 'read_only']::text[]
      )
    )
  );

DROP POLICY IF EXISTS ai_conversations_insert_writer ON public.ai_conversations;
CREATE POLICY ai_conversations_insert_writer
  ON public.ai_conversations FOR INSERT TO authenticated
  WITH CHECK (
    created_by = (SELECT auth.uid())
    AND (
      private.is_org_admin(organization_id)
      OR public.has_department_role(
        organization_id, 'road_asset',
        ARRAY['department_manager', 'officer']::text[]
      )
    )
  );

DROP POLICY IF EXISTS ai_conversations_update_writer ON public.ai_conversations;
CREATE POLICY ai_conversations_update_writer
  ON public.ai_conversations FOR UPDATE TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR (
      created_by = (SELECT auth.uid())
      AND public.has_department_role(
        organization_id, 'road_asset',
        ARRAY['department_manager', 'officer']::text[]
      )
    )
  )
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR (
      created_by = (SELECT auth.uid())
      AND public.has_department_role(
        organization_id, 'road_asset',
        ARRAY['department_manager', 'officer']::text[]
      )
    )
  );

-- Messages inherit organization and department authorization from their parent
-- conversation. The parent must be visible to the caller under its own RLS.
DROP POLICY IF EXISTS ai_messages_select_parent_scope ON public.ai_messages;
CREATE POLICY ai_messages_select_parent_scope
  ON public.ai_messages FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.ai_conversations c
      WHERE c.id = ai_messages.conversation_id
    )
  );

DROP POLICY IF EXISTS ai_messages_insert_parent_writer ON public.ai_messages;
CREATE POLICY ai_messages_insert_parent_writer
  ON public.ai_messages FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.ai_conversations c
      WHERE c.id = ai_messages.conversation_id
        AND c.status = 'active'
        AND (
          private.is_org_admin(c.organization_id)
          OR (
            c.created_by = (SELECT auth.uid())
            AND public.has_department_role(
              c.organization_id, 'road_asset',
              ARRAY['department_manager', 'officer']::text[]
            )
          )
        )
    )
  );

COMMENT ON TABLE public.ai_conversations IS
  'AI-RMMS conversations; row access is limited by organization admin or road_asset department role and creator ownership.';
COMMENT ON TABLE public.ai_messages IS
  'AI-RMMS messages; row access inherits authorization from the parent conversation.';
