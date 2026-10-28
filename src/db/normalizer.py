"""Document normalizer: converts raw JobListing into custom NoSQL MongoDB document schema."""

from datetime import datetime, timezone
import re
from typing import Any

from src.models.job_listing import JobListing
from src.red_flag_detector import RedFlagDetector
from src.salary_extractor import SalaryExtractor
from src.scoring_features import _SYNONYM_GROUPS


def _extract_skills(text: str) -> list[str]:
    """Extract distinct technical skills and tools from job description using canonical synonym groups."""
    if not text:
        return []

    text_lower = text.lower()
    found_skills: set[str] = set()

    for group in _SYNONYM_GROUPS:
        canonical = group[0].title() if not group[0].isupper() else group[0]
        # Check if any variant exists as a word or phrase
        for variant in group:
            # Word boundary regex for short terms like 'go', 'r', 'c', 'js'
            if len(variant) <= 3:
                pattern = rf"\b{re.escape(variant)}\b"
                if re.search(pattern, text_lower):
                    found_skills.add(canonical)
                    break
            else:
                if variant in text_lower:
                    found_skills.add(canonical)
                    break

    return sorted(found_skills)


def normalize_job_for_db(job: JobListing, raw_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convert a JobListing instance into our custom normalized NoSQL document format."""
    # 1. Salary extraction
    meta = dict(job.metadata or {})
    if job.salary_raw:
        meta["salary_raw"] = job.salary_raw
        if isinstance(job.salary_raw, list):
            meta["payRangeDetails"] = job.salary_raw
        elif isinstance(job.salary_raw, dict):
            meta["compensation"] = job.salary_raw

    salary_info = SalaryExtractor.extract(job.description_text or "", meta)

    # 2. Heuristic Red Flag verdict
    flags = RedFlagDetector.scan(job.description_text or "", job.title or "")
    rf_summary = RedFlagDetector.summarize(flags)
    red_flag_verdict = rf_summary.get("verdict", "clean")

    # 3. Skills extraction
    skills = _extract_skills(job.description_text or "")

    # 4. Normalized locations list
    locations = list(job.locations) if job.locations else []
    if job.location and job.location not in locations:
        locations.insert(0, job.location)

    # 5. Dates
    posted_date_iso = job.posted_date.isoformat() if job.posted_date else None

    # 6. Build custom document
    doc: dict[str, Any] = {
        "_id": job.id,
        "ats_source": job.ats_source,
        "company": job.company,
        "company_slug": job.company_slug,
        "title": job.title,
        "title_normalized": job.title.lower().strip(),
        "workplace_type": job.workplace_type or ("Remote" if job.remote else "On-site"),
        "remote": bool(job.remote),
        "location": job.location or ("Remote" if job.remote else "Unspecified"),
        "locations": locations,
        "country": job.country,
        "employment_type": job.employment_type or "Full-time",
        "experience_level": job.experience_level or "Mid-Senior",
        "department": job.department,
        "team": job.team,
        "salary": {
            "raw": salary_info.display if salary_info else (job.salary_raw or "Not listed"),
            "min": salary_info.min_salary if salary_info else None,
            "max": salary_info.max_salary if salary_info else None,
            "currency": salary_info.currency if salary_info else "USD",
            "period": salary_info.period if salary_info else "year",
        },
        "has_equity": bool(job.has_equity),
        "skills_extracted": skills,
        "red_flag_verdict": red_flag_verdict,
        "posted_date": posted_date_iso,
        "application_url": job.application_url,
        "job_url": job.job_url or job.application_url,
        "description_text": job.description_text or "",
        "description_html": job.description_html or "",
        "description_sections": job.description_sections or {},
        "status": job.status or "new",
        "metadata": {**(job.metadata or {}), **(raw_metadata or {})},
    }

    return doc
