import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from google import genai

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.schemas.documents import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
    DocumentEvidence,
    DocumentQuestionRequest,
    DocumentQuestionResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentSearchResult,
)
from app.services.document_extraction import extract_text
from app.services.document_intelligence import classify_document
from app.services.semantic_search import search_document_chunks

router = APIRouter(prefix="/documents", tags=["documents"])
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
        snippet = snippet[:max_length - 1].rstrip() + "…"
    return snippet


@router.post("/classify", response_model=DocumentClassificationResponse)
def classify_document_text(request: DocumentClassificationRequest, current_user=Depends(get_current_user)):
    result = classify_document(request.filename, request.text)
    return DocumentClassificationResponse(filename=request.filename, document_type=result.document_type, confidence=result.confidence, reasons=result.reasons)


@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(request: DocumentSearchRequest, current_user=Depends(get_current_user)):
    query = request.query.strip()
    escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped_query}%"
    document_query = (current_user["client"].table("documents")
        .select("id,title,document_type,status,extraction_status,document_date,extracted_text")
        .or_(f"title.ilike.{pattern},extracted_text.ilike.{pattern}")
        .order("created_at", desc=True).limit(request.limit))
    if request.document_type:
        document_query = document_query.eq("document_type", request.document_type)
    rows = document_query.execute().data or []
    results = [DocumentSearchResult(id=str(row["id"]), title=row["title"], document_type=row.get("document_type"), status=row["status"], extraction_status=row["extraction_status"], document_date=str(row["document_date"]) if row.get("document_date") else None, snippet=_document_snippet(row.get("extracted_text"), query)) for row in rows]
    return DocumentSearchResponse(query=query, results=results)


@router.post("/question", response_model=DocumentQuestionResponse)
def ask_document_question(request: DocumentQuestionRequest, current_user=Depends(get_current_user)):
    """Answer using semantic document evidence, with keyword retrieval as a safe fallback."""
    question = request.question.strip()
    evidence = []

    if not request.document_type:
        try:
            profile = (
                current_user["client"]
                .table("user_profiles")
                .select("organization_id")
                .eq("id", current_user["id"])
                .maybe_single()
                .execute()
            )
            organization_id = (profile.data or {}).get("organization_id")
            if organization_id:
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
                        .select("id,title,document_type")
                        .in_("id", document_ids)
                        .execute()
                        .data
                        or []
                    )
                    metadata = {str(row["id"]): row for row in documents}
                    evidence = [
                        DocumentEvidence(
                            document_id=match.document_id,
                            title=metadata[match.document_id]["title"],
                            document_type=metadata[match.document_id].get("document_type"),
                            snippet=match.content[:500].strip(),
                        )
                        for match in matches
                        if match.document_id in metadata
                    ]
        except Exception:
            evidence = []

    if not evidence:
        escaped_query = question.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped_query}%"
        document_query = (
            current_user["client"].table("documents")
            .select("id,title,document_type,status,extraction_status,document_date,extracted_text")
            .or_(f"title.ilike.{pattern},extracted_text.ilike.{pattern}")
            .order("created_at", desc=True)
            .limit(request.limit)
        )
        if request.document_type:
            document_query = document_query.eq("document_type", request.document_type)
        rows = document_query.execute().data or []
        evidence = [
            DocumentEvidence(
                document_id=str(row["id"]),
                title=row["title"],
                document_type=row.get("document_type"),
                snippet=_document_snippet(row.get("extracted_text"), question),
            )
            for row in rows
        ]

    if not evidence:
        return DocumentQuestionResponse(
            question=question,
            answer="I could not find relevant stored document evidence. The answer is not available from the retrieved documents.",
            evidence=[],
            ai_generated=False,
        )

    settings = get_settings()
    if not settings.gemini_api_key:
        return DocumentQuestionResponse(
            question=question,
            answer="Relevant document evidence was found, but the AI provider is not configured yet. Review the evidence below.",
            evidence=evidence,
            ai_generated=False,
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
        "Do not make approvals or binding decisions. Keep the answer concise and suitable for a road-maintenance engineering office.\n\n"
        f"Question: {question}\n\nEvidence:\n{json.dumps(context, default=str)}"
    )
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config={"system_instruction": "You are the AI-RMMS evidence-based document assistant."},
        )
        answer = response.text.strip() if response.text else ""
    except Exception:
        answer = "I could not generate the AI answer right now. Please review the retrieved document evidence."
    return DocumentQuestionResponse(question=question, answer=answer, evidence=evidence, ai_generated=bool(answer))


@router.post("/upload-and-classify", response_model=DocumentClassificationResponse)
async def classify_uploaded_document(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if not filename or suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported document type. Use TXT, CSV, PDF, DOCX, XLSX, or XLSM.")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Document exceeds the 10 MB upload limit.")
    text = extract_text(filename, content)
    if not text:
        raise HTTPException(status_code=422, detail="No readable text could be extracted from the document.")
    result = classify_document(filename, text)
    profile = current_user["client"].table("user_profiles").select("organization_id").eq("id", current_user["id"]).maybe_single().execute()
    organization_id = (profile.data or {}).get("organization_id")
    if not organization_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    document = current_user["client"].table("documents").insert({"organization_id": organization_id, "title": filename, "document_type": result.document_type, "mime_type": file.content_type, "status": "processed", "extraction_status": "completed", "classification_confidence": result.confidence, "extracted_text": text, "file_size_bytes": len(content), "uploaded_by": current_user["id"]}).execute()
    if not document.data:
        raise HTTPException(status_code=500, detail="Document could not be saved.")
    return DocumentClassificationResponse(filename=filename, document_type=result.document_type, confidence=result.confidence, reasons=result.reasons + [f"Stored {len(text)} extracted characters in the document record."])
