"""Configuration service for managing user preferences and ATS company configurations."""

import json
import logging
from typing import Any
import yaml

from config.settings import settings
from src.ats.aggregator import parse_ats_url

logger = logging.getLogger(__name__)


class ConfigService:
    """Manages search preferences and ATS company integration configurations."""

    def get_preferences(self) -> dict[str, Any]:
        """Load search preferences from input/preferences.yaml."""
        prefs_path = settings.input_dir / "preferences.yaml"
        if not prefs_path.exists():
            return {}
        try:
            with open(prefs_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error("Error loading preferences: %s", e)
            return {}

    def update_preferences(self, data: dict[str, Any]) -> dict[str, Any]:
        """Save updated preferences to input/preferences.yaml."""
        prefs_path = settings.input_dir / "preferences.yaml"
        with open(prefs_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
        return self.get_preferences()

    def get_ats_companies(self) -> dict[str, Any]:
        """Load configured ATS boards from config/ats_companies.json."""
        path = settings.ats_companies_path
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Error reading ats_companies.json: %s", e)
            return {}

    def add_ats_link(
        self,
        url: str | None = None,
        platform: str | None = None,
        company_slug: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Add a company ATS board by URL or platform + slug."""
        if url:
            parsed = parse_ats_url(url)
            if not parsed:
                raise ValueError("Could not detect supported ATS platform from URL.")
            platform, company_slug, detected_name = parsed
            if not name:
                name = detected_name

        if not platform or not company_slug:
            raise ValueError("Platform and company_slug are required.")

        config = self.get_ats_companies()
        if platform not in config:
            config[platform] = {"enabled": True, "rate_limit_delay_seconds": 1.0, "companies": []}

        entry = config[platform]
        if isinstance(entry, list):
            config[platform] = {"enabled": True, "rate_limit_delay_seconds": 1.0, "companies": entry}
        companies_list = config[platform].setdefault("companies", [])

        if not any(
            (isinstance(c, dict) and c.get("slug") == company_slug) or
            (isinstance(c, str) and c == company_slug)
            for c in companies_list
        ):
            companies_list.append({"slug": company_slug, "name": name or company_slug.replace("-", " ").title()})
            settings.ats_companies_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

        return config

    def delete_ats_company(self, platform: str, company_slug: str) -> dict[str, Any]:
        """Remove a company board from ats_companies.json."""
        config = self.get_ats_companies()
        if platform in config:
            entry = config[platform]
            if isinstance(entry, dict):
                companies = entry.get("companies", [])
            else:
                companies = entry

            config[platform]["companies"] = [
                c for c in companies
                if not (
                    (isinstance(c, dict) and c.get("slug") == company_slug) or
                    (isinstance(c, str) and c == company_slug)
                )
            ]
            settings.ats_companies_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return config

