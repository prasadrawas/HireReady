"""Cover letter generator using Gemini with evidence-linked claims from the master resume."""

import json
import logging
from pathlib import Path

from src.llm_client import LLMClient, llm_client
from src.models.jd import JDAnalysis
from src.models.match import MatchReport
from src.models.resume import ResumeData

logger = logging.getLogger(__name__)

COVER_LETTER_PROMPT = """You are writing a professional cover letter for a specific job application. You will receive the candidate's resume data, the job analysis with extracted keywords, and a match report.

CANDIDATE RESUME:
{resume_data}

JOB ANALYSIS:
{jd_analysis}

MATCH REPORT:
{match_report}

Write a concise, compelling cover letter (250-350 words) that:

1. Opens with a strong hook referencing the specific role and company — no generic "I am writing to apply" openings.
2. Highlights 2-3 of the candidate's most relevant achievements that directly address the JD's critical requirements. Use specific details from the resume.
3. Connects the candidate's experience to the company's stated needs, using terminology from the JD where it accurately describes the candidate's work.
4. Closes with confidence and a call to action.

STRICT RULES:
- Every claim MUST be supported by the candidate's actual resume. Do NOT invent achievements, metrics, skills, or experience.
- Do NOT claim skills the candidate doesn't have. If the JD asks for something not in the resume, do not mention it.
- Do NOT repeat the resume verbatim — synthesize and tell a story.
- Use a professional but natural tone — not robotic, not overly casual.
- Do NOT include a header/address block — just the letter body.
- Mention the company name and role title naturally in the text.

Return a JSON object with these fields:
{{
  "body": "The full cover letter text with paragraph breaks as \\n\\n",
  "key_points": ["List of 2-3 bullet points summarizing what the letter emphasizes"],
  "source_bullets": ["List of bullet IDs from the resume that support the letter's claims"]
}}
"""


class CoverLetterGenerator:
    """Generates tailored cover letters using Gemini with evidence linking."""

    def __init__(self, client: LLMClient | None = None):
        self.client = client or llm_client

    def generate(
        self,
        resume: ResumeData,
        jd_analysis: JDAnalysis,
        match_report: MatchReport,
        output_dir: Path | None = None,
    ) -> dict:
        """Generate a cover letter and save to output directory."""
        prompt = (
            COVER_LETTER_PROMPT
            .replace("{resume_data}", json.dumps(resume.model_dump(), indent=2, default=str))
            .replace("{jd_analysis}", json.dumps(jd_analysis.model_dump(), indent=2, default=str))
            .replace("{match_report}", json.dumps(match_report.model_dump(), indent=2, default=str))
        )

        try:
            raw_text, error = self.client._call_model(prompt, temperature=0.3)
            if raw_text is None:
                raise Exception(f"Gemini call failed: {error}")
            result = self.client._clean_and_decode_json(raw_text)
        except Exception as e:
            logger.debug("Cover letter generation failed: %s. Using fallback.", e)
            result = self._fallback(resume, jd_analysis)

        body = result.get("body", "")
        key_points = result.get("key_points", [])
        source_bullets = result.get("source_bullets", [])

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Plain text version
            (output_dir / "cover_letter.txt").write_text(body, encoding="utf-8")

            # HTML version
            html = self._render_html(body, jd_analysis)
            (output_dir / "cover_letter.html").write_text(html, encoding="utf-8")

            # Metadata
            metadata = {
                "company": jd_analysis.company,
                "role": jd_analysis.job_title,
                "key_points": key_points,
                "source_bullets": source_bullets,
                "word_count": len(body.split()),
            }
            (output_dir / "cover_letter_meta.json").write_text(
                json.dumps(metadata, indent=2), encoding="utf-8"
            )

        return result

    def _render_html(self, body: str, jd_analysis: JDAnalysis) -> str:
        """Render cover letter body as clean HTML."""
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        p_tags = "\n".join(f"    <p>{p}</p>" for p in paragraphs)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Cover Letter — {jd_analysis.company} — {jd_analysis.job_title}</title>
  <style>
    body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 700px; margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.7; font-size: 14px; }}
    p {{ margin-bottom: 1em; }}
  </style>
</head>
<body>
{p_tags}
</body>
</html>"""

    def _fallback(self, resume: ResumeData, jd_analysis: JDAnalysis) -> dict:
        """Conservative fallback when Gemini is unavailable."""
        name = resume.contact.name
        company = jd_analysis.company
        role = jd_analysis.job_title

        top_skills = []
        for sg in resume.skills[:2]:
            top_skills.extend(sg.skills[:3])
        skills_str = ", ".join(top_skills[:5])

        body = (
            f"I am excited to apply for the {role} position at {company}. "
            f"With experience spanning {skills_str}, I am confident in my ability to contribute meaningfully to your team.\n\n"
            f"Please find my resume attached for your review. I look forward to discussing how my background aligns with your needs."
        )
        return {"body": body, "key_points": [], "source_bullets": []}
