"""Config-driven generic ATS client. Reads field mappings from ats_platforms.json."""

import asyncio
from datetime import date, datetime
import html as html_mod
import json
import logging
from pathlib import Path
from typing import Any

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
        self.platform_config = platform_config
        self.request_cfg = platform_config.get("request", {})
        self.detail_cfg = platform_config.get("detail_request")
        self.response_cfg = platform_config.get("response", {})

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def fetch_jobs(
        self,
        company_slug: str,
        company_name: str,
        preferences: Any = None,
        force_refresh: bool = False,
    ) -> list[JobListing]:
        """Fetch and normalize job postings for a company using config-driven parsing and TTL caching."""
        cache_file = settings.ats_cache_dir / f"{self.platform_name}_{company_slug}.json"
        data = None

        if not force_refresh and cache_file.exists():
            try:
                import time
                age = time.time() - cache_file.stat().st_mtime
                if age < settings.ats_cache_ttl_seconds:
                    data = json.loads(cache_file.read_text(encoding="utf-8"))
                    logger.debug("Loaded %s jobs for %s from cache (age %.1fs)", self.platform_name, company_slug, age)
            except Exception as err:
                logger.debug("Failed reading cache for %s: %s", company_slug, err)

        if data is None:
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

                # Save raw board response to cache
                try:
                    cache_file.write_text(json.dumps(data, default=str), encoding="utf-8")
                except Exception as write_err:
                    logger.debug("Failed writing cache for %s: %s", company_slug, write_err)
            except Exception as e:
                logger.debug("Failed to fetch %s jobs for %s: %s", self.platform_name, company_name, e)
                return []

        postings = self._extract_listings(data)

        # Optimization 1: Pre-filter before detail fetch (e.g. Rippling, SmartRecruiters)
        if self.detail_cfg and postings:
            target_postings = postings
            if preferences:
                target_postings = [
                    p for p in postings
                    if self._pre_matches_preferences(p, company_name, company_slug, preferences)
                ]
                logger.debug(
                    "Pre-filtered %s %s from %s down to %s postings before detail fetch",
                    self.platform_name,
                    company_slug,
                    len(postings),
                    len(target_postings),
                )
            postings = await self._fetch_details(target_postings, company_slug, force_refresh=force_refresh)

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

    def _pre_matches_preferences(
        self,
        posting: dict,
        company_name: str,
        company_slug: str,
        prefs: Any,
    ) -> bool:
        """Fast pre-filter for basic listing fields before fetching expensive detail endpoints."""
        import difflib

        # 1. Company exclusion
        if hasattr(prefs, "companies_exclude") and prefs.companies_exclude:
            if company_slug.lower() in [c.lower() for c in prefs.companies_exclude]:
                return False
            if any(c.lower() in company_name.lower() for c in prefs.companies_exclude):
                return False

        # 2. Target roles check on listing title
        if hasattr(prefs, "target_roles") and prefs.target_roles:
            title = str(self._get_field(posting, self.response_cfg.get("title_field", "title")) or "").strip().lower()
            if not title:
                return True

            TITLE_FILLER = {
                "senior", "sr", "junior", "jr", "staff", "principal", "lead", "head",
                "manager", "director", "vp", "intern", "associate", "i", "ii", "iii",
                "iv", "v", "remote", "hybrid", "contract", "full", "time", "part",
            }

            matched_role = False
            for target in prefs.target_roles:
                target_lower = target.lower()
                if target_lower in title or title in target_lower:
                    matched_role = True
                    break
                target_words = set(target_lower.split()) - TITLE_FILLER
                title_words = set(title.split()) - TITLE_FILLER
                common = target_words.intersection(title_words)
                if target_words and len(common) >= len(target_words) * 0.6 and len(common) >= 2:
                    matched_role = True
                    break
                ratio = difflib.SequenceMatcher(None, target_lower, title).ratio()
                if ratio >= 0.70:
                    matched_role = True
                    break

            if not matched_role:
                return False

        return True

    async def _fetch_details(self, postings: list[dict], company_slug: str, force_refresh: bool = False) -> list[dict]:
        """Concurrently fetch details for postings when a platform defines detail_request."""
        if not self.detail_cfg:
            return postings

        url_tmpl = self.detail_cfg.get("url_template", "")
        method = self.detail_cfg.get("method", "GET").upper()
        headers = self.detail_cfg.get("headers") or {}
        id_field = self.response_cfg.get("id_field", "id")
        sem = asyncio.Semaphore(15)

        async def _fetch_one(posting: dict) -> dict:
            p_id = str(self._get_field(posting, id_field) or "")
            if not p_id or not url_tmpl:
                return posting

            # Check detail cache
            clean_id = p_id.replace("/", "_").replace("\\", "_")
            detail_cache = settings.ats_cache_dir / f"{self.platform_name}_{company_slug}_detail_{clean_id}.json"
            if not force_refresh and detail_cache.exists():
                try:
                    import time
                    if time.time() - detail_cache.stat().st_mtime < settings.ats_cache_ttl_seconds:
                        d_json = json.loads(detail_cache.read_text(encoding="utf-8"))
                        if isinstance(d_json, dict):
                            return {**posting, **d_json, "_raw_detail": d_json}
                except Exception:
                    pass

            url = url_tmpl.replace("{slug}", company_slug).replace("{id}", p_id)
            async with sem:
                try:
                    if method == "POST":
                        resp = await self.client.post(url, headers=headers)
                    else:
                        resp = await self.client.get(url, headers=headers)
                    if resp.status_code == 200:
                        detail_json = resp.json()
                        if isinstance(detail_json, dict):
                            # Cache the individual detail
                            try:
                                detail_cache.write_text(json.dumps(detail_json, default=str), encoding="utf-8")
                            except Exception:
                                pass
                            return {**posting, **detail_json, "_raw_detail": detail_json}
                except Exception as err:
                    logger.debug("Failed detail fetch for %s: %s", p_id, err)
            return posting

        enriched = await asyncio.gather(*[_fetch_one(p) for p in postings])
        return list(enriched)

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
        """Resolve a JSONPath-like expression to extract an array from data."""
        if path == "$":
            return data if isinstance(data, list) else None

        if path.startswith("$."):
            key = path[2:]
            if isinstance(data, dict) and key in data:
                val = data[key]
                return val if isinstance(val, list) else None

        return None

    @staticmethod
    def _normalize_workplace_type(val: Any, is_remote: bool = False) -> str | None:
        """Normalize workplace type to Remote, Hybrid, On-site, or Unspecified."""
        if not val:
            return "Remote" if is_remote else None
        s = str(val).lower().replace("_", "-").replace(" ", "-")
        if "hybrid" in s:
            return "Hybrid"
        if "remote" in s or is_remote:
            return "Remote"
        if "on-site" in s or "onsite" in s or "on site" in s:
            return "On-site"
        return str(val).strip().title()

    @staticmethod
    def _normalize_employment_type(val: Any) -> str | None:
        """Normalize employment type to Full-time, Part-time, Contract, Internship, etc."""
        if not val:
            return None
        s = str(val).lower().replace("_", "-").replace(" ", "-")
        if any(k in s for k in ["full-time", "fulltime", "salaried-ft", "permanent", "full"]):
            return "Full-time"
        if any(k in s for k in ["part-time", "parttime", "part"]):
            return "Part-time"
        if any(k in s for k in ["contract", "freelance", "contractor"]):
            return "Contract"
        if any(k in s for k in ["intern", "internship"]):
            return "Internship"
        return str(val).strip()

    def _resolve_locations(self, posting: dict, cfg: dict) -> list[str]:
        """Resolve all locations / secondary locations for a job."""
        loc_spec = cfg.get("locations_field")
        if not loc_spec:
            return []
        val = self._get_field(posting, loc_spec)
        if not val:
            return []
        locations: list[str] = []
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    s = item.strip()
                    if s and s not in locations:
                        locations.append(s)
                elif isinstance(item, dict):
                    loc_name = item.get("name") or item.get("location") or item.get("city")
                    if loc_name and isinstance(loc_name, str):
                        s = loc_name.strip()
                        if s and s not in locations:
                            locations.append(s)
                    elif "address" in item and isinstance(item["address"], dict):
                        postal = item["address"].get("postalAddress", {})
                        parts = [postal.get("addressLocality"), postal.get("addressRegion"), postal.get("addressCountry")]
                        clean_parts = [p for p in parts if p]
                        if clean_parts:
                            s = ", ".join(clean_parts)
                            if s not in locations:
                                locations.append(s)
        elif isinstance(val, str):
            locations.append(val.strip())
        return locations

    def _resolve_html_description(self, posting: dict, cfg: dict) -> tuple[str, dict[str, str]]:
        """Resolve HTML description and structured sections across various ATS formats."""
        desc_spec = cfg.get("description_html_field")
        sections: dict[str, str] = {}
        html_parts: list[str] = []

        if desc_spec:
            specs = desc_spec if isinstance(desc_spec, list) else [desc_spec]
            for spec in specs:
                val = self._resolve_path(posting, spec)
                if not val:
                    continue
                if isinstance(val, dict):
                    # E.g. Rippling: {"company": "...", "role": "..."}
                    for k, v in val.items():
                        if v and isinstance(v, str):
                            sections[k] = v
                            clean_k = k.replace("_", " ").title()
                            html_parts.append(
                                f"<div class=\"job-section-{k}\"><h4 class=\"font-semibold text-slate-800 dark:text-slate-200 mb-1\">{clean_k}</h4>{v}</div>"
                            )
                elif isinstance(val, str):
                    part_name = spec.split(".")[-1]
                    sections[part_name] = val
                    html_parts.append(val)
                elif isinstance(val, list):
                    for item in val:
                        if isinstance(item, str):
                            html_parts.append(item)
                        elif isinstance(item, dict) and "text" in item:
                            txt = item["text"]
                            if txt:
                                html_parts.append(str(txt))

        # Check extra_description_field (e.g. Lever "additional", Pinpoint "benefits")
        extra_field = cfg.get("extra_description_field")
        if extra_field:
            extra_val = self._get_field(posting, extra_field)
            if extra_val and isinstance(extra_val, str) and extra_val.strip():
                sections["additional"] = extra_val
                html_parts.append(f"<div class=\"job-section-additional\">{extra_val}</div>")

        desc_html = "\n".join(html_parts)

        # Unescape HTML entities repeatedly (e.g. Greenhouse &lt;p&gt;)
        max_unescape = 3
        while max_unescape > 0 and ("&lt;" in desc_html or "&amp;lt;" in desc_html or "&amp;amp;" in desc_html):
            unescaped = html_mod.unescape(desc_html)
            if unescaped == desc_html:
                break
            desc_html = unescaped
            max_unescape -= 1

        return desc_html, sections

    def _parse_posting(self, posting: dict, company_slug: str, company_name: str) -> JobListing | None:
        """Parse a single posting dict into a JobListing using configured field mappings."""
        cfg = self.response_cfg

        posting_id = str(self._get_field(posting, cfg.get("id_field", "id")) or "")
        title = str(self._get_field(posting, cfg.get("title_field", "title")) or "").strip()
        if not posting_id or not title:
            return None

        # Location & Secondary Locations
        location = self._get_field_str(posting, cfg.get("location_field", "location"))
        locations = self._resolve_locations(posting, cfg)
        if location and location not in locations:
            locations = [location] + locations

        # Department & Team
        department = self._get_field_str(posting, cfg.get("department_field", "department"))
        team = self._get_field_str(posting, cfg.get("team_field")) if cfg.get("team_field") else None

        # Remote detection
        remote_val = self._get_field(posting, cfg.get("remote_field")) if cfg.get("remote_field") else None
        remote = bool(remote_val) if remote_val is not None else False
        if not remote:
            loc_lower = location.lower()
            title_lower = title.lower()
            remote = "remote" in loc_lower or "remote" in title_lower

        # Workplace Type (Remote, Hybrid, On-site)
        raw_workplace = self._get_field(posting, cfg.get("workplace_type_field")) if cfg.get("workplace_type_field") else None
        workplace_type = self._normalize_workplace_type(raw_workplace, is_remote=remote)

        # Employment Type (Full-time, Contract, etc.)
        raw_emp = self._get_field(posting, cfg.get("employment_type_field")) if cfg.get("employment_type_field") else None
        employment_type = self._normalize_employment_type(raw_emp)

        # Experience Level (Associate, Lead, etc.)
        raw_exp = self._get_field(posting, cfg.get("experience_level_field")) if cfg.get("experience_level_field") else None
        experience_level = str(raw_exp).strip() if raw_exp else None

        # Country
        country = self._get_field_str(posting, cfg.get("country_field")) if cfg.get("country_field") else None

        # Description HTML & Sections
        desc_html, desc_sections = self._resolve_html_description(posting, cfg)

        # Description Plain Text
        desc_text = str(self._get_field(posting, cfg.get("description_text_field")) or "") if cfg.get("description_text_field") else ""
        if desc_text:
            max_unescape = 3
            while max_unescape > 0 and ("&lt;" in desc_text or "&amp;" in desc_text):
                unescaped = html_mod.unescape(desc_text)
                if unescaped == desc_text:
                    break
                desc_text = unescaped
                max_unescape -= 1
            if "<div" in desc_text or "<p" in desc_text or "<br" in desc_text or "<li" in desc_text:
                desc_text = BeautifulSoup(desc_text, "html.parser").get_text("\n", strip=True)

        if not desc_text and desc_html:
            desc_text = BeautifulSoup(desc_html, "html.parser").get_text("\n", strip=True)

        # Application URL & Job URL
        apply_url = self._get_field_str(posting, cfg.get("application_url_field", ""))
        if not apply_url:
            fallback = cfg.get("application_url_fallback", "")
            if fallback:
                apply_url = fallback.replace("{slug}", company_slug).replace("{id}", posting_id)

        job_url = self._get_field_str(posting, cfg.get("job_url_field", "")) if cfg.get("job_url_field") else None
        if not job_url:
            job_url = apply_url

        # Salary / Compensation & Equity
        salary_raw = self._get_field(posting, cfg.get("salary_field")) if cfg.get("salary_field") else None
        has_equity = False
        if salary_raw:
            s_str = str(salary_raw).lower()
            if "equity" in s_str:
                has_equity = True
        if not has_equity and ("equity" in desc_text[:1200].lower() or "stock options" in desc_text[:1200].lower()):
            has_equity = True

        # Posted date & Updated date
        posted_date = self._parse_date(posting, cfg.get("posted_date_field"), cfg.get("date_format", "iso"))
        updated_date = self._parse_date(posting, cfg.get("updated_date_field", "updated_at"), "iso")

        job_id = generate_job_id(company_slug, title, posting_id)

        # Preserve metadata for salary extraction & downstream components
        meta = {
            **posting.get("metadata", {}),
            "salary_raw": salary_raw,
            "payRangeDetails": salary_raw if isinstance(salary_raw, list) else None,
            "compensation": salary_raw if isinstance(salary_raw, dict) else None,
            "workplace_type": workplace_type,
            "employment_type": employment_type,
            "experience_level": experience_level,
        }

        return JobListing(
            id=job_id,
            ats_source=self.platform_name,
            company=company_name,
            company_slug=company_slug,
            title=title,
            location=location or ("Remote" if remote else "Unspecified"),
            locations=locations,
            remote=remote,
            workplace_type=workplace_type,
            employment_type=employment_type,
            experience_level=experience_level,
            department=department or None,
            team=team or None,
            country=country or None,
            posted_date=posted_date,
            updated_date=updated_date,
            description_html=desc_html,
            description_text=desc_text,
            description_sections=desc_sections,
            application_url=apply_url,
            job_url=job_url,
            salary_raw=salary_raw,
            has_equity=has_equity,
            api_posting_id=posting_id,
            metadata=meta,
            first_seen=datetime.now(),
        )

    def _parse_date(self, posting: dict, field_spec: Any, date_format: str = "iso") -> date | None:
        """Parse date from posting using field spec and format."""
        if not field_spec:
            return None

        date_val = self._get_field(posting, field_spec)
        if not date_val:
            return None

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
        """Resolve a field value from a posting dict."""
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
            return str(val.get("name") or val.get("label") or str(val))
        return str(val)

    def _resolve_path(self, data: Any, path: str) -> Any:
        """Walk a dot-notation path with optional array indices."""
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
