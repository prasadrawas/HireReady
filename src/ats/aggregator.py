"""ATS Aggregator for multi-source fetching, filtering, and deduplication."""

import asyncio
from datetime import date, datetime
import difflib
import json
import logging
from pathlib import Path
from typing import Any

from config.settings import settings
from src.ats.base import BaseATSClient, parse_ats_url, slugify
from src.ats.generic_client import GenericATSClient, load_platform_configs
from src.models.job_listing import JobListing
from src.models.preferences import SearchPreferences

logger = logging.getLogger(__name__)


class ATSAggregator:
    """Orchestrates job scanning across multiple ATS platforms.

    All ATS platforms are handled by the config-driven GenericATSClient.
    Platform definitions (endpoints, field mappings) live in config/ats_platforms.json.
    Company lists live in config/ats_companies.json.
    No platform-specific Python code is needed — adding a new ATS is purely config.
    """

    def __init__(
        self,
        config_path: str | Path | None = None,
        seen_jobs_path: str | Path | None = None,
        platforms_config_path: str | Path | None = None,
    ):
        self.config_path = Path(config_path) if config_path else settings.ats_companies_path
        self.seen_jobs_path = Path(seen_jobs_path) if seen_jobs_path else settings.seen_jobs_path
        self.platforms_config_path = Path(platforms_config_path) if platforms_config_path else None
        self.clients: dict[str, BaseATSClient] = {}

    def _load_config(self) -> dict[str, Any]:
        """Load and normalize ats_companies.json configuration."""
        if not self.config_path.exists():
            logger.warning("ATS config file not found: %s", self.config_path)
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            return self._normalize_config(raw_data)
        except Exception as e:
            logger.debug("Error reading ATS config: %s", e)
            return {}

    def _normalize_config(self, raw_data: Any) -> dict[str, Any]:
        """Normalize URL lists, link arrays, or categorized dicts into unified internal structure.

        Accepts any platform name — not limited to lever/greenhouse/ashby.
        New platforms defined in ats_platforms.json are automatically supported.
        """
        platform_configs = load_platform_configs(self.platforms_config_path)
        known_platforms = set(platform_configs.keys())

        # Build standard config with entries for all known platforms
        standard_config: dict[str, dict[str, Any]] = {}
        for plat in known_platforms:
            standard_config[plat] = {"enabled": True, "rate_limit_delay_seconds": 1.0, "companies": []}

        def add_entry(item: Any, default_platform: str | None = None):
            if isinstance(item, str):
                parsed = parse_ats_url(item)
                if parsed:
                    plat, slug, name = parsed
                    if plat not in standard_config:
                        standard_config[plat] = {"enabled": True, "rate_limit_delay_seconds": 1.0, "companies": []}
                    standard_config[plat]["companies"].append({"slug": slug, "name": name, "url": item})
                else:
                    logger.warning("Could not auto-detect ATS platform from link: %s", item)
            elif isinstance(item, dict):
                url = item.get("url") or item.get("link")
                name = item.get("name")
                if url:
                    parsed = parse_ats_url(url, custom_name=name)
                    if parsed:
                        plat, slug, name = parsed
                        if plat not in standard_config:
                            standard_config[plat] = {"enabled": True, "rate_limit_delay_seconds": 1.0, "companies": []}
                        standard_config[plat]["companies"].append({"slug": slug, "name": name, "url": url})
                        return
                slug = item.get("slug")
                plat = item.get("ats") or item.get("platform") or default_platform
                if slug and plat:
                    if plat not in standard_config:
                        standard_config[plat] = {"enabled": True, "rate_limit_delay_seconds": 1.0, "companies": []}
                    standard_config[plat]["companies"].append({
                        "slug": slug,
                        "name": name or slug.replace("-", " ").title(),
                    })

        # Case 1: Direct list of URLs or company objects [ "https://...", ... ]
        if isinstance(raw_data, list):
            for item in raw_data:
                add_entry(item)
            return standard_config

        # Case 2: Dict containing links / ats_links / urls list
        if isinstance(raw_data, dict):
            for key in ["ats_links", "links", "urls", "job_boards"]:
                if key in raw_data and isinstance(raw_data[key], list):
                    for item in raw_data[key]:
                        add_entry(item)

            # Check for categorized platforms (any name, not just lever/greenhouse/ashby)
            for plat_name, plat_data in raw_data.items():
                if plat_name in ("ats_links", "links", "urls", "job_boards"):
                    continue  # already handled above
                if isinstance(plat_data, dict):
                    if plat_name not in standard_config:
                        standard_config[plat_name] = {"enabled": True, "rate_limit_delay_seconds": 1.0, "companies": []}
                    standard_config[plat_name]["enabled"] = plat_data.get("enabled", True)
                    standard_config[plat_name]["rate_limit_delay_seconds"] = plat_data.get("rate_limit_delay_seconds", 1.0)
                    for comp in plat_data.get("companies", []):
                        add_entry(comp, default_platform=plat_name)

        return standard_config

    def _load_seen_jobs(self) -> dict[str, Any]:
        """Load seen_jobs.json cache."""
        if not self.seen_jobs_path.exists():
            return {}
        try:
            with open(self.seen_jobs_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Error reading seen_jobs.json: %s. Using empty.", e)
            return {}

    def save_seen_jobs(self, seen_jobs: dict[str, Any]):
        """Persist seen_jobs.json cache."""
        self.seen_jobs_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.seen_jobs_path, "w", encoding="utf-8") as f:
            json.dump(seen_jobs, f, indent=2, default=str)

    async def fetch_all(
        self,
        preferences: SearchPreferences,
    ) -> tuple[list[JobListing], dict[str, int]]:
        """Fetch from all enabled ATS sources, apply filters, deduplicate, and identify new jobs."""
        config = self._load_config()
        platform_configs = load_platform_configs(self.platforms_config_path)
        all_raw_jobs: list[JobListing] = []
        counts_by_source: dict[str, int] = {}

        tasks = []
        for ats_name, ats_cfg in config.items():
            if not ats_cfg.get("enabled", True):
                logger.info("ATS %s is disabled, skipping.", ats_name)
                continue

            # Look up platform definition in ats_platforms.json
            if ats_name not in platform_configs:
                logger.warning(
                    "ATS platform '%s' found in ats_companies.json but has no definition in ats_platforms.json. Skipping.",
                    ats_name,
                )
                continue

            delay = float(ats_cfg.get("rate_limit_delay_seconds", 1.0))
            client = GenericATSClient(
                platform_name=ats_name,
                platform_config=platform_configs[ats_name],
                rate_limit_delay_seconds=delay,
            )
            self.clients[ats_name] = client

            companies = ats_cfg.get("companies", [])
            for comp in companies:
                tasks.append(
                    self._fetch_company_jobs(
                        client=client,
                        ats_name=ats_name,
                        slug=comp["slug"],
                        name=comp.get("name", comp["slug"]),
                    )
                )

        # Run concurrent fetches across companies
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, tuple):
                source, jobs = res
                all_raw_jobs.extend(jobs)
                counts_by_source[source] = counts_by_source.get(source, 0) + len(jobs)
            elif isinstance(res, Exception):
                logger.debug("Error during ATS fetch: %s", res)

        # Close HTTP clients
        for client in self.clients.values():
            await client.close()

        total_fetched = len(all_raw_jobs)

        # Step 2.1: Filter by preferences
        filtered_jobs = [j for j in all_raw_jobs if self._matches_preferences(j, preferences)]
        total_filtered = len(filtered_jobs)

        # Step 2.2: Deduplicate across ATS sources
        deduped_jobs = self._deduplicate(filtered_jobs)
        total_deduped = len(deduped_jobs)

        # Step 2.3: Check against seen_jobs.json
        seen_jobs = self._load_seen_jobs()
        new_jobs: list[JobListing] = []
        for job in deduped_jobs:
            if job.id not in seen_jobs:
                job.status = "new"
                new_jobs.append(job)
                # Register in seen_jobs
                seen_jobs[job.id] = {
                    "ats_source": job.ats_source,
                    "company": job.company,
                    "title": job.title,
                    "application_url": job.application_url,
                    "first_seen": datetime.now().isoformat(),
                    "status": "new",
                    "updated_at": datetime.now().isoformat(),
                }
            else:
                job.status = seen_jobs[job.id].get("status", "scored")

        self.save_seen_jobs(seen_jobs)

        stats = {
            "total_fetched": total_fetched,
            "after_filters": total_filtered,
            "after_dedup": total_deduped,
            "new_jobs": len(new_jobs),
            "matching_jobs": deduped_jobs,
            **counts_by_source,
        }

        return new_jobs, stats

    async def _fetch_company_jobs(
        self,
        client: BaseATSClient,
        ats_name: str,
        slug: str,
        name: str,
    ) -> tuple[str, list[JobListing]]:
        """Fetch jobs for a single company."""
        jobs = await client.fetch_jobs(slug, name)
        return ats_name, jobs

    def _matches_preferences(self, job: JobListing, prefs: SearchPreferences) -> bool:
        """Filter job based on search preferences."""
        # 1. Company exclusion
        if job.company_slug.lower() in [c.lower() for c in prefs.companies_exclude]:
            return False
        if any(c.lower() in job.company.lower() for c in prefs.companies_exclude):
            return False

        # 2. Maximum listing age
        if prefs.max_listing_age_days and job.posted_date:
            age_days = (date.today() - job.posted_date).days
            if age_days > prefs.max_listing_age_days:
                return False

        # 3. Remote only filter
        if prefs.remote_only and not job.remote:
            return False

        # 4. Location match (if locations specified and not remote)
        if prefs.locations and not job.remote:
            loc_lower = job.location.lower()
            matched_loc = any(
                req_loc.lower() in loc_lower
                for req_loc in prefs.locations
            )
            # If "remote" is in allowed locations and job is remote, allow
            if any("remote" in l.lower() for l in prefs.locations) and job.remote:
                matched_loc = True
            if not matched_loc:
                return False

        # 5. Role match (strict title match)
        # Filler words that should NOT count as meaningful overlap
        TITLE_FILLER = {
            "senior", "sr", "junior", "jr", "staff", "principal", "lead", "head",
            "manager", "director", "vp", "intern", "associate", "i", "ii", "iii",
            "iv", "v", "remote", "hybrid", "contract", "full", "time", "part",
        }

        if prefs.target_roles:
            title_lower = job.title.lower()
            matched_role = False
            for target in prefs.target_roles:
                target_lower = target.lower()
                # Exact substring check
                if target_lower in title_lower or title_lower in target_lower:
                    matched_role = True
                    break
                # Keyword overlap — only count meaningful words, not filler
                target_words = set(target_lower.split()) - TITLE_FILLER
                title_words = set(title_lower.split()) - TITLE_FILLER
                common = target_words.intersection(title_words)
                # Require overlap on core role words (e.g., "data" + "engineer")
                if target_words and len(common) >= len(target_words) * 0.6 and len(common) >= 2:
                    matched_role = True
                    break
                # Fuzzy ratio — raise threshold to avoid false positives
                ratio = difflib.SequenceMatcher(None, target_lower, title_lower).ratio()
                if ratio >= 0.70:
                    matched_role = True
                    break
            if not matched_role:
                return False

        return True

    def _deduplicate(self, jobs: list[JobListing]) -> list[JobListing]:
        """Deduplicate jobs by company and title, preferring direct apply URLs."""
        seen: dict[tuple[str, str], JobListing] = {}
        for job in jobs:
            key = (slugify(job.company), slugify(job.title))
            if key not in seen:
                seen[key] = job
            else:
                existing = seen[key]
                # Prefer Lever apply URL over Greenhouse/Ashby or longer/more direct apply URL
                if "apply" in job.application_url and "apply" not in existing.application_url:
                    seen[key] = job
        return list(seen.values())
