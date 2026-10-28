"""Job description analysis Pydantic models."""

from typing import Literal
from pydantic import BaseModel, Field


class Keyword(BaseModel):
    """Extracted keyword with evidence and category."""

    term: str
    category: Literal["critical", "high", "preferred", "contextual"]
    evidence: str
    relevance_score: float


class JDAnalysis(BaseModel):
    """Structured job description analysis extracted via Gemini."""

    job_id: str
    job_title: str
    company: str
    application_url: str
    experience_level: str
    keywords: list[Keyword] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    qualifications_required: list[str] = Field(default_factory=list)
    qualifications_preferred: list[str] = Field(default_factory=list)
    raw_text: str
