from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.schemas.documents import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
)
from app.services.document_intelligence import classify_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/classify", response_model=DocumentClassificationResponse)
def classify_uploaded_document(
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
