from pydantic import BaseModel, Field


class OfficeAssistantRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class OfficeAssistantResponse(BaseModel):
    answer: str
    evidence: list[str]
    advisory: bool = True
