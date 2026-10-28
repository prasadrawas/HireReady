"""Resume match report Pydantic models."""

from typing import Literal
from pydantic import BaseModel, Field


class KeywordMatch(BaseModel):
    """Keyword presence, promotion status, or gap assessment."""

    term: str
    category: Literal["critical", "high", "preferred", "contextual"]
    status: Literal["present", "promotable", "addable", "gap"]
    found_in: str | None = None
    suggestion: str | None = None


class SectionRecommendation(BaseModel):
    """Recommendation for section restructuring or enhancement."""

    section: str
    action: str
    reason: str


class MatchReport(BaseModel):
    """Detailed resume-to-JD match report."""

    job_id: str
    application_url: str
    coverage_score: float
    keywords_present: list[KeywordMatch] = Field(default_factory=list)
    keywords_promotable: list[KeywordMatch] = Field(default_factory=list)
    keywords_addable: list[KeywordMatch] = Field(default_factory=list)
    keywords_gap: list[KeywordMatch] = Field(default_factory=list)
    section_recommendations: list[SectionRecommendation] = Field(default_factory=list)
