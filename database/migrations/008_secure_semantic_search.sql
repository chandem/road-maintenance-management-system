-- AI-RMMS Step 1 hardening: secure semantic search
-- 1) Enforce organization membership inside match_document_chunks
-- 2) Allow org members to insert/update/delete their document_chunks (ingestion)
-- 3) Keep anon locked out; authenticated only via membership checks

-- ---------------------------------------------------------------------------
-- RLS policies for document_chunks write path (ingestion pipeline)
-- ---------------------------------------------------------------------------

drop policy if exists "members access document chunks" on document_chunks;
drop policy if exists "members select document chunks" on document_chunks;
drop policy if exists "members insert document chunks" on document_chunks;
drop policy if exists "members update document chunks" on document_chunks;
drop policy if exists "members delete document chunks" on document_chunks;

alter table document_chunks enable row level security;

revoke all on document_chunks from anon;

grant select, insert, update, delete on document_chunks to authenticated;

create policy "members select document chunks"
on document_chunks for select
to authenticated
using ((select private.is_org_member(organization_id)));

create policy "members insert document chunks"
on document_chunks for insert
to authenticated
with check ((select private.is_org_member(organization_id)));

create policy "members update document chunks"
on document_chunks for update
to authenticated
using ((select private.is_org_member(organization_id)))
with check ((select private.is_org_member(organization_id)));

create policy "members delete document chunks"
on document_chunks for delete
to authenticated
using ((select private.is_org_member(organization_id)));

-- ---------------------------------------------------------------------------
-- Secure match_document_chunks RPC
-- Caller must be an active member of filter_organization_id.
-- Returns no rows (not an error) when membership fails, to avoid info leaks.
-- ---------------------------------------------------------------------------

create or replace function public.match_document_chunks(
  query_embedding extensions.vector(768),
  match_threshold float,
  match_count integer,
  filter_organization_id uuid
)
returns table (
  id uuid,
  document_id uuid,
  organization_id uuid,
  chunk_index integer,
  content text,
  start_char integer,
  end_char integer,
  similarity float
)
language sql
stable
security invoker
set search_path = public, extensions
as $$
  select
    dc.id,
    dc.document_id,
    dc.organization_id,
    dc.chunk_index,
    dc.content,
    dc.start_char,
    dc.end_char,
    (1 - (dc.embedding <=> query_embedding))::float as similarity
  from public.document_chunks dc
  where dc.organization_id = filter_organization_id
    and private.is_org_member(filter_organization_id)
    and dc.embedding is not null
    and (1 - (dc.embedding <=> query_embedding)) >= match_threshold
  order by dc.embedding <=> query_embedding asc
  limit least(greatest(coalesce(match_count, 10), 1), 50);
$$;

revoke execute on function public.match_document_chunks(
  extensions.vector(768), float, integer, uuid
) from public;

revoke execute on function public.match_document_chunks(
  extensions.vector(768), float, integer, uuid
) from anon;

grant execute on function public.match_document_chunks(
  extensions.vector(768), float, integer, uuid
) to authenticated;

comment on function public.match_document_chunks is
  'Organization-scoped semantic search over document_chunks. Requires active membership via private.is_org_member.';
