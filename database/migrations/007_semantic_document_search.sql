-- Semantic document search over organization-scoped document chunks.
-- Uses pgvector cosine distance through an RPC because PostgREST does not
-- expose pgvector similarity operators directly.

alter table document_chunks enable row level security;

revoke all on document_chunks from anon;
grant select on document_chunks to authenticated;

create policy "members access document chunks"
on document_chunks for select
to authenticated
using ((select private.is_org_member(organization_id)));

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
    and dc.embedding is not null
    and (1 - (dc.embedding <=> query_embedding)) >= match_threshold
  order by dc.embedding <=> query_embedding asc
  limit least(greatest(match_count, 1), 50);
$$;

revoke execute on function public.match_document_chunks(
  extensions.vector(768), float, integer, uuid
) from public;

grant execute on function public.match_document_chunks(
  extensions.vector(768), float, integer, uuid
) to authenticated;
