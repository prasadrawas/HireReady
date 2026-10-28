"""Job listing and scoring Pydantic models."""

from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class JobListing(BaseModel):
    """Normalized job listing across all ATS sources."""

    id: str
    ats_source: str  # platform name from ats_platforms.json (e.g. "lever", "greenhouse", "ashby") or "direct"
    company: str
    company_slug: str
    title: str
    location: str
    remote: bool = False
    department: str | None = None
    posted_date: date | None = None
    description_html: str
    description_text: str
    application_url: str
    api_posting_id: str
    metadata: dict = Field(default_factory=dict)
    first_seen: datetime = Field(default_factory=datetime.now)
    status: Literal[
        "new",
        "scored",
        "selected",
        "analyzed",
        "tailored",
        "validated",
        "ready_for_review",
        "approved",
        "submitted",
        "rejected",
        "skipped",
        "validation_failed",
    ] = "new"


class QuickScore(BaseModel):
    """Pass 1 fast deterministic score."""

    job_id: str
    keyword_overlap: float
    title_match: float
    seniority_match: float
    composite_score: float
    pass_to_deep_scoring: bool


class DeepScore(BaseModel):
    """Pass 2 Gemini semantic score."""

    job_id: str
    semantic_match: float
    role_fit: str
    key_gaps: list[str] = Field(default_factory=list)
    recommendation: Literal["strong_match", "good_match", "weak_match", "skip"]
