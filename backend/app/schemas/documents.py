from datetime import datetime
from pydantic import BaseModel, Field


class DocumentClassificationRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    text: str = Field(default="", max_length=200_000)


class DocumentClassificationResponse(BaseModel):
    filename: str
    document_type: str
    confidence: float
    reasons: list[str]
    document_id: str | None = None
    chunk_count: int | None = None
    embedded_count: int | None = None
    embedding_status: str | None = None


class DocumentIngestionResponse(BaseModel):
    document_id: str
    title: str
    chunk_count: int
    embedded_count: int
    embedding_status: str
    message: str


class DocumentSummary(BaseModel):
    id: str
    title: str
    document_type: str | None = None
    status: str
    extraction_status: str
    document_date: str | None = None
    file_size_bytes: int | None = None
    classification_confidence: float | None = None
    created_at: datetime | None = None


class DocumentSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    document_type: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=10, ge=1, le=50)


class DocumentSearchResult(BaseModel):
    id: str
    title: str
    document_type: str | None
    status: str
    extraction_status: str
    document_date: str | None
    snippet: str


class DocumentSearchResponse(BaseModel):
    query: str
    results: list[DocumentSearchResult]


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2_000)
    limit: int = Field(default=5, ge=1, le=20)
    minimum_similarity: float = Field(default=0.35, ge=0.0, le=1.0)


class SemanticSearchMatch(BaseModel):
    chunk_id: str
    document_id: str
    title: str | None = None
    document_type: str | None = None
    content: str
    similarity: float


class SemanticSearchResponse(BaseModel):
    query: str
    match_count: int
    matches: list[SemanticSearchMatch]


class DocumentQuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2_000)
    document_type: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=5, ge=1, le=10)


class DocumentEvidence(BaseModel):
    document_id: str
    title: str
    document_type: str | None
    snippet: str


class DocumentQuestionResponse(BaseModel):
    question: str
    answer: str
    evidence: list[DocumentEvidence]
    ai_generated: bool
    retrieval_method: str = "none"
