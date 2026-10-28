"""Lever ATS client implementation."""

from datetime import date, datetime
import logging
from bs4 import BeautifulSoup

from src.ats.base import BaseATSClient, generate_job_id
from src.models.job_listing import JobListing

logger = logging.getLogger(__name__)


class LeverClient(BaseATSClient):
    """Client for fetching jobs from Lever API."""

    BASE_URL = "https://api.lever.co/v0/postings"

    async def fetch_jobs(self, company_slug: str, company_name: str) -> list[JobListing]:
        """Fetch listings from Lever API for given company slug."""
        url = f"{self.BASE_URL}/{company_slug}?mode=json"
        await self._rate_limit()

        try:
            response = await self.client.get(url)
            if response.status_code == 404:
                logger.debug("Lever board not found for %s (%s)", company_name, company_slug)
                return []
            response.raise_for_status()
            postings = response.json()
        except Exception as e:
            logger.debug("Failed to fetch Lever jobs for %s: %s", company_name, e)
            return []

        if not isinstance(postings, list):
            logger.debug("Unexpected Lever response format for %s", company_name)
            return []

        jobs: list[JobListing] = []
        for p in postings:
            try:
                posting_id = str(p.get("id", ""))
                title = p.get("text", "").strip()
                if not posting_id or not title:
                    continue

                categories = p.get("categories", {}) or {}
                location = categories.get("location", "") or ""
                department = categories.get("department") or categories.get("team")
                commitment = categories.get("commitment", "")

                # Detect remote
                loc_lower = location.lower()
                title_lower = title.lower()
                remote = "remote" in loc_lower or "remote" in title_lower

                # Application URL
                apply_url = p.get("applyUrl") or f"https://jobs.lever.co/{company_slug}/{posting_id}/apply"

                # Dates
                created_at_ms = p.get("createdAt")
                posted_date = None
                if created_at_ms:
                    try:
                        posted_date = datetime.fromtimestamp(created_at_ms / 1000.0).date()
                    except Exception:
                        posted_date = None

                # HTML description
                desc_html = p.get("description", "")
                if p.get("additional"):
                    desc_html += f"\n<div>{p.get('additional')}</div>"

                # Clean text description
                plain_desc = p.get("descriptionPlain") or ""
                if not plain_desc and desc_html:
                    plain_desc = BeautifulSoup(desc_html, "html.parser").get_text("\n", strip=True)

                job_id = generate_job_id(company_slug, title, posting_id)

                jobs.append(
                    JobListing(
                        id=job_id,
                        ats_source="lever",
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
                        metadata={"commitment": commitment, "hosted_url": p.get("hostedUrl")},
                        first_seen=datetime.now(),
                    )
                )
            except Exception as e:
                logger.debug("Error parsing Lever posting: %s", e)
                continue

        return jobs
