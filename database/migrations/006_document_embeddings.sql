-- AI-RMMS document vector storage
-- PostgreSQL / Supabase
-- Stores chunked document text and Gemini embeddings for semantic retrieval.

create extension if not exists vector with schema extensions;

create table if not exists document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  organization_id uuid not null references organizations(id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  start_char integer,
  end_char integer,
  embedding extensions.vector(768),
  embedding_model text,
  embedding_provider text,
  embedding_dimension integer,
  embedding_status text not null default 'pending',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (document_id, chunk_index),
  check (chunk_index >= 0),
  check (start_char is null or start_char >= 0),
  check (end_char is null or end_char >= 0),
  check (end_char is null or start_char is null or end_char >= start_char)
);

create index if not exists idx_document_chunks_document
  on document_chunks(document_id, chunk_index);

create index if not exists idx_document_chunks_org
  on document_chunks(organization_id);

create index if not exists idx_document_chunks_embedding_status
  on document_chunks(organization_id, embedding_status);

create index if not exists idx_document_chunks_embedding_hnsw
  on document_chunks
  using hnsw (embedding vector_cosine_ops);

-- RLS is intentionally deferred until the organization-membership authorization
-- model is finalized. Do not expose document_chunks through the Data API before
-- organization-scoped policies are added.
