"""API Service facade coordinating domain services for FastAPI routes."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator

from config.settings import settings
from src.ats.aggregator import ATSAggregator
from src.models.job_listing import JobListing
from src.models.resume import ResumeData
from src.resume_parser import ResumeParser
from src.services.config_service import ConfigService
from src.services.job_query_service import JobQueryService
from src.services.scan_service import ScanService
from src.services.tailoring_service import TailoringService
from src.tracker import ApplicationTracker

logger = logging.getLogger("hireready.api.service")


class APIService:
    """Facade providing high-level operations for the web API by delegating to specialized services."""

    def __init__(
        self,
        config_service: ConfigService | None = None,
        job_query_service: JobQueryService | None = None,
        tailoring_service: TailoringService | None = None,
        scan_service: ScanService | None = None,
        tracker: ApplicationTracker | None = None,
    ):
        self.tracker = tracker or ApplicationTracker()
        self.config_service = config_service or ConfigService()
        self.job_query_service = job_query_service or JobQueryService(tracker=self.tracker)
        self.tailoring_service = tailoring_service or TailoringService(tracker=self.tracker)
        self.aggregator = ATSAggregator()
        self.scan_service = scan_service or ScanService(aggregator=self.aggregator)

    # --- Resume ---

    def get_resume(self) -> ResumeData:
        """Parse and return master resume data."""
        return ResumeParser().parse()

    # --- Preferences & ATS Company Config ---

    def get_preferences(self) -> dict[str, Any]:
        """Fetch search preferences."""
        return self.config_service.get_preferences()

    def update_preferences(self, data: dict[str, Any]) -> dict[str, Any]:
        """Update search preferences."""
        return self.config_service.update_preferences(data)

    def get_ats_companies(self) -> dict[str, Any]:
        """Fetch configured ATS company links."""
        return self.config_service.get_ats_companies()

    def add_ats_link(
        self,
        url: str | None = None,
        platform: str | None = None,
        company_slug: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Add an ATS company link."""
        return self.config_service.add_ats_link(url, platform, company_slug, name)

    def delete_ats_company(self, platform: str, company_slug: str) -> dict[str, Any]:
        """Remove an ATS company configuration."""
        return self.config_service.delete_ats_company(platform, company_slug)

    # --- Jobs & Output Queries ---

    def get_jobs(self) -> dict[str, Any]:
        """Fetch enriched, cleaned job listings from last scan."""
        return self.job_query_service.get_jobs()

    def get_job_output(self, job_id: str) -> dict[str, Any]:
        """Fetch generated artifacts for a tailored job."""
        return self.job_query_service.get_job_output(job_id)

    # --- Tracker ---

    def get_tracker(self) -> dict[str, Any]:
        """Load raw application tracker data."""
        return self.tracker._load_data()

    def update_tracker(self, job_id: str, status: str, notes: str | None = None) -> dict[str, Any]:
        """Update tracker stage and notes for an application."""
        jobs_data = self.get_jobs()
        job = next((j for j in jobs_data["jobs"] if j["id"] == job_id), None)

        data = self.tracker._load_data()
        apps = data.get("applications", [])
        app = next((a for a in apps if a.get("job_id") == job_id), None)

        if app:
            app["status"] = status
            app["updated_at"] = datetime.now().isoformat()
            if notes:
                app.setdefault("notes", []).append({
                    "text": notes,
                    "created_at": datetime.now().isoformat(),
                })
            if status == "submitted":
                app["submitted_at"] = datetime.now().isoformat()
            self.tracker._save_data(data)
        elif job:
            self.tracker.record_application(
                job_id=job_id,
                company=job.get("company", ""),
                title=job.get("title", ""),
                application_url=job.get("application_url", ""),
                output_dir="",
                coverage_score=0.0,
                validation_passed=False,
                needs_review_count=0,
                status=status,
                salary=job.get("salary", ""),
                linkedin_url="",
            )
            data = self.tracker._load_data()

        return data

    def delete_tracker(self, job_id: str) -> dict[str, Any]:
        """Delete a tracked application."""
        data = self.tracker._load_data()
        data["applications"] = [a for a in data.get("applications", []) if a.get("job_id") != job_id]
        self.tracker._save_data(data)
        return data

    # --- Tailoring ---

    def tailor_job(self, job_id: str, generate_cover_letter: bool = False) -> dict[str, Any]:
        """Execute resume tailoring pipeline for a job."""
        jobs_data = self.get_jobs()
        job_dict = next((j for j in jobs_data["jobs"] if j["id"] == job_id), None)
        if not job_dict:
            raise ValueError(f"Job {job_id} not found in recent scan results.")

        resume = self.get_resume()
        job = JobListing.model_validate(job_dict)

        self.tailoring_service.tailor(job, resume, generate_cover_letter=generate_cover_letter)
        return self.get_job_output(job.id)

    # --- Auto-Apply ---

    def auto_apply_job(
        self,
        job_id: str,
        headed: bool = True,
        auto_submit: bool = False,
        review_timeout_sec: int = 15,
    ) -> dict[str, Any]:
        """Execute Playwright automated application workflow for a job listing."""
        from src.auto_apply.runner import AutoApplyRunner
        runner = AutoApplyRunner(service=self, tracker=self.tracker)
        return runner.apply(
            job_id=job_id,
            headed=headed,
            auto_submit=auto_submit,
            review_timeout_sec=review_timeout_sec,
        )

    # --- Scan Streaming ---

    async def scan_stream(self) -> AsyncGenerator[str, None]:
        """Stream scan execution progress via Server-Sent Events."""
        try:
            resume = self.get_resume()
        except Exception as e:
            logger.error("Failed to load resume for scanning: %s", e)
            import json
            yield json.dumps({"type": "error", "message": f"Resume error: {e}"})
            return

        async for event in self.scan_service.stream_scan(resume):
            yield event
