"""ATS validation Pydantic models."""

from pydantic import BaseModel, Field


class CheckResult(BaseModel):
    """Result of an individual validation check."""

    check: str
    passed: bool
    detail: str | None = None


class ValidationReport(BaseModel):
    """Overall ATS and integrity validation report."""

    job_id: str
    application_url: str
    checks: list[CheckResult] = Field(default_factory=list)
    keyword_verification: dict[str, bool] = Field(default_factory=dict)
    page_count: int
    unsupported_claims: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    passed: bool
