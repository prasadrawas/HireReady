"""Greenhouse ATS client implementation."""

from datetime import datetime
import html
import logging
from bs4 import BeautifulSoup

from src.ats.base import BaseATSClient, generate_job_id
from src.models.job_listing import JobListing

logger = logging.getLogger(__name__)


class GreenhouseClient(BaseATSClient):
    """Client for fetching jobs from Greenhouse Boards API."""

    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    async def fetch_jobs(self, company_slug: str, company_name: str) -> list[JobListing]:
        """Fetch listings from Greenhouse API for given company slug."""
        url = f"{self.BASE_URL}/{company_slug}/jobs?content=true"
        await self._rate_limit()

        try:
            response = await self.client.get(url)
            if response.status_code == 404:
                logger.debug("Greenhouse board not found for %s (%s)", company_name, company_slug)
                return []
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.debug("Failed to fetch Greenhouse jobs for %s: %s", company_name, e)
            return []

        postings = data.get("jobs", []) if isinstance(data, dict) else []
        jobs: list[JobListing] = []

        for p in postings:
            try:
                posting_id = str(p.get("id", ""))
                title = p.get("title", "").strip()
                if not posting_id or not title:
                    continue

                location_info = p.get("location", {}) or {}
                location = location_info.get("name", "") if isinstance(location_info, dict) else str(location_info)

                # Department
                department = None
                departments = p.get("departments", [])
                if departments and isinstance(departments, list) and len(departments) > 0:
                    department = departments[0].get("name") if isinstance(departments[0], dict) else str(departments[0])

                # Remote detection
                loc_lower = location.lower()
                title_lower = title.lower()
                remote = "remote" in loc_lower or "remote" in title_lower

                apply_url = p.get("absolute_url") or f"https://boards.greenhouse.io/{company_slug}/jobs/{posting_id}"

                # Date parsing
                updated_at_str = p.get("updated_at")
                posted_date = None
                if updated_at_str:
                    try:
                        posted_date = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00")).date()
                    except Exception:
                        posted_date = None

                raw_content = p.get("content", "") or ""
                desc_html = html.unescape(raw_content)
                if "&lt;" in desc_html:
                    desc_html = html.unescape(desc_html)
                plain_desc = BeautifulSoup(desc_html, "html.parser").get_text("\n", strip=True) if desc_html else ""

                job_id = generate_job_id(company_slug, title, posting_id)

                jobs.append(
                    JobListing(
                        id=job_id,
                        ats_source="greenhouse",
                        company=company_name,
                        company_slug=company_slug,
                        title=title,
                        location=location or ("Remote" if remote else "Unspecified"),
                        remote=remote,
                        department=department,
                        posted_date=posted_date,
                        description_html=desc_html,
                        description_text=plain_desc,
                        application_url=apply_url,
                        api_posting_id=posting_id,
                        metadata={"offices": p.get("offices", [])},
                        first_seen=datetime.now(),
                    )
                )
            except Exception as e:
                logger.debug("Error parsing Greenhouse job: %s", e)
                continue

        return jobs
