"""Ashby ATS client implementation."""

from datetime import datetime
import logging
from bs4 import BeautifulSoup

from src.ats.base import BaseATSClient, generate_job_id
from src.models.job_listing import JobListing

logger = logging.getLogger(__name__)


class AshbyClient(BaseATSClient):
    """Client for fetching jobs from Ashby Posting API."""

    BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"

    async def fetch_jobs(self, company_slug: str, company_name: str) -> list[JobListing]:
        """Fetch listings from Ashby API for given company slug."""
        url = f"{self.BASE_URL}/{company_slug}?includeCompensation=true"
        await self._rate_limit()

        try:
            response = await self.client.get(url)
            if response.status_code == 404:
                logger.debug("Ashby board not found for %s (%s)", company_name, company_slug)
                return []
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.debug("Failed to fetch Ashby jobs for %s: %s", company_name, e)
            return []

        # Ashby can return list of jobs or {"jobs": [...]} or {"postings": [...]}
        if isinstance(data, dict):
            postings = data.get("jobs") or data.get("postings") or []
        elif isinstance(data, list):
            postings = data
        else:
            postings = []

        jobs: list[JobListing] = []
        for p in postings:
            try:
                posting_id = str(p.get("id", ""))
                title = p.get("title", "").strip()
                if not posting_id or not title:
                    continue

                location = p.get("locationName") or p.get("location") or ""
                if isinstance(location, dict):
                    location = location.get("name", "")

                department = p.get("departmentName") or p.get("department")
                if isinstance(department, dict):
                    department = department.get("name")

                employment_type = p.get("employmentType")

                # Remote detection
                is_remote_flag = p.get("isRemote", False)
                loc_lower = str(location).lower()
                title_lower = title.lower()
                remote = bool(is_remote_flag or "remote" in loc_lower or "remote" in title_lower)

                apply_url = (
                    p.get("applyUrl")
                    or p.get("applicationUrl")
                    or p.get("jobUrl")
                    or f"https://jobs.ashbyhq.com/{company_slug}/{posting_id}/application"
                )

                # Date parsing
                published_at_str = p.get("publishedAt") or p.get("updatedAt")
                posted_date = None
                if published_at_str:
                    try:
                        posted_date = datetime.fromisoformat(published_at_str.replace("Z", "+00:00")).date()
                    except Exception:
                        posted_date = None

                desc_html = p.get("descriptionHtml", "") or ""
                plain_desc = p.get("descriptionPlain") or ""
                if not plain_desc and desc_html:
                    plain_desc = BeautifulSoup(desc_html, "html.parser").get_text("\n", strip=True)

                job_id = generate_job_id(company_slug, title, posting_id)

                jobs.append(
                    JobListing(
                        id=job_id,
                        ats_source="ashby",
                        company=company_name,
                        company_slug=company_slug,
                        title=title,
                        location=str(location) or ("Remote" if remote else "Unspecified"),
                        remote=remote,
                        department=str(department) if department else None,
                        posted_date=posted_date,
                        description_html=desc_html,
                        description_text=plain_desc,
                        application_url=apply_url,
                        api_posting_id=posting_id,
                        metadata={"employment_type": employment_type},
                        first_seen=datetime.now(),
                    )
                )
            except Exception as e:
                logger.debug("Error parsing Ashby job: %s", e)
                continue

        return jobs
