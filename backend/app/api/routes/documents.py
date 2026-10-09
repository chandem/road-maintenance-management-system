import json
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.api.dependencies import get_current_user, require_org_admin
from app.core.config import get_settings
from app.schemas.documents import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
    DocumentEvidence,
    DocumentIngestionResponse,
    DocumentQuestionRequest,
    DocumentQuestionResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentSearchResult,
    DocumentSummary,
    SemanticSearchMatch,
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from app.services.ai_provider import generate_text
from app.services.document_extraction import extract_text
from app.services.document_intelligence import classify_document
from app.services.document_ingestion import ingest_document_chunks
from app.services.semantic_search import search_document_chunks

router = APIRouter(prefix="/documents", tags=["documents"])

# Department-aware API authorization complements database RLS. Keep the SQL
# migration unapplied until the authenticated-JWT staging matrix passes.
ALLOWED_EXTENSIONS = {".txt", ".csv", ".pdf", ".docx", ".xlsx", ".xlsm"}
MAX_FILE_SIZE = 10 * 1024 * 1024


def _document_snippet(text: str | None, query: str, max_length: int = 240) -> str:
    if not text:
        return ""
    normalized_text = text.strip()
    if not normalized_text:
        return ""
    clean_query = query.strip()
    position = normalized_text.lower().find(clean_query.lower())
    if position < 0:
        return normalized_text[:max_length].strip()
    query_length = len(clean_query)
    available = max(max_length - query_length - 2, 0)
    before = available // 2
    after = available - before
    start = max(0, position - before)
    end = min(len(normalized_text), position + query_length + after)
    snippet = normalized_text[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(normalized_text):
        snippet += "…"
    if len(snippet) > max_length:
        snippet = snippet[: max_length - 1].rstrip() + "…"
    return snippet


def _organization_id(current_user) -> str:
    profile = (
        current_user["client"]
        .table("user_profiles")
        .select("organization_id")
        .eq("id", current_user["id"])
        .maybe_single()
        .execute()
    )
    organization_id = (profile.data or {}).get("organization_id")
    if not organization_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return str(organization_id)


VALID_DEPARTMENT_CODES = {
    "road_asset",
    "machinery_maintenance",
    "finance",
    "human_resources",
    "general_assets",
}


def _authorize_department(current_user, department_code: str | None, *, write: bool = False) -> str:
    """Return the active organization ID after checking department access.

    Admins may omit department_code to access all organization documents.
    Non-admins must specify a department and hold a matching active role.
    Authorization lookups use the caller's JWT-scoped client and fail closed.
    """
    from app.services.ai_audit import resolve_organization_id

    client = current_user["client"]
    user_id = current_user["id"]
    try:
        organization_id = resolve_organization_id(client, user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Document organization membership could not be verified.",
        ) from exc
    if not organization_id:
        raise HTTPException(status_code=403, detail="Active organization membership is required.")

    try:
        membership = (
            client.table("organization_members")
            .select("role")
            .eq("organization_id", organization_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Document authorization could not be verified.",
        ) from exc

    if not membership.data:
        raise HTTPException(status_code=403, detail="Active organization membership is required.")
    if membership.data.get("role") in {"owner", "admin"}:
        if department_code is not None and department_code not in VALID_DEPARTMENT_CODES:
            raise HTTPException(status_code=422, detail="Invalid department code.")
        return str(organization_id)

    if department_code is None:
        raise HTTPException(
            status_code=403,
            detail="Specify a department you are authorized to access.",
        )
    if department_code not in VALID_DEPARTMENT_CODES:
        raise HTTPException(status_code=422, detail="Invalid department code.")

    allowed_roles = ["department_manager", "officer"] if write else [
        "department_manager", "officer", "read_only"
    ]
    try:
        result = client.rpc(
            "has_department_role",
            {
                "p_organization_id": organization_id,
                "p_department_code": department_code,
                "p_allowed_roles": allowed_roles,
            },
        ).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Document department permissions could not be verified.",
        ) from exc
    if result.data is not True:
        raise HTTPException(
            status_code=403,
            detail="You do not have the required document department permissions.",
        )
    return str(organization_id)


def _authorize_document_row(current_user, row: dict, *, write: bool = False) -> str:
    """Authorize one fetched document; unclassified records are admin-only."""
    organization_id = _authorize_department(
        current_user,
        row.get("department_code"),
        write=write,
    )
    if str(row.get("organization_id")) != organization_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return organization_id


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    current_user=Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    document_type: str | None = Query(default=None, max_length=100),
    department_code: str | None = Query(default=None),
):
    """List documents only within an authorized department (or all for admins)."""
    organization_id = _authorize_department(current_user, department_code)
    query = (
        current_user["client"]
        .table("documents")
        .select(
            "id,title,organization_id,department_code,status,extraction_status,document_date,"
            "file_size_bytes,classification_confidence,created_at,document_type"
        )
        .eq("organization_id", organization_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if department_code:
        query = query.eq("department_code", department_code)
    if document_type:
        query = query.eq("document_type", document_type)
    rows = query.execute().data or []
    return [
        DocumentSummary(
            id=str(row["id"]),
            title=row["title"],
            department_code=row.get("department_code"),
            document_type=row.get("document_type"),
            status=row["status"],
            extraction_status=row["extraction_status"],
            document_date=str(row["document_date"]) if row.get("document_date") else None,
            file_size_bytes=row.get("file_size_bytes"),
            classification_confidence=(
                float(row["classification_confidence"])
                if row.get("classification_confidence") is not None
                else None
            ),
            created_at=row.get("created_at"),
        )
        for row in rows
    ]


@router.get("/{document_id}", response_model=DocumentSummary)
def get_document(
    document_id: UUID,
    current_user=Depends(get_current_user),
):
    """Get one document summary by ID."""
    row = (
        current_user["client"]
        .table("documents")
        .select(
            "id,title,organization_id,department_code,document_type,status,extraction_status,document_date,"
            "file_size_bytes,classification_confidence,created_at"
        )
        .eq("id", str(document_id))
        .maybe_single()
        .execute()
    )
    if not row.data:
        raise HTTPException(status_code=404, detail="Document not found")
    data = row.data
    _authorize_document_row(current_user, data)
    return DocumentSummary(
        id=str(data["id"]),
        title=data["title"],
        department_code=data.get("department_code"),
        document_type=data.get("document_type"),
        status=data["status"],
        extraction_status=data["extraction_status"],
        document_date=str(data["document_date"]) if data.get("document_date") else None,
        file_size_bytes=data.get("file_size_bytes"),
        classification_confidence=(
            float(data["classification_confidence"])
            if data.get("classification_confidence") is not None
            else None
        ),
        created_at=data.get("created_at"),
    )


@router.post("/classify", response_model=DocumentClassificationResponse)
def classify_document_text(
    request: DocumentClassificationRequest,
    current_user=Depends(require_org_admin()),
):
    result = classify_document(request.filename, request.text)
    return DocumentClassificationResponse(
        filename=request.filename,
        document_type=result.document_type,
        confidence=result.confidence,
        reasons=result.reasons,
    )


@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(
    request: DocumentSearchRequest,
    current_user=Depends(get_current_user),
):
    """Keyword search over document titles and extracted text."""
    organization_id = _authorize_department(current_user, request.department_code)
    query = request.query.strip()
    escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped_query}%"
    document_query = (
        current_user["client"]
        .table("documents")
        .select("id,title,organization_id,department_code,document_type,status,extraction_status,document_date,extracted_text")
        .eq("organization_id", organization_id)
        .or_(f"title.ilike.{pattern},extracted_text.ilike.{pattern}")
        .order("created_at", desc=True)
        .limit(request.limit)
    )
    if request.department_code:
        document_query = document_query.eq("department_code", request.department_code)
    if request.document_type:
        document_query = document_query.eq("document_type", request.document_type)
    rows = document_query.execute().data or []
    results = [
        DocumentSearchResult(
            id=str(row["id"]),
            title=row["title"],
            document_type=row.get("document_type"),
            status=row["status"],
            extraction_status=row["extraction_status"],
            document_date=str(row["document_date"]) if row.get("document_date") else None,
            snippet=_document_snippet(row.get("extracted_text"), query),
        )
        for row in rows
    ]
    return DocumentSearchResponse(query=query, results=results)


@router.post("/semantic-search", response_model=SemanticSearchResponse)
def semantic_search_documents(
    request: SemanticSearchRequest,
    current_user=Depends(get_current_user),
):
    """Vector search over organization document chunks (Step 4)."""
    organization_id = _authorize_department(current_user, request.department_code)
    matches = search_document_chunks(
        request.query,
        organization_id=organization_id,
        access_token=current_user["access_token"],
        limit=request.limit,
        minimum_similarity=request.minimum_similarity,
    )
    if not matches:
        return SemanticSearchResponse(query=request.query, match_count=0, matches=[])

    document_ids = list(dict.fromkeys(m.document_id for m in matches))
    documents = (
        current_user["client"]
        .table("documents")
        .select("id,title,document_type,department_code")
        .eq("organization_id", organization_id)
        .in_("id", document_ids)
        .execute()
        .data
        or []
    )
    if request.department_code:
        documents = [row for row in documents if row.get("department_code") == request.department_code]
    metadata = {str(row["id"]): row for row in documents}
    # Filter the RPC results again in the API before any content is returned or
    # passed to an LLM. Database RLS remains the required defense-in-depth layer.
    matches = [match for match in matches if match.document_id in metadata]

    enriched = [
        SemanticSearchMatch(
            chunk_id=m.chunk_id,
            document_id=m.document_id,
            title=(metadata.get(m.document_id) or {}).get("title"),
            document_type=(metadata.get(m.document_id) or {}).get("document_type"),
            content=m.content,
            similarity=m.similarity,
        )
        for m in matches
    ]
    return SemanticSearchResponse(
        query=request.query,
        match_count=len(enriched),
        matches=enriched,
    )


@router.post("/question", response_model=DocumentQuestionResponse)
def ask_document_question(
    request: DocumentQuestionRequest,
    current_user=Depends(get_current_user),
):
    """Evidence-based Q&A: semantic retrieval first, keyword fallback."""
    organization_id = _authorize_department(current_user, request.department_code)
    question = request.question.strip()
    evidence: list[DocumentEvidence] = []
    retrieval_method = "none"

    if not request.document_type:
        try:
            matches = search_document_chunks(
                question,
                organization_id=organization_id,
                access_token=current_user["access_token"],
                limit=request.limit,
                minimum_similarity=0.35,
            )
            document_ids = list(dict.fromkeys(match.document_id for match in matches))
            if document_ids:
                documents = (
                    current_user["client"]
                    .table("documents")
                    .select("id,title,document_type,department_code")
                    .eq("organization_id", organization_id)
                    .in_("id", document_ids)
                    .execute()
                    .data
                    or []
                )
                if request.department_code:
                    documents = [row for row in documents if row.get("department_code") == request.department_code]
                metadata = {str(row["id"]): row for row in documents}
                evidence = [
                    DocumentEvidence(
                        document_id=match.document_id,
                        title=str(
                            (metadata.get(match.document_id) or {}).get("title")
                            or match.document_id
                        ),
                        document_type=(metadata.get(match.document_id) or {}).get(
                            "document_type"
                        ),
                        snippet=match.content[:500].strip(),
                    )
                    for match in matches
                    if match.document_id in metadata
                ]
                if evidence:
                    retrieval_method = "semantic"
        except Exception:
            evidence = []

    if not evidence:
        escaped_query = question.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped_query}%"
        document_query = (
            current_user["client"]
            .table("documents")
            .select(
                "id,title,organization_id,department_code,document_type,status,extraction_status,document_date,extracted_text"
            )
            .eq("organization_id", organization_id)
            .or_(f"title.ilike.{pattern},extracted_text.ilike.{pattern}")
            .order("created_at", desc=True)
            .limit(request.limit)
        )
        if request.department_code:
            document_query = document_query.eq("department_code", request.department_code)
        if request.document_type:
            document_query = document_query.eq("document_type", request.document_type)
        rows = document_query.execute().data or []
        evidence = [
            DocumentEvidence(
                document_id=str(row["id"]),
                title=str(row.get("title") or row["id"]),
                document_type=row.get("document_type"),
                snippet=_document_snippet(row.get("extracted_text"), question),
            )
            for row in rows
        ]
        if evidence:
            retrieval_method = "keyword"

    if not evidence:
        return DocumentQuestionResponse(
            question=question,
            answer=(
                "I could not find relevant stored document evidence. "
                "The answer is not available from the retrieved documents."
            ),
            evidence=[],
            ai_generated=False,
            retrieval_method="none",
        )

    settings = get_settings()
    if not settings.gemini_api_key:
        return DocumentQuestionResponse(
            question=question,
            answer=(
                "Relevant document evidence was found, but the AI provider is not "
                "configured yet. Review the evidence below."
            ),
            evidence=evidence,
            ai_generated=False,
            retrieval_method=retrieval_method,
        )

    context = [
        {
            "document_id": item.document_id,
            "title": item.title,
            "document_type": item.document_type,
            "evidence": item.snippet,
        }
        for item in evidence
    ]
    prompt = (
        "Answer the user's question using ONLY the supplied document evidence. "
        "If the evidence does not contain the answer, say it is not available. "
        "Do not invent facts, costs, dates, quantities, causes, measurements, or site observations. "
        "Do not make approvals or binding decisions. Keep the answer concise and suitable for a "
        "road-maintenance engineering office.\n\n"
        f"Question: {question}\n\nEvidence:\n{json.dumps(context, default=str)}"
    )
    ai_result = generate_text(
        prompt,
        system_instruction="You are the AI-RMMS evidence-based document assistant.",
    )
    if ai_result:
        answer = ai_result.text
    else:
        answer = (
            "I could not generate the AI answer right now. "
            "Please review the retrieved document evidence."
        )
    return DocumentQuestionResponse(
        question=question,
        answer=answer,
        evidence=evidence,
        ai_generated=bool(ai_result),
        retrieval_method=retrieval_method,
    )


@router.post("/upload-and-classify", response_model=DocumentClassificationResponse)
async def classify_uploaded_document(
    file: UploadFile = File(...),
    department_code: str = Form(...),
    current_user=Depends(get_current_user),
):
    """Upload → extract → classify → store → chunk → embed."""
    organization_id = _authorize_department(current_user, department_code, write=True)
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if not filename or suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported document type. Use TXT, CSV, PDF, DOCX, XLSX, or XLSM.",
        )
    # Read at most one byte beyond the limit so oversized uploads cannot be
    # copied wholesale into application memory before the size check.
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Document exceeds the 10 MB upload limit.")
    text = extract_text(filename, content)
    if not text:
        raise HTTPException(
            status_code=422,
            detail="No readable text could be extracted from the document.",
        )

    result = classify_document(filename, text)

    document = (
        current_user["client"]
        .table("documents")
        .insert(
            {
                "organization_id": organization_id,
                "department_code": department_code,
                "title": filename,
                "document_type": result.document_type,
                "mime_type": file.content_type,
                "status": "processed",
                "extraction_status": "completed",
                "classification_confidence": result.confidence,
                "extracted_text": text,
                "file_size_bytes": len(content),
                "uploaded_by": current_user["id"],
            }
        )
        .execute()
    )
    if not document.data:
        raise HTTPException(status_code=500, detail="Document could not be saved.")

    document_id = str(document.data[0]["id"])
    chunk_count = None
    embedded_count = None
    embedding_status = None
    ingestion_note = "Document chunks were not generated yet."

    try:
        ingestion = ingest_document_chunks(
            current_user["client"],
            document_id=document_id,
            organization_id=organization_id,
            extracted_text=text,
        )
        chunk_count = ingestion.chunk_count
        embedded_count = ingestion.embedded_count
        embedding_status = ingestion.embedding_status
        ingestion_note = (
            f"Created {ingestion.chunk_count} document chunks; "
            f"{ingestion.embedded_count} embeddings ready "
            f"(status: {ingestion.embedding_status})."
        )
    except Exception:
        ingestion_note = (
            "Document was saved, but semantic indexing failed. "
            "Use POST /documents/{id}/ingest after the vector schema is available."
        )

    return DocumentClassificationResponse(
        filename=filename,
        document_type=result.document_type,
        confidence=result.confidence,
        reasons=result.reasons
        + [
            f"Stored {len(text)} extracted characters in the document record.",
            ingestion_note,
        ],
        document_id=document_id,
        chunk_count=chunk_count,
        embedded_count=embedded_count,
        embedding_status=embedding_status,
    )


@router.post("/{document_id}/ingest", response_model=DocumentIngestionResponse)
def reindex_document(
    document_id: UUID,
    current_user=Depends(get_current_user),
):
    """Re-run chunk + embed for an existing document."""
    supabase = current_user["client"]

    document = (
        supabase.table("documents")
        .select("id,title,organization_id,department_code,extracted_text,extraction_status")
        .eq("id", str(document_id))
        .maybe_single()
        .execute()
    )
    if not document.data:
        raise HTTPException(status_code=404, detail="Document not found")

    row = document.data
    organization_id = _authorize_document_row(current_user, row, write=True)

    text = (row.get("extracted_text") or "").strip()
    if not text:
        raise HTTPException(
            status_code=422,
            detail="Document has no extracted text to index.",
        )

    try:
        ingestion = ingest_document_chunks(
            supabase,
            document_id=str(document_id),
            organization_id=organization_id,
            extracted_text=text,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Semantic indexing failed. Check vector migrations and embeddings config.",
        ) from exc

    return DocumentIngestionResponse(
        document_id=str(document_id),
        title=row.get("title") or str(document_id),
        chunk_count=ingestion.chunk_count,
        embedded_count=ingestion.embedded_count,
        embedding_status=ingestion.embedding_status,
        message=(
            f"Indexed {ingestion.chunk_count} chunks with "
            f"{ingestion.embedded_count} embeddings "
            f"(status: {ingestion.embedding_status})."
        ),
    )
