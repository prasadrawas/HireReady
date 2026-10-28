"""Config-driven generic ATS client. Reads field mappings from ats_platforms.json."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

from config.settings import settings
from src.ats.base import BaseATSClient, generate_job_id
from src.models.job_listing import JobListing

logger = logging.getLogger(__name__)


class GenericATSClient(BaseATSClient):
    """A single client that handles any ATS platform based on JSON configuration.

    Instead of writing a separate Python file per ATS, this client reads
    ``config/ats_platforms.json`` to understand endpoints, HTTP methods,
    and response field mappings for each platform.
    """

    def __init__(
        self,
        platform_name: str,
        platform_config: dict[str, Any],
        rate_limit_delay_seconds: float = 1.0,
        timeout: float = 15.0,
    ):
        super().__init__(rate_limit_delay_seconds=rate_limit_delay_seconds, timeout=timeout)
        self.platform_name = platform_name
        self.request_cfg = platform_config.get("request", {})
        self.response_cfg = platform_config.get("response", {})

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def fetch_jobs(self, company_slug: str, company_name: str) -> list[JobListing]:
        """Fetch and normalize job postings for a company using config-driven parsing."""
        url = self.request_cfg.get("url_template", "").replace("{slug}", company_slug)
        method = self.request_cfg.get("method", "GET").upper()
        headers = self.request_cfg.get("headers") or {}
        body = self.request_cfg.get("body")

        await self._rate_limit()

        try:
            if method == "POST":
                response = await self.client.post(url, headers=headers, json=body)
            else:
                response = await self.client.get(url, headers=headers)

            if response.status_code == 404:
                logger.debug("%s board not found for %s (%s)", self.platform_name, company_name, company_slug)
                return []
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.debug("Failed to fetch %s jobs for %s: %s", self.platform_name, company_name, e)
            return []

        postings = self._extract_listings(data)
        jobs: list[JobListing] = []

        for posting in postings:
            try:
                job = self._parse_posting(posting, company_slug, company_name)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug("Error parsing %s posting: %s", self.platform_name, e)
                continue

        return jobs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_listings(self, data: Any) -> list[dict]:
        """Extract the listings array from the API response using configured path."""
        listings_path = self.response_cfg.get("listings_path", "$")

        result = self._resolve_listings_path(data, listings_path)
        if result is not None:
            return result

        # Try fallback paths
        for fallback in self.response_cfg.get("listings_path_fallback", []):
            result = self._resolve_listings_path(data, fallback)
            if result is not None:
                return result

        # Last resort: if data is already a list, use it directly
        if isinstance(data, list):
            return data

        return []

    def _resolve_listings_path(self, data: Any, path: str) -> list[dict] | None:
        """Resolve a JSONPath-like expression to extract an array from data.

        Supported patterns:
        - ``$``           → root is the array
        - ``$.jobs``      → data["jobs"]
        - ``$.postings``  → data["postings"]
        """
        if path == "$":
            return data if isinstance(data, list) else None

        if path.startswith("$."):
            key = path[2:]
            if isinstance(data, dict) and key in data:
                val = data[key]
                return val if isinstance(val, list) else None

        return None

    def _parse_posting(self, posting: dict, company_slug: str, company_name: str) -> JobListing | None:
        """Parse a single posting dict into a JobListing using configured field mappings."""
        cfg = self.response_cfg

        posting_id = str(self._get_field(posting, cfg.get("id_field", "id")) or "")
        title = str(self._get_field(posting, cfg.get("title_field", "title")) or "").strip()
        if not posting_id or not title:
            return None

        # Location
        location = self._get_field_str(posting, cfg.get("location_field", "location"))

        # Department
        department = self._get_field_str(posting, cfg.get("department_field", "department"))

        # Remote detection
        remote_val = self._get_field(posting, cfg.get("remote_field")) if cfg.get("remote_field") else None
        remote = bool(remote_val) if remote_val is not None else False
        if not remote:
            loc_lower = location.lower()
            title_lower = title.lower()
            remote = "remote" in loc_lower or "remote" in title_lower

        # Description HTML
        desc_html = str(self._get_field(posting, cfg.get("description_html_field", "")) or "")
        extra_desc_field = cfg.get("extra_description_field")
        if extra_desc_field:
            extra = self._get_field(posting, extra_desc_field)
            if extra:
                desc_html += f"\n<div>{extra}</div>"

        # Description plain text
        desc_text = str(self._get_field(posting, cfg.get("description_text_field")) or "") if cfg.get("description_text_field") else ""
        if not desc_text and desc_html:
            desc_text = BeautifulSoup(desc_html, "html.parser").get_text("\n", strip=True)

        # Application URL
        apply_url = self._get_field_str(posting, cfg.get("application_url_field", ""))
        if not apply_url:
            fallback = cfg.get("application_url_fallback", "")
            if fallback:
                apply_url = fallback.replace("{slug}", company_slug).replace("{id}", posting_id)

        # Posted date
        posted_date = self._parse_date(posting, cfg)

        job_id = generate_job_id(company_slug, title, posting_id)

        return JobListing(
            id=job_id,
            ats_source=self.platform_name,
            company=company_name,
            company_slug=company_slug,
            title=title,
            location=location or ("Remote" if remote else "Unspecified"),
            remote=remote,
            department=department or None,
            posted_date=posted_date,
            description_html=desc_html,
            description_text=desc_text,
            application_url=apply_url,
            api_posting_id=posting_id,
            metadata={},
            first_seen=datetime.now(),
        )

    def _parse_date(self, posting: dict, cfg: dict) -> "date | None":
        """Parse the posted date from a posting using the configured date field and format."""
        from datetime import date

        date_val = self._get_field(posting, cfg.get("posted_date_field"))
        if not date_val:
            return None

        date_format = cfg.get("date_format", "iso")
        try:
            if date_format == "epoch_ms":
                return datetime.fromtimestamp(int(date_val) / 1000.0).date()
            elif date_format == "epoch":
                return datetime.fromtimestamp(int(date_val)).date()
            else:
                # ISO format
                return datetime.fromisoformat(str(date_val).replace("Z", "+00:00")).date()
        except Exception:
            return None

    def _get_field(self, data: dict, field_spec: Any) -> Any:
        """Resolve a field value from a posting dict.

        Supports:
        - Simple key: ``"title"``
        - Dot notation: ``"location.name"``
        - Array index: ``"departments[0].name"``
        - List of fallbacks: ``["locationName", "location"]``
        - None → returns None
        """
        if field_spec is None:
            return None

        if isinstance(field_spec, list):
            for spec in field_spec:
                val = self._resolve_path(data, spec)
                if val is not None:
                    return val
            return None

        return self._resolve_path(data, field_spec)

    def _get_field_str(self, data: dict, field_spec: Any) -> str:
        """Resolve a field and coerce to string."""
        val = self._get_field(data, field_spec)
        if val is None:
            return ""
        if isinstance(val, dict):
            return val.get("name", str(val))
        return str(val)

    def _resolve_path(self, data: Any, path: str) -> Any:
        """Walk a dot-notation path with optional array indices.

        Examples:
        - ``"title"`` → data["title"]
        - ``"location.name"`` → data["location"]["name"]
        - ``"departments[0].name"`` → data["departments"][0]["name"]
        - ``"categories.location"`` → data["categories"]["location"]
        """
        if not path or data is None:
            return None

        import re
        parts = re.split(r"\.", path)
        current = data

        for part in parts:
            if current is None:
                return None

            # Check for array index: e.g. "departments[0]"
            idx_match = re.match(r"^(\w+)\[(\d+)\]$", part)
            if idx_match:
                key, idx = idx_match.group(1), int(idx_match.group(2))
                if isinstance(current, dict) and key in current:
                    arr = current[key]
                    if isinstance(arr, list) and idx < len(arr):
                        current = arr[idx]
                    else:
                        return None
                else:
                    return None
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current


def load_platform_configs(config_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load all platform definitions from ats_platforms.json."""
    path = config_path or (settings.config_dir / "ats_platforms.json")
    if not path.exists():
        logger.warning("ATS platforms config not found: %s", path)
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
