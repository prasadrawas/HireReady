"""Search preferences Pydantic schema."""

from pydantic import BaseModel, Field


class SearchPreferences(BaseModel):
    """User job search preferences."""

    target_roles: list[str] = Field(default_factory=list)
    target_keywords: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    remote_only: bool = False
    min_seniority: str = "senior"
    industries_include: list[str] = Field(default_factory=list)
    industries_exclude: list[str] = Field(default_factory=list)
    companies_exclude: list[str] = Field(default_factory=list)
    max_listing_age_days: int = 30
    salary_min: int | None = None
