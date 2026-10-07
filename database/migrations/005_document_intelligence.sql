-- AI-RMMS document intelligence persistence
-- Adds extracted content and processing metadata to the existing documents table.

alter table documents
  add column if not exists extracted_text text,
  add column if not exists file_size_bytes bigint,
  add column if not exists extraction_status text not null default 'pending',
  add column if not exists classification_confidence numeric(5,4);

create index if not exists idx_documents_org_type
  on documents(organization_id, document_type);

create index if not exists idx_documents_extraction_status
  on documents(organization_id, extraction_status);
