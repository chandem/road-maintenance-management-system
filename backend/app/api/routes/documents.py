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
    return DocumentClassificationResponse(
        filename=filename,
        document_type=result.document_type,
        confidence=result.confidence,
        reasons=result.reasons + [f"Extracted {len(text)} characters from the uploaded document."],
    )
