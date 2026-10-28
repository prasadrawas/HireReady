"""Job alerts: notifications for new high-match jobs found during scans."""

import json
import logging
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


class JobAlertManager:
    """Manages job alert notifications and alert history."""

    def __init__(self, alerts_path: Path | None = None):
        self.alerts_path = alerts_path or (settings.data_dir / "alerts.json")

    def _load_alerts(self) -> list[dict[str, Any]]:
        if not self.alerts_path.exists():
            return []
        try:
            with open(self.alerts_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_alerts(self, alerts: list[dict[str, Any]]):
        self.alerts_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.alerts_path, "w", encoding="utf-8") as f:
            json.dump(alerts, f, indent=2, default=str)

    def send_alerts(
        self,
        jobs: list[dict[str, Any]],
        min_score: float = 0.7,
        notify: bool = True,
    ) -> list[dict[str, Any]]:
        """Send alerts for high-match jobs. Returns list of alerted jobs.

        Args:
            jobs: List of dicts with keys: company, title, score, application_url, job_id
            min_score: Minimum match score to trigger an alert (0.0-1.0)
            notify: Whether to send desktop notifications
        """
        high_match = [j for j in jobs if j.get("score", 0) >= min_score]
        if not high_match:
            return []

        alerts = self._load_alerts()

        alerted = []
        for job in high_match:
            alert_record = {
                "job_id": job.get("job_id", ""),
                "company": job.get("company", ""),
                "title": job.get("title", ""),
                "score": job.get("score", 0),
                "application_url": job.get("application_url", ""),
                "alerted_at": datetime.now().isoformat(),
            }
            alerts.append(alert_record)
            alerted.append(alert_record)

        self._save_alerts(alerts)

        if notify and alerted:
            self._send_desktop_notification(alerted)

        return alerted

    def _send_desktop_notification(self, jobs: list[dict[str, Any]]):
        """Send a desktop notification about new high-match jobs."""
        count = len(jobs)
        if count == 1:
            job = jobs[0]
            title = "HireReady: New Job Match!"
            body = f"{job['company']} — {job['title']} ({int(job['score'] * 100)}% match)"
        else:
            title = f"HireReady: {count} New Job Matches!"
            lines = [f"  {j['company']} — {j['title']} ({int(j['score'] * 100)}%)" for j in jobs[:5]]
            body = "\n".join(lines)
            if count > 5:
                body += f"\n  ... and {count - 5} more"

        system = platform.system()
        try:
            if system == "Darwin":
                # macOS notification
                script = f'display notification "{body}" with title "{title}"'
                subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    timeout=5,
                )
            elif system == "Linux":
                subprocess.run(
                    ["notify-send", title, body],
                    capture_output=True,
                    timeout=5,
                )
            # Windows: could use win10toast or plyer, skip for now
            logger.info("Desktop notification sent: %s", title)
        except Exception as e:
            logger.debug("Failed to send desktop notification: %s", e)

    def get_alert_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent alert history."""
        alerts = self._load_alerts()
        return alerts[-limit:]


def generate_cron_command(python_path: str | None = None, project_dir: str | None = None) -> str:
    """Generate a cron line for daily job scanning.

    Usage: Add the output to your crontab with `crontab -e`
    """
    proj = project_dir or str(settings.base_dir)
    py = python_path or f"{proj}/venv/bin/python"

    # Run daily at 8:00 AM
    return f"0 8 * * * cd {proj} && {py} main.py scan --auto-tailor-top 3 >> {proj}/data/cron.log 2>&1"
