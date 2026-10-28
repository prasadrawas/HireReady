"""Tailored resume and change record Pydantic models."""

from typing import Literal
from pydantic import BaseModel, Field

from src.models.resume import (
    ContactInfo,
    Education,
    Experience,
    Project,
    SkillGroup,
)


class ChangeRecord(BaseModel):
    """Specific resume modification record with source bullet tracking."""

    section: str
    original: str
    tailored: str
    source_bullet_id: str
    keywords_integrated: list[str] = Field(default_factory=list)
    change_type: Literal["rewrite", "reorder", "promote", "add_keyword", "new_bullet"]


class TailoredResume(BaseModel):
    """Complete tailored resume data structure."""

    job_id: str
    application_url: str
    contact: ContactInfo
    summary: str
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    changes: list[ChangeRecord] = Field(default_factory=list)
    needs_review: list[str] = Field(default_factory=list)
