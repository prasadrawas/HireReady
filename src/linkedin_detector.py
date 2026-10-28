"""LinkedIn Easy Apply URL detector for job listings."""

import logging
import re
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class LinkedInDetector:
    """Detect and construct LinkedIn job search/apply URLs for matched listings."""

    LINKEDIN_SEARCH_URL = "https://www.linkedin.com/jobs/search/"

    @classmethod
    def build_search_url(cls, company: str, title: str) -> str:
        """Build a LinkedIn job search URL scoped to company and role."""
        keywords = quote_plus(f"{title} {company}")
        return f"{cls.LINKEDIN_SEARCH_URL}?keywords={keywords}&f_AL=true"

    @classmethod
    def build_company_search_url(cls, company: str, title: str) -> str:
        """Build a LinkedIn search URL without Easy Apply filter."""
        keywords = quote_plus(f"{title}")
        company_encoded = quote_plus(company)
        return f"{cls.LINKEDIN_SEARCH_URL}?keywords={keywords}&company={company_encoded}"

    @classmethod
    def extract_linkedin_url_from_jd(cls, description_text: str) -> str | None:
        """Try to find a LinkedIn job URL embedded in the JD text."""
        patterns = [
            r"https?://(?:www\.)?linkedin\.com/jobs/view/\d+",
            r"https?://(?:www\.)?linkedin\.com/jobs/\d+",
        ]
        for pattern in patterns:
            match = re.search(pattern, description_text)
            if match:
                return match.group(0)
        return None

    @classmethod
    def get_linkedin_info(cls, company: str, title: str, description_text: str = "") -> dict:
        """Get LinkedIn URLs for a job listing.

        Returns a dict with:
        - linkedin_easy_apply_search: URL to LinkedIn search filtered for Easy Apply
        - linkedin_job_search: URL to LinkedIn search for this role at this company
        - linkedin_direct_url: Direct LinkedIn job URL if found in JD text (or None)
        """
        direct_url = cls.extract_linkedin_url_from_jd(description_text) if description_text else None

        return {
            "linkedin_easy_apply_search": cls.build_search_url(company, title),
            "linkedin_job_search": cls.build_company_search_url(company, title),
            "linkedin_direct_url": direct_url,
        }
