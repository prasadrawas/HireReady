"""Applicant profile model and loader for auto-applying to jobs."""

import logging
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field

from config.settings import settings
from src.resume_parser import ResumeParser

logger = logging.getLogger(__name__)


class ContactProfile(BaseModel):
    """Personal and contact information."""

    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""
    current_company: str = ""
    current_title: str = ""


class WorkAuthorization(BaseModel):
    """Work authorization and visa sponsorship status."""

    authorized_to_work: bool = True
    requires_sponsorship: bool = False
    citizenship_status: str = "Citizen / Permanent Resident"


class EmploymentPreferences(BaseModel):
    """Compensation, availability, and workplace preferences."""

    target_salary: str = "$180,000"
    salary_currency: str = "USD"
    earliest_start_date: str = "2 weeks notice"
    notice_period_weeks: int = 2
    willing_to_relocate: bool = True
    preferred_workplace: str = "Hybrid or Remote"


class EEOCDemographics(BaseModel):
    """Equal Employment Opportunity voluntary self-identification disclosures."""

    gender: str = "Decline to self-identify"
    race_ethnicity: str = "Decline to self-identify"
    veteran_status: str = "I am not a protected veteran"
    disability_status: str = "No, I do not have a disability"


class ApplicantProfile(BaseModel):
    """Complete candidate profile for automated job applications."""

    contact: ContactProfile = Field(default_factory=ContactProfile)
    work_authorization: WorkAuthorization = Field(default_factory=WorkAuthorization)
    employment_preferences: EmploymentPreferences = Field(default_factory=EmploymentPreferences)
    eeoc_demographics: EEOCDemographics = Field(default_factory=EEOCDemographics)


def load_applicant_profile(path: Path | None = None) -> ApplicantProfile:
    """Load the applicant profile from YAML, falling back to master resume if needed.

    Args:
        path: Optional path to the applicant_profile.yaml file.

    Returns:
        ApplicantProfile instance.
    """
    profile_path = path or settings.applicant_profile_path
    raw_data: dict[str, Any] = {}

    if profile_path.exists():
        try:
            parsed = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                raw_data = parsed
        except Exception as e:
            logger.warning("Failed to parse %s: %s", profile_path, e)

    contact_dict = raw_data.get("contact", {})

    # If contact data is missing or incomplete, attempt fallback from master resume
    if not contact_dict.get("email") or not (contact_dict.get("first_name") or contact_dict.get("full_name")):
        if settings.master_resume_path.exists():
            try:
                parser = ResumeParser()
                resume_data = parser.parse(settings.master_resume_path.read_text(encoding="utf-8"))
                ci = resume_data.contact_info

                if not contact_dict.get("full_name"):
                    contact_dict["full_name"] = ci.name or ""
                if not contact_dict.get("email"):
                    contact_dict["email"] = ci.email or ""
                if not contact_dict.get("phone"):
                    contact_dict["phone"] = ci.phone or ""
                if not contact_dict.get("location"):
                    contact_dict["location"] = ci.location or ""
                if not contact_dict.get("linkedin"):
                    contact_dict["linkedin"] = ci.linkedin or ""
                if not contact_dict.get("github"):
                    contact_dict["github"] = ci.github or ""
                if not contact_dict.get("website"):
                    contact_dict["website"] = ci.website or ""

                if resume_data.experience and not contact_dict.get("current_company"):
                    contact_dict["current_company"] = resume_data.experience[0].company or ""
                if resume_data.experience and not contact_dict.get("current_title"):
                    contact_dict["current_title"] = resume_data.experience[0].title or ""
            except Exception as e:
                logger.debug("Failed to extract fallback contact from master resume: %s", e)

    # Normalize first/last/full name
    full_name = contact_dict.get("full_name", "").strip()
    first_name = contact_dict.get("first_name", "").strip()
    last_name = contact_dict.get("last_name", "").strip()

    if not full_name and (first_name or last_name):
        full_name = f"{first_name} {last_name}".strip()
    elif full_name and not (first_name and last_name):
        parts = full_name.split()
        if parts:
            first_name = parts[0]
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    contact_dict["full_name"] = full_name
    contact_dict["first_name"] = first_name
    contact_dict["last_name"] = last_name

    raw_data["contact"] = contact_dict

    return ApplicantProfile.model_validate(raw_data)

