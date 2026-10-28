"""Application status tracking module with follow-up reminders and interview stage tracking."""

from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)

# Interview pipeline stages in order
STAGES = [
    "ready_for_review",
    "approved",
    "submitted",
    "applied",
    "recruiter_screen",
    "phone_interview",
    "technical_interview",
    "onsite_interview",
    "final_round",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
    "no_response",
    "validation_failed",
]

# Default follow-up intervals (days after submission)
DEFAULT_FOLLOWUP_DAYS = [7, 14, 21]


class ApplicationTracker:
    """Manages application statuses, interview stages, and follow-up reminders."""

    def __init__(self, tracker_path: Path | str | None = None):
        self.tracker_path = Path(tracker_path) if tracker_path else settings.tracker_path

    def _load_data(self) -> dict[str, list[dict[str, Any]]]:
        """Load tracker JSON data."""
        if not self.tracker_path.exists():
            return {"applications": []}
        try:
            with open(self.tracker_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict) or "applications" not in data:
                    return {"applications": []}
                return data
        except Exception as e:
            logger.warning("Error reading tracker.json: %s. Reinitializing.", e)
            return {"applications": []}

    def _save_data(self, data: dict[str, Any]):
        """Save tracker JSON data."""
        self.tracker_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tracker_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def record_application(
        self,
        job_id: str,
        company: str,
        title: str,
        application_url: str,
        output_dir: str | Path,
        coverage_score: float = 0.0,
        validation_passed: bool = False,
        needs_review_count: int = 0,
        status: str = "ready_for_review",
        salary: str | None = None,
        linkedin_url: str | None = None,
    ) -> dict[str, Any]:
        """Insert or update an application record."""
        data = self._load_data()
        apps = data.get("applications", [])
        now_str = datetime.now().isoformat()

        # Check if already present
        found = False
        record = {}
        for app in apps:
            if app.get("job_id") == job_id:
                app.update({
                    "company": company,
                    "title": title,
                    "application_url": application_url,
                    "output_dir": str(output_dir),
                    "coverage_score": coverage_score,
                    "validation_passed": validation_passed,
                    "needs_review_count": needs_review_count,
                    "status": status,
                    "updated_at": now_str,
                })
                if salary:
                    app["salary"] = salary
                if linkedin_url:
                    app["linkedin_url"] = linkedin_url
                found = True
                record = app
                break

        if not found:
            record = {
                "job_id": job_id,
                "company": company,
                "title": title,
                "application_url": application_url,
                "output_dir": str(output_dir),
                "coverage_score": coverage_score,
                "validation_passed": validation_passed,
                "needs_review_count": needs_review_count,
                "status": status,
                "salary": salary or "Not listed",
                "linkedin_url": linkedin_url,
                "created_at": now_str,
                "updated_at": now_str,
                "submitted_at": None,
                "followup_dates": [],
                "interview_stages": [],
                "notes": [],
            }
            apps.append(record)

        data["applications"] = apps
        self._save_data(data)
        return record

    def mark_submitted(self, job_id_or_prefix: str) -> bool:
        """Mark an application as submitted and set follow-up reminder dates."""
        data = self._load_data()
        updated = False
        now = datetime.now()

        for app in data.get("applications", []):
            jid = app.get("job_id", "")
            if jid == job_id_or_prefix or jid.startswith(job_id_or_prefix):
                app["status"] = "submitted"
                app["submitted_at"] = now.isoformat()
                app["updated_at"] = now.isoformat()
                # Set follow-up dates
                app["followup_dates"] = [
                    {
                        "date": (now + timedelta(days=d)).strftime("%Y-%m-%d"),
                        "days_after": d,
                        "completed": False,
                    }
                    for d in DEFAULT_FOLLOWUP_DAYS
                ]
                updated = True
                break

        if updated:
            self._save_data(data)
        return updated

    def add_interview_stage(
        self,
        job_id_or_prefix: str,
        stage: str,
        date: str | None = None,
        notes: str = "",
    ) -> bool:
        """Add an interview stage to an application's pipeline."""
        data = self._load_data()
        updated = False

        for app in data.get("applications", []):
            jid = app.get("job_id", "")
            if jid == job_id_or_prefix or jid.startswith(job_id_or_prefix):
                if "interview_stages" not in app:
                    app["interview_stages"] = []
                app["interview_stages"].append({
                    "stage": stage,
                    "date": date or datetime.now().strftime("%Y-%m-%d"),
                    "notes": notes,
                    "added_at": datetime.now().isoformat(),
                })
                app["status"] = stage
                app["updated_at"] = datetime.now().isoformat()
                updated = True
                break

        if updated:
            self._save_data(data)
        return updated

    def add_note(self, job_id_or_prefix: str, note: str) -> bool:
        """Add a note to an application."""
        data = self._load_data()
        updated = False

        for app in data.get("applications", []):
            jid = app.get("job_id", "")
            if jid == job_id_or_prefix or jid.startswith(job_id_or_prefix):
                if "notes" not in app:
                    app["notes"] = []
                app["notes"].append({
                    "text": note,
                    "added_at": datetime.now().isoformat(),
                })
                app["updated_at"] = datetime.now().isoformat()
                updated = True
                break

        if updated:
            self._save_data(data)
        return updated

    def complete_followup(self, job_id_or_prefix: str, followup_index: int = 0) -> bool:
        """Mark a follow-up as completed."""
        data = self._load_data()
        updated = False

        for app in data.get("applications", []):
            jid = app.get("job_id", "")
            if jid == job_id_or_prefix or jid.startswith(job_id_or_prefix):
                followups = app.get("followup_dates", [])
                if 0 <= followup_index < len(followups):
                    followups[followup_index]["completed"] = True
                    followups[followup_index]["completed_at"] = datetime.now().isoformat()
                    app["updated_at"] = datetime.now().isoformat()
                    updated = True
                break

        if updated:
            self._save_data(data)
        return updated

    def get_pending_followups(self) -> list[dict[str, Any]]:
        """Get all applications with pending follow-ups that are due."""
        data = self._load_data()
        today = datetime.now().strftime("%Y-%m-%d")
        pending = []

        for app in data.get("applications", []):
            if app.get("status") in ("rejected", "withdrawn", "accepted", "no_response"):
                continue
            for fu in app.get("followup_dates", []):
                if not fu.get("completed") and fu.get("date", "") <= today:
                    pending.append({
                        "job_id": app.get("job_id"),
                        "company": app.get("company"),
                        "title": app.get("title"),
                        "application_url": app.get("application_url"),
                        "followup_date": fu.get("date"),
                        "days_after": fu.get("days_after"),
                    })
        return pending

    def list_applications(self, status: str | None = None) -> list[dict[str, Any]]:
        """List applications, optionally filtered by status."""
        data = self._load_data()
        apps = data.get("applications", [])
        if status:
            return [a for a in apps if a.get("status") == status]
        return apps

    def get_application(self, job_id_or_prefix: str) -> dict[str, Any] | None:
        """Find an application by job_id or matching prefix."""
        data = self._load_data()
        for app in data.get("applications", []):
            jid = app.get("job_id", "")
            if jid == job_id_or_prefix or jid.startswith(job_id_or_prefix):
                return app
        return None

    def update_status(self, job_id_or_prefix: str, new_status: str) -> bool:
        """Update status of a tracked application."""
        data = self._load_data()
        updated = False
        for app in data.get("applications", []):
            jid = app.get("job_id", "")
            if jid == job_id_or_prefix or jid.startswith(job_id_or_prefix):
                app["status"] = new_status
                app["updated_at"] = datetime.now().isoformat()
                updated = True
                break
        if updated:
            self._save_data(data)
        return updated

    def get_pipeline_summary(self) -> dict[str, int]:
        """Get count of applications by stage for funnel view."""
        data = self._load_data()
        counts: dict[str, int] = {}
        for app in data.get("applications", []):
            status = app.get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1
        return counts
