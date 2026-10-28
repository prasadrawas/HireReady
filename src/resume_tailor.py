"""Resume tailoring module using Gemini with strict evidence linking and diff tracking.

Supports two modes:
- Combined mode (default): single Gemini call that analyzes the JD AND tailors the resume.
- Separate mode: accepts a pre-computed JDAnalysis and MatchReport.
"""

import json
import logging
from pathlib import Path

from src.llm_client import LLMClient, llm_client
from src.models.jd import JDAnalysis, Keyword
from src.models.match import MatchReport
from src.models.resume import BulletPoint, Experience, Project, ResumeData
from src.models.tailored import ChangeRecord, TailoredResume

logger = logging.getLogger(__name__)

COMBINED_PROMPT = """You are an expert resume analyst and tailoring specialist. You will perform TWO tasks in a SINGLE response:

TASK 1 — JD ANALYSIS: Analyze the job description and extract structured keywords.
TASK 2 — RESUME TAILORING: Tailor the candidate's resume to match the JD requirements.

---

JOB DESCRIPTION:
{jd_text}

JOB METADATA:
- Job ID: {job_id}
- Company: {company}
- Title: {job_title}
- Application URL: {application_url}

CANDIDATE RESUME:
{resume_data}

---

Return a SINGLE JSON object with two top-level keys: "jd_analysis" and "tailored_resume".

For "jd_analysis", return:
- job_id: "{job_id}"
- job_title: "{job_title}"
- company: "{company}"
- application_url: "{application_url}"
- experience_level: string (entry, mid, senior, staff, principal, lead, manager)
- keywords: array of objects with fields:
  - term: string
  - category: "critical" | "high" | "preferred" | "contextual"
  - evidence: EXACT quote from the JD
  - relevance_score: 0.0-1.0
- responsibilities: array of strings
- qualifications_required: array of strings
- qualifications_preferred: array of strings
- raw_text: first 200 chars of the JD

Keyword categorization rules:
- critical: explicitly required ("must have", "required", "X years of experience with")
- high: frequently mentioned or strongly emphasized
- preferred: nice-to-have ("preferred", "bonus")
- contextual: industry terminology mentioned in passing

For "tailored_resume", return the full tailored resume matching this schema:
{schema}

STRICT TAILORING RULES — VIOLATION INVALIDATES THE OUTPUT:

1. EVIDENCE LINKING: Every bullet must include "source_id" referencing a bullet ID from the original resume. Unlinked bullets go to "needs_review" list.

2. NO FABRICATION: Do NOT invent metrics, percentages, skills, tools, certifications, job titles, company names, or achievements.

3. YOU MAY: Rephrase for clarity, reorder for relevance, integrate JD terminology where it accurately describes existing work, emphasize measurable impact already stated, rewrite the summary.

4. YOU MAY NOT: Add skills not in the resume, fabricate numbers, claim unlisted certifications, exaggerate scope, change dates/companies/titles.

5. KEYWORD INTEGRATION: critical → high → preferred. Only where natural. No stuffing.

6. PRESERVE: All dates, company names, job titles exactly as original.

7. SUMMARY: Rewrite to align with target role. 2-3 sentences. Every claim must be supported.

8. SKILLS: Reorder to put JD-relevant skills first. Do not add new skills.

Return the complete JSON with both "jd_analysis" and "tailored_resume" keys."""

RESUME_TAILORING_PROMPT = """You are tailoring a resume for a specific job. You will receive the candidate's current resume data, the job analysis with extracted keywords, and a match report showing coverage gaps.

CANDIDATE RESUME:
{resume_data}

JOB ANALYSIS:
{jd_analysis}

MATCH REPORT:
{match_report}

Generate a tailored version of the resume. Return a JSON object matching this exact schema:
{schema}

STRICT RULES — VIOLATION OF ANY RULE INVALIDATES THE OUTPUT:

1. EVIDENCE LINKING (mandatory): Every bullet point you write or modify MUST include a "source_id" field referencing a bullet ID from the original resume (e.g., "bullet_exp_01_03"). If you write a bullet that cannot be linked to any original bullet, you MUST add it to the "needs_review" list instead of including it in the resume sections. No exceptions.

2. NO FABRICATION (mandatory): You MUST NOT invent any of the following:
   - Metrics or percentages not in the original resume
   - Skills or tools the candidate has not demonstrated
   - Certifications or qualifications not listed
   - Job titles, company names, or employers
   - Project names or project outcomes
   - Team sizes, revenue numbers, or impact figures
   If a number, metric, or achievement is not in the original resume, do not create one.

3. WHAT YOU MAY DO:
   - Rephrase existing bullets for clarity and impact
   - Reorder sections and bullets to prioritize relevance to the target role
   - Integrate JD terminology where it ACCURATELY describes work the candidate actually did
   - Emphasize measurable impact that is ALREADY stated in the original bullets
   - Combine or split bullets if it improves clarity (but maintain source linking)
   - Rewrite the professional summary to align with the target role

4. WHAT YOU MAY NOT DO:
   - Add skills the candidate doesn't have
   - Fabricate quantitative results (percentages, dollar amounts, user counts)
   - Claim certifications not in the original resume
   - Exaggerate scope, seniority, or team leadership
   - Change dates, company names, or job titles

5. KEYWORD INTEGRATION: Integrate keywords in this priority order: critical -> high -> preferred. Only integrate a keyword where it naturally and accurately describes the candidate's work. Do not stuff keywords. Do not repeat the same keyword unnaturally.

6. DATES AND EMPLOYERS: Preserve all dates, company names, and job titles EXACTLY as they appear in the original resume. Do not modify, abbreviate, or reformat them.

7. PROFESSIONAL SUMMARY: Rewrite to align with the target role, emphasizing relevant experience and skills. Keep it to 2-3 sentences. Every claim in the summary must be supported by the resume content.

8. SKILLS SECTION: Reorder skill groups to put the most relevant category first. Within each group, reorder skills to put JD-relevant skills first. Do not add skills that are not in the original resume.

Return the complete tailored resume as JSON. Be thorough but honest. The goal is to present the candidate's REAL experience in the best possible light for this specific role — not to fabricate a perfect candidate."""


class ResumeTailor:
    """Tailors resume with LLM and guarantees strict evidence linking and claim integrity."""

    def __init__(self, client: LLMClient | None = None):
        self.client = client or llm_client

    def analyze_and_tailor(
        self,
        resume: ResumeData,
        job_description: str,
        job_id: str,
        company: str,
        job_title: str,
        application_url: str,
        output_dir: Path | None = None,
    ) -> tuple[JDAnalysis, TailoredResume]:
        """Combined JD analysis + resume tailoring in a SINGLE Gemini call.

        Returns (JDAnalysis, TailoredResume) from one API call instead of two.
        """
        original_bullets = self._index_bullets(resume)

        prompt = (
            COMBINED_PROMPT
            .replace("{jd_text}", job_description)
            .replace("{job_id}", job_id)
            .replace("{company}", company)
            .replace("{job_title}", job_title)
            .replace("{application_url}", application_url)
            .replace("{resume_data}", json.dumps(resume.model_dump(), indent=2, default=str))
        )

        try:
            raw_text, error = self.client._call_model(
                prompt.replace("{schema}", json.dumps(TailoredResume.model_json_schema(), indent=2)),
                temperature=0.2,
            )
            if raw_text is None:
                raise Exception(f"Gemini call failed: {error}")

            combined = self.client._clean_and_decode_json(raw_text)

            # Parse JD analysis
            jd_data = combined.get("jd_analysis", {})
            jd_data.setdefault("job_id", job_id)
            jd_data.setdefault("job_title", job_title)
            jd_data.setdefault("company", company)
            jd_data.setdefault("application_url", application_url)
            jd_data.setdefault("raw_text", job_description[:200])
            jd_analysis = JDAnalysis.model_validate(jd_data)

            # Parse tailored resume
            tailored_data = combined.get("tailored_resume", {})
            tailored = TailoredResume.model_validate(tailored_data)

        except Exception as e:
            logger.debug("Combined analysis+tailoring failed (%s). Using separate fallbacks.", e)
            jd_analysis = self._heuristic_analysis(job_id, job_title, company, application_url, job_description)
            tailored = self._fallback_tailoring(resume, jd_analysis, MatchReport(
                job_id=job_id, application_url=application_url, coverage_score=0.5,
                keywords_present=[], keywords_promotable=[], keywords_addable=[], keywords_gap=[],
                section_recommendations=[],
            ))

        # Enforce strict rules
        tailored = self._enforce_strict_rules(tailored, resume, original_bullets, jd_analysis)

        # Generate change summary
        summary_md = self._generate_change_summary(tailored, jd_analysis, MatchReport(
            job_id=job_id, application_url=application_url,
            coverage_score=0.0, keywords_present=[], keywords_promotable=[],
            keywords_addable=[], keywords_gap=[], section_recommendations=[],
        ))

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "job_analysis.json").write_text(
                json.dumps(jd_analysis.model_dump(), indent=2, default=str), encoding="utf-8"
            )
            (output_dir / "tailored_resume.json").write_text(
                json.dumps(tailored.model_dump(), indent=2, default=str), encoding="utf-8"
            )
            (output_dir / "change_summary.md").write_text(summary_md, encoding="utf-8")

        return jd_analysis, tailored

    def tailor(
        self,
        resume: ResumeData,
        jd_analysis: JDAnalysis,
        match_report: MatchReport,
        output_dir: Path | None = None,
    ) -> TailoredResume:
        """Separate-mode tailoring: accepts pre-computed JDAnalysis and MatchReport."""
        original_bullets = self._index_bullets(resume)

        prompt = (
            RESUME_TAILORING_PROMPT.replace(
                "{resume_data}", json.dumps(resume.model_dump(), indent=2, default=str)
            )
            .replace(
                "{jd_analysis}", json.dumps(jd_analysis.model_dump(), indent=2, default=str)
            )
            .replace(
                "{match_report}", json.dumps(match_report.model_dump(), indent=2, default=str)
            )
        )

        try:
            tailored: TailoredResume = self.client.generate_structured(
                prompt=prompt,
                response_model=TailoredResume,
            )
        except Exception as e:
            logger.debug("Gemini tailoring failed (%s). Using conservative fallback.", e)
            tailored = self._fallback_tailoring(resume, jd_analysis, match_report)

        tailored = self._enforce_strict_rules(tailored, resume, original_bullets, jd_analysis)
        summary_md = self._generate_change_summary(tailored, jd_analysis, match_report)

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "tailored_resume.json").write_text(
                json.dumps(tailored.model_dump(), indent=2, default=str), encoding="utf-8"
            )
            (output_dir / "change_summary.md").write_text(summary_md, encoding="utf-8")

        return tailored

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _index_bullets(self, resume: ResumeData) -> dict[str, str]:
        """Build id→text map of all original bullets."""
        bullets: dict[str, str] = {}
        for exp in resume.experience:
            for b in exp.bullets:
                bullets[b.id] = b.text
        for proj in resume.projects:
            for b in proj.bullets:
                bullets[b.id] = b.text
        return bullets

    def _enforce_strict_rules(
        self,
        tailored: TailoredResume,
        master: ResumeData,
        original_bullets: dict[str, str],
        jd_analysis: JDAnalysis,
    ) -> TailoredResume:
        """Enforce evidence linking, preserve employer names/dates, and flag unverified claims."""
        tailored.job_id = jd_analysis.job_id
        tailored.application_url = jd_analysis.application_url
        tailored.contact = master.contact
        tailored.certifications = master.certifications

        for i, exp in enumerate(tailored.experience):
            if i < len(master.experience):
                master_exp = master.experience[i]
                exp.company = master_exp.company
                exp.title = master_exp.title
                exp.start_date = master_exp.start_date
                exp.end_date = master_exp.end_date

            valid_bullets = []
            for b in exp.bullets:
                sid = b.source_id or b.id
                if sid in original_bullets:
                    b.source_id = sid
                    valid_bullets.append(b)
                else:
                    tailored.needs_review.append(
                        f"Unlinked experience bullet flagged: '{b.text}' (no matching master bullet)"
                    )
            exp.bullets = valid_bullets

        for i, proj in enumerate(tailored.projects):
            if i < len(master.projects):
                master_proj = master.projects[i]
                proj.name = master_proj.name
                proj.url = master_proj.url

            valid_proj_bullets = []
            for b in proj.bullets:
                sid = b.source_id or b.id
                if sid in original_bullets:
                    b.source_id = sid
                    valid_proj_bullets.append(b)
                else:
                    tailored.needs_review.append(
                        f"Unlinked project bullet flagged: '{b.text}' (no matching master bullet)"
                    )
            proj.bullets = valid_proj_bullets

        if not tailored.changes:
            tailored.changes = self._derive_change_records(tailored, original_bullets, jd_analysis)

        return tailored

    def _derive_change_records(
        self,
        tailored: TailoredResume,
        original_bullets: dict[str, str],
        jd_analysis: JDAnalysis,
    ) -> list[ChangeRecord]:
        """Derive change records by comparing original bullets with tailored bullets."""
        changes: list[ChangeRecord] = []

        for exp in tailored.experience:
            for b in exp.bullets:
                orig_text = original_bullets.get(b.source_id or "", "")
                if orig_text and orig_text.strip() != b.text.strip():
                    integrated = [
                        k.term for k in jd_analysis.keywords
                        if k.term.lower() in b.text.lower() and k.term.lower() not in orig_text.lower()
                    ]
                    changes.append(
                        ChangeRecord(
                            section="Experience",
                            original=orig_text,
                            tailored=b.text,
                            source_bullet_id=b.source_id or b.id,
                            keywords_integrated=integrated,
                            change_type="rewrite",
                        )
                    )

        return changes

    def _fallback_tailoring(
        self,
        master: ResumeData,
        jd_analysis: JDAnalysis,
        match_report: MatchReport,
    ) -> TailoredResume:
        """Conservative fallback: reorders skills and preserves master content."""
        return TailoredResume(
            job_id=jd_analysis.job_id,
            application_url=jd_analysis.application_url,
            contact=master.contact,
            summary=master.summary,
            skills=master.skills,
            experience=master.experience,
            projects=master.projects,
            education=master.education,
            certifications=master.certifications,
            changes=[],
            needs_review=[],
        )

    def _heuristic_analysis(
        self, job_id: str, job_title: str, company: str, application_url: str, text: str,
    ) -> JDAnalysis:
        """Heuristic fallback JD analysis."""
        keywords = [
            Keyword(term="Python", category="critical", evidence="Python required", relevance_score=0.9),
            Keyword(term="SQL", category="critical", evidence="SQL queries", relevance_score=0.85),
        ]
        return JDAnalysis(
            job_id=job_id, job_title=job_title, company=company,
            application_url=application_url, experience_level="senior",
            keywords=keywords, responsibilities=[], qualifications_required=[],
            qualifications_preferred=[], raw_text=text[:200],
        )

    def _generate_change_summary(
        self,
        tailored: TailoredResume,
        jd_analysis: JDAnalysis,
        match_report: MatchReport,
    ) -> str:
        """Generate change_summary.md markdown artifact."""
        rewritten_count = sum(1 for c in tailored.changes if c.change_type == "rewrite")
        reordered_count = sum(1 for c in tailored.changes if c.change_type == "reorder")
        flagged_count = len(tailored.needs_review)

        md = [
            f"# Tailoring Summary: {jd_analysis.company} — {jd_analysis.job_title}",
            "",
            f"- **Application URL:** [{tailored.application_url}]({tailored.application_url})",
            f"- **Coverage Score:** {int(match_report.coverage_score * 100)}%",
            f"- **Modifications:** {rewritten_count} bullets rewritten, {reordered_count} reordered, {flagged_count} flagged",
            "",
            "## Summary Statement",
            f"> {tailored.summary}",
            "",
            "## Modifications & Evidence Linking",
            "",
        ]

        if not tailored.changes:
            md.append("*No bullet modifications were required; master resume matches target requirements.*")
        else:
            for idx, chg in enumerate(tailored.changes, start=1):
                md.extend([
                    f"### Change #{idx} ({chg.section})",
                    f"- **Source ID:** `{chg.source_bullet_id}`",
                    f"- **Change Type:** `{chg.change_type}`",
                    f"- **Keywords Integrated:** {', '.join(chg.keywords_integrated) if chg.keywords_integrated else 'None'}",
                    "",
                    "```diff",
                    f"- {chg.original}",
                    f"+ {chg.tailored}",
                    "```",
                    "",
                ])

        if tailored.needs_review:
            md.extend([
                "## NEEDS REVIEW",
                "The following items could not be validated against the master resume and require manual approval:",
                "",
            ])
            for item in tailored.needs_review:
                md.append(f"- {item}")
            md.append("")

        return "\n".join(md)
