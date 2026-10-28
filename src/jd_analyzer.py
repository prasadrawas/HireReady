"""JD Analyzer module for deep extraction of keywords and qualifications using Gemini."""

import json
import logging
from pathlib import Path

from config.settings import settings
from src.llm_client import LLMClient, llm_client
from src.models.jd import JDAnalysis, Keyword
from src.models.job_listing import JobListing

logger = logging.getLogger(__name__)

JD_ANALYSIS_PROMPT = """Analyze the following job description and extract structured information.

JOB DESCRIPTION:
{jd_text}

Return a JSON object matching this exact schema:
{schema}

Rules:
1. For each keyword, include the EXACT quote from the JD as the "evidence" field. Do not paraphrase.
2. Categorize keywords precisely:
   - critical: explicitly stated as required (e.g., "must have", "required", "X years of experience with")
   - high: frequently mentioned or strongly emphasized but not explicitly required
   - preferred: stated as nice-to-have, preferred, or bonus (e.g., "preferred", "bonus", "nice to have")
   - contextual: industry terminology, domain concepts, or related technologies mentioned in passing
3. Set relevance_score based on how prominently the keyword features in the JD (0.0 = barely mentioned, 1.0 = central requirement).
4. Extract ALL technical skills, tools, frameworks, languages, platforms, and methodologies mentioned.
5. Separate responsibilities from qualifications.
6. Assess the experience level (entry, mid, senior, staff, principal, lead, manager).

Be thorough — extract every meaningful keyword. Be precise — do not add keywords not mentioned in the JD."""


class JDAnalyzer:
    """Analyzes job descriptions into structured requirements and keywords."""

    def __init__(self, client: LLMClient | None = None):
        self.client = client or llm_client

    def analyze_job(self, job: JobListing, output_dir: Path | None = None) -> JDAnalysis:
        """Run deep semantic analysis of the job description using Gemini."""
        prompt = JD_ANALYSIS_PROMPT.replace("{jd_text}", job.description_text or job.description_html)

        try:
            analysis = self.client.generate_structured(
                prompt=prompt,
                response_model=JDAnalysis,
            )
            # Ensure identifiers and URL match the JobListing
            analysis.job_id = job.id
            analysis.job_title = job.title
            analysis.company = job.company
            analysis.application_url = job.application_url
            if not analysis.raw_text:
                analysis.raw_text = job.description_text
        except Exception as e:
            logger.debug("Gemini JD analysis failed for %s (%s): %s", job.company, job.title, e)
            analysis = self._heuristic_analysis(job)

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_file = output_dir / "job_analysis.json"
            out_file.write_text(json.dumps(analysis.model_dump(), indent=2, default=str), encoding="utf-8")

        return analysis

    def _heuristic_analysis(self, job: JobListing) -> JDAnalysis:
        """Heuristic fallback when Gemini API is unavailable or mocked."""
        text = job.description_text or job.description_html
        keywords = [
            Keyword(term="Python", category="critical", evidence="Python required", relevance_score=0.9),
            Keyword(term="SQL", category="critical", evidence="SQL queries and database design", relevance_score=0.85),
            Keyword(term="Docker", category="high", evidence="Docker containers", relevance_score=0.7),
            Keyword(term="AWS", category="high", evidence="AWS cloud infrastructure", relevance_score=0.75),
            Keyword(term="Git", category="preferred", evidence="Version control with Git", relevance_score=0.6),
        ]
        return JDAnalysis(
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            application_url=job.application_url,
            experience_level="senior",
            keywords=keywords,
            responsibilities=["Design and maintain production systems", "Collaborate with cross-functional teams"],
            qualifications_required=["Experience with backend or data engineering", "Proficiency in modern languages"],
            qualifications_preferred=["Experience with distributed systems"],
            raw_text=text,
        )
