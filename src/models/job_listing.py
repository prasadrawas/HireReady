"""Job listing and scoring Pydantic models."""

from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class JobListing(BaseModel):
    """Normalized job listing across all ATS sources."""

    id: str
    ats_source: str  # platform name from ats_platforms.json (e.g. "lever", "greenhouse", "ashby", "rippling") or "direct"
    company: str
    company_slug: str
    title: str
    location: str
    locations: list[str] = Field(default_factory=list)
    remote: bool = False
    workplace_type: str | None = None  # "Remote" | "Hybrid" | "On-site" | "Unspecified"
    employment_type: str | None = None  # "Full-time" | "Part-time" | "Contract" | "Internship"
    experience_level: str | None = None  # "Associate" | "Mid-Senior" | "Lead" | "Executive"
    department: str | None = None
    team: str | None = None
    country: str | None = None
    posted_date: date | None = None
    updated_date: date | None = None
    deadline_date: date | None = None
    description_html: str
    description_text: str
    description_sections: dict[str, str] = Field(default_factory=dict)
    application_url: str
    job_url: str | None = None
    salary_raw: Any = None
    has_equity: bool = False
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
