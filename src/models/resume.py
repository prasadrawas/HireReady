"""Resume data Pydantic models."""

from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    """Candidate contact information."""

    name: str
    email: str
    phone: str
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None
    location: str | None = None


class SkillGroup(BaseModel):
    """Categorized skill set."""

    category: str
    skills: list[str] = Field(default_factory=list)


class BulletPoint(BaseModel):
    """Individual resume bullet point with deterministic ID for evidence linking."""

    id: str
    text: str
    source_id: str | None = None


class Experience(BaseModel):
    """Work experience entry."""

    company: str
    title: str
    location: str | None = None
    start_date: str
    end_date: str | None = None
    bullets: list[BulletPoint] = Field(default_factory=list)


class Project(BaseModel):
    """Project portfolio entry."""

    name: str
    url: str | None = None
    description: str
    bullets: list[BulletPoint] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class Education(BaseModel):
    """Educational degree entry."""

    institution: str
    degree: str
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None
    details: list[str] = Field(default_factory=list)


class ResumeData(BaseModel):
    """Parsed master resume data contract."""

    contact: ContactInfo
    summary: str
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
