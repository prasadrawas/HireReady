"""Abstract base class for ATS clients."""

from abc import ABC, abstractmethod
import asyncio
import hashlib
import re
from typing import Any
import httpx
from src.models.job_listing import JobListing


def slugify(text: str) -> str:
    """Normalize string to URL and filename friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def generate_job_id(company_slug: str, title: str, posting_id: str) -> str:
    """Generate unique deterministic hash ID: {company_slug}_{role_slug}_{id_hash}."""
    slug_company = slugify(company_slug)
    slug_title = slugify(title) or "role"
    hash_digest = hashlib.sha256(f"{slug_company}:{posting_id}".encode("utf-8")).hexdigest()[:8]
    return f"{slug_company}_{slug_title}_{hash_digest}"


def parse_ats_url(url: str, custom_name: str | None = None) -> tuple[str, str, str] | None:
    """Parse any ATS job board URL into (ats_platform, slug, company_name).

    Supported formats:
    - Lever: https://jobs.lever.co/{slug} or https://api.lever.co/v0/postings/{slug}
    - Greenhouse: https://boards.greenhouse.io/{slug}, https://job-boards.greenhouse.io/{slug}, or ?for={slug}
    - Ashby: https://jobs.ashbyhq.com/{slug} or https://api.ashbyhq.com/posting-api/job-board/{slug}
    - Workable: https://apply.workable.com/{slug}
    - SmartRecruiters: https://jobs.smartrecruiters.com/{slug}
    - Recruitee: https://{slug}.recruitee.com
    - Pinpoint: https://{slug}.pinpointhq.com
    - Rippling: https://www.rippling.com/careers/{slug} or API board URL
    - Breezy HR: https://{slug}.breezy.hr
    - Workday: https://{slug}.myworkdayjobs.com
    """
    import urllib.parse

    if not url or not isinstance(url, str):
        return None
    url_clean = url.strip()
    if not url_clean.startswith("http"):
        url_clean = "https://" + url_clean
    try:
        parsed = urllib.parse.urlparse(url_clean)
    except Exception:
        return None

    host = parsed.netloc.lower()
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    query_params = urllib.parse.parse_qs(parsed.query)

    def _make_name(slug: str) -> str:
        return custom_name or slug.replace("-", " ").title()

    # 1. Lever
    if "lever.co" in host:
        if "postings" in path_parts:
            idx = path_parts.index("postings")
            slug = path_parts[idx + 1] if idx + 1 < len(path_parts) else None
        elif path_parts:
            slug = path_parts[0]
        else:
            slug = None
        if slug:
            clean_slug = slug.lower().strip()
            return ("lever", clean_slug, _make_name(clean_slug))

    # 2. Greenhouse
    if "greenhouse.io" in host:
        slug = None
        if "for" in query_params:
            slug = query_params["for"][0]
        elif "token" in query_params:
            slug = query_params["token"][0]
        elif "boards" in path_parts:
            idx = path_parts.index("boards")
            slug = path_parts[idx + 1] if idx + 1 < len(path_parts) else None
        elif path_parts:
            if path_parts[0] in ("embed", "jobs") and len(path_parts) > 1:
                slug = path_parts[1]
            else:
                slug = path_parts[0]
        if slug:
            clean_slug = slug.lower().strip()
            return ("greenhouse", clean_slug, _make_name(clean_slug))

    # 3. Ashby
    if "ashbyhq.com" in host:
        slug = None
        if "job-board" in path_parts:
            idx = path_parts.index("job-board")
            slug = path_parts[idx + 1] if idx + 1 < len(path_parts) else None
        elif path_parts:
            slug = path_parts[0]
        if slug:
            clean_slug = slug.lower().strip()
            return ("ashby", clean_slug, _make_name(clean_slug))

    # 4. Workable
    if "workable.com" in host:
        # https://apply.workable.com/{slug} or API URL
        if path_parts:
            # Skip "api", "v1", "widget", "accounts" path segments
            slug = None
            for part in reversed(path_parts):
                if part not in ("api", "v1", "widget", "accounts"):
                    slug = part
                    break
            if slug:
                clean_slug = slug.lower().strip()
                return ("workable", clean_slug, _make_name(clean_slug))

    # 5. SmartRecruiters
    if "smartrecruiters.com" in host:
        # https://jobs.smartrecruiters.com/{slug} or API URL
        if path_parts:
            slug = None
            for part in path_parts:
                if part not in ("v1", "companies", "postings", "jobs"):
                    slug = part
                    break
            if slug:
                clean_slug = slug.lower().strip()
                return ("smartrecruiters", clean_slug, _make_name(clean_slug))

    # 6. Recruitee — subdomain pattern: {slug}.recruitee.com
    if "recruitee.com" in host:
        parts = host.split(".")
        if len(parts) >= 3 and parts[-2] == "recruitee":
            slug = parts[0]
            if slug and slug not in ("www", "api"):
                return ("recruitee", slug, _make_name(slug))

    # 7. Pinpoint — subdomain pattern: {slug}.pinpointhq.com
    if "pinpointhq.com" in host:
        parts = host.split(".")
        if len(parts) >= 3 and parts[-2] == "pinpointhq":
            slug = parts[0]
            if slug and slug not in ("www", "api"):
                return ("pinpoint", slug, _make_name(slug))

    # 8. Rippling
    if "rippling.com" in host:
        # https://www.rippling.com/careers/{slug} or API board URL
        if "careers" in path_parts:
            idx = path_parts.index("careers")
            slug = path_parts[idx + 1] if idx + 1 < len(path_parts) else None
        elif "board" in path_parts:
            idx = path_parts.index("board")
            slug = path_parts[idx + 1] if idx + 1 < len(path_parts) else None
        else:
            slug = None
        if slug:
            clean_slug = slug.lower().strip()
            return ("rippling", clean_slug, _make_name(clean_slug))

    # 9. Breezy HR — subdomain pattern: {slug}.breezy.hr
    if "breezy.hr" in host:
        parts = host.split(".")
        if len(parts) >= 3 and parts[-2] == "breezy":
            slug = parts[0]
            if slug and slug not in ("www", "api", "app"):
                return ("breezyhr", slug, _make_name(slug))

    # 10. Workday — subdomain pattern: {slug}.myworkdayjobs.com
    if "myworkdayjobs.com" in host:
        parts = host.split(".")
        if len(parts) >= 3:
            # Handle {slug}.wd5.myworkdayjobs.com or {slug}.myworkdayjobs.com
            slug = parts[0]
            if slug and slug not in ("www",):
                return ("workday", slug, _make_name(slug))

    return None


class BaseATSClient(ABC):
    """Abstract base class for querying applicant tracking systems."""

    def __init__(self, rate_limit_delay_seconds: float = 1.0, timeout: float = 15.0):
        self.rate_limit_delay_seconds = rate_limit_delay_seconds
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "HireReady-Scanner/1.0"})

    async def close(self):
        """Close the underlying HTTP client session."""
        await self.client.aclose()

    @abstractmethod
    async def fetch_jobs(self, company_slug: str, company_name: str) -> list[JobListing]:
        """Fetch and normalize job postings for a company."""
        pass

    async def _rate_limit(self):
        """Enforce configured rate limit delay."""
        if self.rate_limit_delay_seconds > 0:
            await asyncio.sleep(self.rate_limit_delay_seconds)
