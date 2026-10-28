"""Job query, cleaning, enrichment, and output inspection service."""

from datetime import datetime
import html
import json
import logging
import math
from typing import Any
from bs4 import BeautifulSoup

from config.settings import settings
from src.db.mongo import is_mongo_configured
from src.red_flag_detector import RedFlagDetector
from src.role_suggester import RoleSuggester
from src.salary_extractor import SalaryExtractor
from src.tracker import ApplicationTracker

logger = logging.getLogger(__name__)


class JobQueryService:
    """Handles reading scanned jobs, unescaping descriptions, enrichment, and output retrieval."""

    def __init__(self, tracker: ApplicationTracker | None = None):
        self.tracker = tracker or ApplicationTracker()

    def get_jobs(
        self,
        search: str | None = None,
        platform: str | None = None,
        company: str | None = None,
        remote_only: bool = False,
        min_salary: int = 0,
        min_score: float = 0.0,
        page: int = 1,
        page_size: int = 0,
    ) -> dict[str, Any]:
        """Fetch jobs from MongoDB (if configured and populated) or fallback to local JSON."""
        if is_mongo_configured():
            mongo_result = self._get_jobs_from_mongo(
                search=search,
                platform=platform,
                company=company,
                remote_only=remote_only,
                min_salary=min_salary,
                min_score=min_score,
                page=page,
                page_size=page_size,
            )
            if mongo_result is not None:
                return mongo_result

        return self._get_jobs_from_local(
            search=search,
            min_score=min_score,
            page=page,
            page_size=page_size,
        )

    def _get_jobs_from_mongo(
        self,
        search: str | None = None,
        platform: str | None = None,
        company: str | None = None,
        remote_only: bool = False,
        min_salary: int = 0,
        min_score: float = 0.0,
        page: int = 1,
        page_size: int = 0,
    ) -> dict[str, Any] | None:
        """Fetch and enrich jobs directly from MongoDB Atlas collection with pagination."""
        try:
            from src.db.mongo import build_mongo_query, fetch_paginated_jobs_sync

            query = build_mongo_query(
                search=search,
                platform=platform,
                company=company,
                remote_only=remote_only,
                min_salary=min_salary,
            )

            effective_page_size = page_size if page_size > 0 else 50
            docs, total_count = fetch_paginated_jobs_sync(
                query=query,
                page=page,
                page_size=effective_page_size,
            )

            if total_count == 0 and not query:
                # If collection is empty, fallback to local file
                return None

            tracker_data = self.tracker._load_data()
            tracker_map = {app["job_id"]: app for app in tracker_data.get("applications", [])}

            # Fast deterministic scoring setup (zero LLM calls)
            resume = None
            prefs = None
            scorer = None
            try:
                from src.resume_parser import ResumeParser, load_preferences
                from src.scorer import Scorer
                resume = ResumeParser().parse()
                prefs = load_preferences()
                scorer = Scorer()
            except Exception as e:
                logger.debug("Scoring context load failed: %s", e)

            enriched = []
            for doc in docs:
                job_id = doc.get("id") or doc.get("_id")
                output_dir = settings.output_dir / job_id
                has_tailored = (output_dir / "resume.pdf").exists()

                # Calculate quick match score deterministically
                match_score = 0.5
                if scorer and resume and prefs:
                    try:
                        from src.models.job_listing import JobListing
                        jl = JobListing(
                            id=job_id,
                            ats_source=doc.get("ats_source", "direct"),
                            company=doc.get("company", "Unknown"),
                            company_slug=doc.get("company_slug", ""),
                            title=doc.get("title", ""),
                            location=doc.get("location", ""),
                            locations=doc.get("locations", []),
                            remote=bool(doc.get("remote", False)),
                            workplace_type=doc.get("workplace_type"),
                            employment_type=doc.get("employment_type"),
                            experience_level=doc.get("experience_level"),
                            department=doc.get("department"),
                            team=doc.get("team"),
                            country=doc.get("country"),
                            description_html=doc.get("description_html", ""),
                            description_text=doc.get("description_text", ""),
                            application_url=doc.get("application_url", ""),
                            job_url=doc.get("job_url"),
                            salary_raw=doc.get("salary", {}).get("raw") if isinstance(doc.get("salary"), dict) else doc.get("salary"),
                            has_equity=bool(doc.get("has_equity", False)),
                            api_posting_id=str(job_id),
                        )
                        qs = scorer.quick_score(jl, resume, prefs)
                        match_score = round(qs.composite_score, 2)
                    except Exception as e:
                        logger.debug("Quick score calculation failed for %s: %s", job_id, e)

                salary_obj = doc.get("salary") if isinstance(doc.get("salary"), dict) else {}
                salary_display = salary_obj.get("raw") or "Not listed"

                enriched.append({
                    **doc,
                    "id": job_id,
                    "score": match_score,
                    "role_fit": doc.get("role_fit", ""),
                    "key_gaps": doc.get("key_gaps", []),
                    "recommendation": doc.get("recommendation", "candidate"),
                    "salary": salary_display,
                    "salary_range": {
                        "min": salary_obj.get("min"),
                        "max": salary_obj.get("max"),
                        "currency": salary_obj.get("currency", "USD"),
                        "period": salary_obj.get("period", "year"),
                    },
                    "has_equity": bool(doc.get("has_equity", False)),
                    "red_flag_verdict": doc.get("red_flag_verdict", "clean"),
                    "has_tailored_resume": has_tailored,
                    "tracker_status": tracker_map.get(job_id, {}).get("status"),
                })

            if min_score > 0:
                enriched = [j for j in enriched if (j.get("score") or 0) >= min_score]

            total_pages = (total_count + effective_page_size - 1) // effective_page_size if effective_page_size > 0 else 1

            return {
                "jobs": enriched,
                "total": total_count,
                "page": page,
                "page_size": effective_page_size,
                "total_pages": total_pages,
                "source": "mongodb",
                "suggestions": {},
            }
        except Exception as e:
            logger.warning("MongoDB query attempt failed, using local JSON fallback: %s", e)
            return None

    def _get_jobs_from_local(
        self,
        search: str | None = None,
        min_score: float = 0.0,
        page: int = 1,
        page_size: int = 0,
    ) -> dict[str, Any]:
        """Load, sanitize HTML, enrich with salaries/red-flags/tracker, and return jobs from local scan."""
        last_scan_path = settings.data_dir / "last_scan.json"
        if not last_scan_path.exists():
            return {"jobs": [], "total": 0, "suggestions": []}

        try:
            data = json.loads(last_scan_path.read_text(encoding="utf-8"))
            raw_jobs = data.get("jobs", [])
            deep_scores = data.get("deep_scores", {})
        except Exception as e:
            logger.error("Error loading last_scan.json: %s", e)
            return {"jobs": [], "total": 0, "suggestions": []}

        tracker_data = self.tracker._load_data()
        tracker_map = {app["job_id"]: app for app in tracker_data.get("applications", [])}

        enriched_jobs = []
        for j in raw_jobs:
            job_id = j.get("id")
            ds = deep_scores.get(job_id, {})

            # Clean and unescape HTML — handle multi-pass encoding
            desc_html = j.get("description_html") or ""
            passes = 3
            while passes > 0 and ("&lt;" in desc_html or "&amp;lt;" in desc_html or "&amp;amp;" in desc_html):
                unescaped = html.unescape(desc_html)
                if unescaped == desc_html:
                    break
                desc_html = unescaped
                passes -= 1

            # Clean description_text — strip leaked HTML tags
            desc_text = j.get("description_text") or ""
            if desc_text:
                passes = 3
                while passes > 0 and ("&lt;" in desc_text or "&amp;" in desc_text):
                    unescaped = html.unescape(desc_text)
                    if unescaped == desc_text:
                        break
                    desc_text = unescaped
                    passes -= 1
                if any(tag in desc_text for tag in ["<div", "<p", "<br", "<li"]):
                    desc_text = BeautifulSoup(desc_text, "html.parser").get_text("\n", strip=True)

            if not desc_text and desc_html:
                desc_text = BeautifulSoup(desc_html, "html.parser").get_text("\n", strip=True)

            j["description_html"] = desc_html
            j["description_text"] = desc_text

            desc = desc_text or desc_html
            meta = dict(j.get("metadata") or {})
            if j.get("salary_raw"):
                meta["salary_raw"] = j["salary_raw"]
                if isinstance(j["salary_raw"], list):
                    meta["payRangeDetails"] = j["salary_raw"]
                elif isinstance(j["salary_raw"], dict):
                    meta["compensation"] = j["salary_raw"]

            salary = SalaryExtractor.extract(desc, meta)
            red_flags = RedFlagDetector.scan(desc, j.get("title", ""))
            flag_summary = RedFlagDetector.summarize(red_flags)

            output_dir = settings.output_dir / job_id
            has_tailored = (output_dir / "resume.pdf").exists()

            enriched_jobs.append({
                **j,
                "score": ds.get("semantic_match", 0.5),
                "role_fit": ds.get("role_fit", ""),
                "key_gaps": ds.get("key_gaps", []),
                "recommendation": ds.get("recommendation", "weak_match"),
                "salary": salary.display if salary.display != "Not listed" else j.get("salary", "Not listed"),
                "salary_range": {
                    "min": salary.min_salary,
                    "max": salary.max_salary,
                    "currency": salary.currency,
                    "period": salary.period,
                },
                "red_flags": [f.to_dict() for f in red_flags],
                "red_flag_count": flag_summary.get("total", 0),
                "red_flag_verdict": flag_summary.get("verdict", "clean"),
                "has_tailored_resume": has_tailored,
                "tracker_status": tracker_map.get(job_id, {}).get("status"),
            })

        # Apply filters
        if min_score > 0:
            enriched_jobs = [j for j in enriched_jobs if (j.get("score") or 0) >= min_score]

        if search:
            q = search.lower()
            enriched_jobs = [
                j for j in enriched_jobs
                if q in j.get("title", "").lower()
                or q in j.get("company", "").lower()
                or q in j.get("location", "").lower()
                or q in j.get("ats_source", "").lower()
            ]

        total = len(enriched_jobs)
        if page_size > 0:
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_jobs = enriched_jobs[start_idx:end_idx]
        else:
            paginated_jobs = enriched_jobs

        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1

        # Generate role suggestions
        suggestions: dict[str, Any] = {}
        try:
            from src.resume_parser import load_preferences
            prefs = load_preferences()
            seen_titles = [j.get("title", "") for j in raw_jobs]
            suggestions = RoleSuggester.suggest(prefs.target_roles, seen_titles)
        except Exception as e:
            logger.debug("Failed to generate role suggestions: %s", e)

        return {
            "jobs": paginated_jobs,
            "total": total,
            "page": page,
            "page_size": page_size or total,
            "total_pages": total_pages,
            "source": "local_json",
            "suggestions": suggestions,
        }

    def get_job_output(self, job_id: str) -> dict[str, Any]:
        """Fetch generated assets and analysis for a tailored job."""
        output_folder = settings.output_dir / job_id
        if not output_folder.exists():
            return {"exists": False}

        result: dict[str, Any] = {"exists": True, "job_id": job_id}

        pdf_path = output_folder / "resume.pdf"
        html_path = output_folder / "resume.html"
        cl_txt_path = output_folder / "cover_letter.txt"
        cl_html_path = output_folder / "cover_letter.html"
        analysis_path = output_folder / "job_analysis.json"
        match_path = output_folder / "match_report.json"
        val_path = output_folder / "validation_report.json"
        summary_path = output_folder / "change_summary.md"
        red_flags_path = output_folder / "red_flags.json"
        company_path = output_folder / "company_brief.json"
        salary_path = output_folder / "salary_info.json"
        url_path = output_folder / "application_url.txt"

        result["has_pdf"] = pdf_path.exists()
        result["has_html"] = html_path.exists()
        result["has_cover_letter"] = cl_txt_path.exists()

        if cl_txt_path.exists():
            result["cover_letter_txt"] = cl_txt_path.read_text(encoding="utf-8")
        if cl_html_path.exists():
            result["cover_letter_html"] = cl_html_path.read_text(encoding="utf-8")
        if analysis_path.exists():
            result["job_analysis"] = json.loads(analysis_path.read_text(encoding="utf-8"))
        if match_path.exists():
            result["match_report"] = json.loads(match_path.read_text(encoding="utf-8"))
        if val_path.exists():
            result["validation_report"] = json.loads(val_path.read_text(encoding="utf-8"))
        if summary_path.exists():
            result["change_summary"] = summary_path.read_text(encoding="utf-8")
        if red_flags_path.exists():
            result["red_flags"] = json.loads(red_flags_path.read_text(encoding="utf-8"))
        if company_path.exists():
            result["company_brief"] = json.loads(company_path.read_text(encoding="utf-8"))
        if salary_path.exists():
            result["salary_info"] = json.loads(salary_path.read_text(encoding="utf-8"))
        if url_path.exists():
            result["application_urls"] = url_path.read_text(encoding="utf-8")

        return result
