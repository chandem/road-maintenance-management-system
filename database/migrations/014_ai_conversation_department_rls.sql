-- AI-RMMS conversation storage and department-level database authorization.
-- This is a source-controlled migration proposal. Do not apply to production
-- until the authenticated-JWT staging matrix passes.
--
-- The live database preflight found these tables absent even though the backend
-- routes reference them. Create them here, then layer restrictive RLS on top of
-- any organization-level policies from earlier schema versions.
--
-- Read-only users may read their own conversations/messages, but cannot create
-- conversations, post messages, or update conversation state. Organization
-- owners/admins retain organization-wide access.

CREATE TABLE IF NOT EXISTS public.ai_conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  created_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
  title text,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'archived')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.ai_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES public.ai_conversations(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content text NOT NULL,
  model text,
  confidence numeric(4,3)
    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.ai_message_sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id uuid NOT NULL REFERENCES public.ai_messages(id) ON DELETE CASCADE,
  source_type text NOT NULL CHECK (source_type IN (
    'road', 'road_section', 'maintenance_plan', 'work_order', 'machinery',
    'asset', 'employee', 'budget', 'expense', 'document', 'other'
  )),
  source_id uuid,
  source_label text,
  evidence text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_conversations_org_created
  ON public.ai_conversations (organization_id, created_by, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation_created
  ON public.ai_messages (conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ai_message_sources_message
  ON public.ai_message_sources (message_id);

ALTER TABLE public.ai_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_message_sources ENABLE ROW LEVEL SECURITY;

-- Explicitly grant only the commands required by the API. RLS narrows these
-- table-level grants by organization, conversation ownership, and department.
REVOKE ALL ON public.ai_conversations, public.ai_messages, public.ai_message_sources
  FROM PUBLIC, anon;

-- Reset authenticated grants too, so rerunning this migration on a database
-- with pre-existing tables cannot preserve stale privileges such as TRUNCATE,
-- REFERENCES, TRIGGER, or unexpected writes from an earlier schema version.
REVOKE ALL ON public.ai_conversations, public.ai_messages, public.ai_message_sources
  FROM authenticated;

-- The API never updates conversations with a caller JWT. The trusted backend
-- may update timestamps using service_role; authenticated users need no UPDATE grant.
GRANT SELECT, INSERT ON public.ai_conversations TO authenticated;
GRANT SELECT, INSERT ON public.ai_messages TO authenticated;
GRANT SELECT ON public.ai_message_sources TO authenticated;

-- Keep permissive policies so restrictive policies below can narrow them.
DROP POLICY IF EXISTS ai_conversations_select ON public.ai_conversations;
CREATE POLICY ai_conversations_select
  ON public.ai_conversations FOR SELECT TO authenticated
  USING (private.is_org_member(organization_id));

DROP POLICY IF EXISTS ai_conversations_insert ON public.ai_conversations;
CREATE POLICY ai_conversations_insert
  ON public.ai_conversations FOR INSERT TO authenticated
  WITH CHECK (
    created_by = (SELECT auth.uid())
    AND private.is_org_member(organization_id)
  );

-- Authenticated users have no UPDATE grant on ai_conversations. The trusted
-- backend service role alone updates timestamps; no caller UPDATE policy is needed.

DROP POLICY IF EXISTS ai_messages_select ON public.ai_messages;
CREATE POLICY ai_messages_select
  ON public.ai_messages FOR SELECT TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.ai_conversations c
    WHERE c.id = ai_messages.conversation_id
      AND private.is_org_member(c.organization_id)
  ));

DROP POLICY IF EXISTS ai_messages_insert ON public.ai_messages;
CREATE POLICY ai_messages_insert
  ON public.ai_messages FOR INSERT TO authenticated
  WITH CHECK (EXISTS (
    SELECT 1 FROM public.ai_conversations c
    WHERE c.id = ai_messages.conversation_id
      AND private.is_org_member(c.organization_id)
  ));

DROP POLICY IF EXISTS ai_message_sources_select ON public.ai_message_sources;
CREATE POLICY ai_message_sources_select
  ON public.ai_message_sources FOR SELECT TO authenticated
  USING (EXISTS (
    SELECT 1
    FROM public.ai_messages m
    JOIN public.ai_conversations c ON c.id = m.conversation_id
    WHERE m.id = ai_message_sources.message_id
      AND private.is_org_member(c.organization_id)
  ));

DROP POLICY IF EXISTS ai_message_sources_insert ON public.ai_message_sources;
-- Evidence/source rows are trusted AI output, not user-authored input.
-- Authenticated clients receive no INSERT privilege; the server-side trusted
-- backend may persist validated sources when that feature is implemented.

-- Department + ownership restrictions. Admins can support any conversation in
-- their organization. Non-admins need an active road_asset role and can access
-- only conversations they created. Read-only is SELECT-only.
DROP POLICY IF EXISTS ai_conversations_department_select ON public.ai_conversations;
CREATE POLICY ai_conversations_department_select
  ON public.ai_conversations AS RESTRICTIVE FOR SELECT TO authenticated
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

DROP POLICY IF EXISTS ai_conversations_department_insert ON public.ai_conversations;
CREATE POLICY ai_conversations_department_insert
  ON public.ai_conversations AS RESTRICTIVE FOR INSERT TO authenticated
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

-- Authenticated users have no UPDATE grant on ai_conversations. The trusted
-- backend service role alone updates timestamps; no caller UPDATE policy is needed.

DROP POLICY IF EXISTS ai_messages_department_select ON public.ai_messages;
CREATE POLICY ai_messages_department_select
  ON public.ai_messages AS RESTRICTIVE FOR SELECT TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.ai_conversations c
    WHERE c.id = ai_messages.conversation_id
      AND (
        private.is_org_admin(c.organization_id)
        OR (
          c.created_by = (SELECT auth.uid())
          AND public.has_department_role(
            c.organization_id, 'road_asset',
            ARRAY['department_manager', 'officer', 'read_only']::text[]
          )
        )
      )
  ));

DROP POLICY IF EXISTS ai_messages_department_insert ON public.ai_messages;
CREATE POLICY ai_messages_department_insert
  ON public.ai_messages AS RESTRICTIVE FOR INSERT TO authenticated
  WITH CHECK (
    -- Direct Data API callers may submit only their own user-role messages.
    -- Assistant/system messages are persisted by the trusted backend only.
    role = 'user'
    AND EXISTS (
      SELECT 1 FROM public.ai_conversations c
      WHERE c.id = ai_messages.conversation_id
        AND (
          private.is_org_admin(c.organization_id)
          OR (
            c.created_by = (SELECT auth.uid())
            AND private.is_org_member(c.organization_id)
            AND public.has_department_role(
              c.organization_id, 'road_asset',
              ARRAY['department_manager', 'officer']::text[]
            )
          )
        )
    )
  );

DROP POLICY IF EXISTS ai_message_sources_department_select ON public.ai_message_sources;
CREATE POLICY ai_message_sources_department_select
  ON public.ai_message_sources AS RESTRICTIVE FOR SELECT TO authenticated
  USING (EXISTS (
    SELECT 1
    FROM public.ai_messages m
    JOIN public.ai_conversations c ON c.id = m.conversation_id
    WHERE m.id = ai_message_sources.message_id
      AND (
        private.is_org_admin(c.organization_id)
        OR (
          c.created_by = (SELECT auth.uid())
          AND ai_message_sources.source_type IN (
            'road', 'road_section', 'maintenance_plan', 'work_order'
          )
          AND public.has_department_role(
            c.organization_id, 'road_asset',
            ARRAY['department_manager', 'officer', 'read_only']::text[]
          )
        )
      )
  ));

DROP POLICY IF EXISTS ai_message_sources_department_insert ON public.ai_message_sources;
-- No authenticated INSERT policy is created: source rows must come from the
-- trusted backend after it validates the referenced road-maintenance records.

-- Do not grant DELETE through this migration. Verify existing table grants in
-- staging; RLS policies above intentionally define no DELETE path.
