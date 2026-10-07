from pydantic import BaseModel, Field


class DocumentClassificationRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    text: str = Field(default="", max_length=200_000)


class DocumentClassificationResponse(BaseModel):
    filename: str
    document_type: str
    confidence: float
    reasons: list[str]


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
