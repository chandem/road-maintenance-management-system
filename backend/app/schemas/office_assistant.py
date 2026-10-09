from pydantic import BaseModel, Field, model_validator


class OfficeAssistantRequest(BaseModel):
    """Accept either `question` or legacy `query`."""

    question: str | None = Field(default=None, min_length=3, max_length=2000)
    query: str | None = Field(default=None, min_length=3, max_length=2000)
    include_documents: bool = True

    @model_validator(mode="after")
    def require_question_text(self):
        text = (self.question or self.query or "").strip()
        if len(text) < 3:
            raise ValueError("Provide question or query with at least 3 characters")
        self.question = text
        self.query = text
        return self


class OfficeAssistantResponse(BaseModel):
    query: str
    answer: str
    evidence: list[str]
    modules_consulted: list[str] = Field(default_factory=list)
    document_evidence: list[str] = Field(default_factory=list)
    advisory: bool = True
    ai_generated: bool = False
