-- AI-RMMS AI Office Assistant foundation
-- Conversations and messages are organization-scoped.
-- AI responses should reference verified source records when available.

create table if not exists public.ai_conversations (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references public.organizations(id) on delete cascade,
    created_by uuid not null references auth.users(id) on delete restrict,
    title text,
    status text not null default 'active'
        check (status in ('active', 'archived')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.ai_messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.ai_conversations(id) on delete cascade,
    role text not null
        check (role in ('user', 'assistant', 'system')),
    content text not null,
    model text,
    confidence numeric(4,3)
        check (confidence is null or (confidence >= 0 and confidence <= 1)),
    created_at timestamptz not null default now()
);

create table if not exists public.ai_message_sources (
    id uuid primary key default gen_random_uuid(),
    message_id uuid not null references public.ai_messages(id) on delete cascade,
    source_type text not null
        check (source_type in (
            'road',
            'road_section',
            'maintenance_plan',
            'work_order',
            'machinery',
            'asset',
            'employee',
            'budget',
            'expense',
            'document',
            'other'
        )),
    source_id uuid,
    source_label text,
    evidence text,
    created_at timestamptz not null default now()
);

create index if not exists idx_ai_conversations_org
    on public.ai_conversations(organization_id);

create index if not exists idx_ai_conversations_created_by
    on public.ai_conversations(created_by);

create index if not exists idx_ai_messages_conversation
    on public.ai_messages(conversation_id, created_at);

create index if not exists idx_ai_message_sources_message
    on public.ai_message_sources(message_id);

alter table public.ai_conversations enable row level security;
alter table public.ai_messages enable row level security;
alter table public.ai_message_sources enable row level security;

drop policy if exists ai_conversations_select on public.ai_conversations;
create policy ai_conversations_select
on public.ai_conversations
for select
to authenticated
using (private.is_org_member(organization_id));

drop policy if exists ai_conversations_insert on public.ai_conversations;
create policy ai_conversations_insert
on public.ai_conversations
for insert
to authenticated
with check (
    created_by = auth.uid()
    and private.is_org_member(organization_id)
);

drop policy if exists ai_conversations_update on public.ai_conversations;
create policy ai_conversations_update
on public.ai_conversations
for update
to authenticated
using (private.is_org_member(organization_id))
with check (private.is_org_member(organization_id));

drop policy if exists ai_messages_select on public.ai_messages;
create policy ai_messages_select
on public.ai_messages
for select
to authenticated
using (
    exists (
        select 1
        from public.ai_conversations c
        where c.id = ai_messages.conversation_id
          and private.is_org_member(c.organization_id)
    )
);

drop policy if exists ai_messages_insert on public.ai_messages;
create policy ai_messages_insert
on public.ai_messages
for insert
to authenticated
with check (
    exists (
        select 1
        from public.ai_conversations c
        where c.id = ai_messages.conversation_id
          and private.is_org_member(c.organization_id)
    )
);

drop policy if exists ai_message_sources_select on public.ai_message_sources;
create policy ai_message_sources_select
on public.ai_message_sources
for select
to authenticated
using (
    exists (
        select 1
        from public.ai_messages m
        join public.ai_conversations c on c.id = m.conversation_id
        where m.id = ai_message_sources.message_id
          and private.is_org_member(c.organization_id)
    )
);

drop policy if exists ai_message_sources_insert on public.ai_message_sources;
create policy ai_message_sources_insert
on public.ai_message_sources
for insert
to authenticated
with check (
    exists (
        select 1
        from public.ai_messages m
        join public.ai_conversations c on c.id = m.conversation_id
        where m.id = ai_message_sources.message_id
          and private.is_org_member(c.organization_id)
    )
);
