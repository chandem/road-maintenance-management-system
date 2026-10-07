from pydantic import BaseModel, Field


class DocumentClassificationRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    text: str = Field(default="", max_length=200_000)


class DocumentClassificationResponse(BaseModel):
    filename: str
    document_type: str
    confidence: float
    reasons: list[str]
