"""Company Research Brief: auto-fetch company info for matched jobs.

Includes a file-based cache so each company is only researched once via Gemini.
Subsequent requests for the same company return the cached result instantly.
"""

import json
import logging
from pathlib import Path
from typing import Any

from config.settings import settings
from src.llm_client import LLMClient, llm_client

logger = logging.getLogger(__name__)


class CompanyCache:
    """File-based cache for company research briefs. One Gemini call per company, ever."""

    def __init__(self, cache_path: Path | None = None):
        self.cache_path = cache_path or (settings.data_dir / "company_cache.json")

    def get(self, company: str) -> dict[str, Any] | None:
        """Get cached research for a company. Returns None if not cached."""
        cache = self._load()
        return cache.get(self._key(company))

    def put(self, company: str, data: dict[str, Any]):
        """Cache research for a company."""
        cache = self._load()
        cache[self._key(company)] = data
        self._save(cache)

    def _key(self, company: str) -> str:
        return company.strip().lower()

    def _load(self) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, cache: dict[str, Any]):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, default=str)

COMPANY_RESEARCH_PROMPT = """Research the following company and provide a brief for a job applicant.

COMPANY: {company}
JOB TITLE: {title}
JOB DESCRIPTION EXCERPT (first 500 chars):
{jd_excerpt}

Return a JSON object with these fields:
{{
  "company_name": "Official company name",
  "industry": "Primary industry (e.g., Fintech, Developer Tools, E-commerce)",
  "stage": "Company stage (e.g., Startup, Growth, Public, Enterprise)",
  "estimated_size": "Estimated employee count range (e.g., '50-200', '1000-5000', '10000+')",
  "known_for": "1-2 sentence description of what the company is known for",
  "tech_stack_signals": ["Technologies mentioned or commonly associated with this company"],
  "culture_signals": ["Culture indicators from the JD (positive or negative)"],
  "funding_status": "Known funding info if available (e.g., 'Series C', 'Public - NYSE', 'Bootstrapped'), or 'Unknown'",
  "glassdoor_sentiment": "General reputation if known (e.g., 'Generally positive', 'Mixed reviews on WLB', 'Unknown')",
  "notable_facts": ["1-3 notable facts relevant to an applicant"],
  "potential_concerns": ["Any concerns a candidate should be aware of, or empty list if none"],
  "verdict": "One of: 'strong_employer', 'solid_choice', 'do_your_research', 'proceed_with_caution'"
}}

Base your response on widely known public information. If you don't have reliable info about the company, say "Unknown" rather than guessing. Focus on facts relevant to a job seeker's decision.
"""


class CompanyResearcher:
    """Generates company research briefs using Gemini with file-based caching.

    Each company is researched via Gemini only ONCE. Subsequent requests for
    the same company (even across different jobs/runs) return the cached result.
    Cache is stored in data/company_cache.json.
    """

    def __init__(self, client: LLMClient | None = None):
        self.client = client or llm_client
        self.cache = CompanyCache()

    def research(
        self,
        company: str,
        title: str,
        description_text: str = "",
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        """Generate a company research brief. Returns cached result if available."""
        # Check cache first
        cached = self.cache.get(company)
        if cached:
            logger.info("Company research cache hit for %s — skipping Gemini call.", company)
            result = cached
        else:
            # Cache miss — call Gemini
            jd_excerpt = description_text[:500] if description_text else "(No JD text available)"
            prompt = (
                COMPANY_RESEARCH_PROMPT
                .replace("{company}", company)
                .replace("{title}", title)
                .replace("{jd_excerpt}", jd_excerpt)
            )

            try:
                raw_text, error = self.client._call_model(prompt, temperature=0.2)
                if raw_text is None:
                    raise Exception(f"Gemini call failed: {error}")
                result = self.client._clean_and_decode_json(raw_text)
            except Exception as e:
                logger.debug("Company research failed for %s: %s. Using fallback.", company, e)
                result = self._fallback(company, title)

            # Save to cache
            self.cache.put(company, result)

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "company_brief.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )

            # Also save a readable markdown version
            md = self._render_markdown(result)
            (output_dir / "company_brief.md").write_text(md, encoding="utf-8")

        return result

    def _render_markdown(self, data: dict[str, Any]) -> str:
        """Render company brief as readable markdown."""
        lines = [
            f"# Company Brief: {data.get('company_name', 'Unknown')}",
            "",
            f"**Industry:** {data.get('industry', 'Unknown')}",
            f"**Stage:** {data.get('stage', 'Unknown')}",
            f"**Size:** {data.get('estimated_size', 'Unknown')} employees",
            f"**Funding:** {data.get('funding_status', 'Unknown')}",
            f"**Reputation:** {data.get('glassdoor_sentiment', 'Unknown')}",
            "",
            f"## What They're Known For",
            f"{data.get('known_for', 'No information available.')}",
            "",
        ]

        tech = data.get("tech_stack_signals", [])
        if tech:
            lines.append("## Tech Stack Signals")
            for t in tech:
                lines.append(f"- {t}")
            lines.append("")

        culture = data.get("culture_signals", [])
        if culture:
            lines.append("## Culture Signals")
            for c in culture:
                lines.append(f"- {c}")
            lines.append("")

        facts = data.get("notable_facts", [])
        if facts:
            lines.append("## Notable Facts")
            for f in facts:
                lines.append(f"- {f}")
            lines.append("")

        concerns = data.get("potential_concerns", [])
        if concerns:
            lines.append("## Potential Concerns")
            for c in concerns:
                lines.append(f"- {c}")
            lines.append("")

        verdict = data.get("verdict", "unknown")
        verdict_display = {
            "strong_employer": "Strong Employer — well-regarded, good opportunity",
            "solid_choice": "Solid Choice — reputable company worth applying to",
            "do_your_research": "Do Your Research — mixed signals, investigate further",
            "proceed_with_caution": "Proceed With Caution — some red flags detected",
        }.get(verdict, verdict)
        lines.append(f"## Verdict: {verdict_display}")

        return "\n".join(lines)

    def _fallback(self, company: str, title: str) -> dict[str, Any]:
        """Fallback when Gemini is unavailable."""
        return {
            "company_name": company,
            "industry": "Unknown",
            "stage": "Unknown",
            "estimated_size": "Unknown",
            "known_for": "Company information unavailable — Gemini API not configured.",
            "tech_stack_signals": [],
            "culture_signals": [],
            "funding_status": "Unknown",
            "glassdoor_sentiment": "Unknown",
            "notable_facts": [],
            "potential_concerns": [],
            "verdict": "do_your_research",
        }
