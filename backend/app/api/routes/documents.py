from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.dependencies import get_current_user
from app.schemas.documents import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
)
from app.services.document_extraction import extract_text
from app.services.document_intelligence import classify_document

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".txt", ".csv", ".pdf", ".docx", ".xlsx", ".xlsm"}
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/classify", response_model=DocumentClassificationResponse)
def classify_document_text(
    request: DocumentClassificationRequest,
    current_user=Depends(get_current_user),
):
    result = classify_document(request.filename, request.text)
    return DocumentClassificationResponse(
        filename=request.filename,
        document_type=result.document_type,
        confidence=result.confidence,
        reasons=result.reasons,
    )


@router.post("/upload-and-classify", response_model=DocumentClassificationResponse)
async def upload_and_classify_document(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()

    if not filename or suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported document type. Use TXT, CSV, PDF, DOCX, XLSX, or XLSM.",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Document exceeds the 10 MB upload limit.")

    text = extract_text(filename, content)
    if not text:
        raise HTTPException(
            status_code=422,
            detail="No readable text could be extracted from the document.",
        )

    result = classify_document(filename, text)

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

    document = (
        current_user["client"]
        .table("documents")
        .insert(
            {
                "organization_id": organization_id,
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

    return DocumentClassificationResponse(
        filename=filename,
        document_type=result.document_type,
        confidence=result.confidence,
        reasons=result.reasons + [f"Stored {len(text)} extracted characters in the document record."],
    )
