"""Resume matcher module: compares JD analysis keywords against master resume."""

import json
import logging
from pathlib import Path
import re
from typing import Any

from src.models.jd import JDAnalysis, Keyword
from src.models.match import KeywordMatch, MatchReport, SectionRecommendation
from src.models.resume import ResumeData

logger = logging.getLogger(__name__)

# Common tech synonyms and abbreviations
TECH_SYNONYMS = {
    "k8s": "kubernetes",
    "kubernetes": "k8s",
    "postgres": "postgresql",
    "postgresql": "postgres",
    "py": "python",
    "ts": "typescript",
    "js": "javascript",
    "aws": "amazon web services",
    "amazon web services": "aws",
    "gcp": "google cloud",
    "google cloud": "gcp",
    "iac": "terraform",
    "terraform": "iac",
    "rest": "restful api",
    "ci/cd": "cicd",
}


class ResumeMatcher:
    """Matches JD keywords against resume content and produces a MatchReport."""

    def match(
        self,
        jd_analysis: JDAnalysis,
        resume: ResumeData,
        output_dir: Path | None = None,
    ) -> MatchReport:
        """Analyze keyword coverage, promotion opportunities, and gaps."""
        # Index all resume content
        skills_by_category: dict[str, list[str]] = {
            group.category: [s.lower() for s in group.skills] for group in resume.skills
        }
        all_skills_flat = {s.lower(): group.category for group in resume.skills for s in group.skills}

        bullet_occurrences: dict[str, list[str]] = {}
        for exp in resume.experience:
            for b in exp.bullets:
                text_lower = b.text.lower()
                for word in text_lower.split():
                    clean_word = re.sub(r"[^\w]", "", word)
                    if clean_word:
                        bullet_occurrences.setdefault(clean_word, []).append(b.id)

        summary_lower = resume.summary.lower()

        keywords_present: list[KeywordMatch] = []
        keywords_promotable: list[KeywordMatch] = []
        keywords_addable: list[KeywordMatch] = []
        keywords_gap: list[KeywordMatch] = []

        critical_covered = 0
        total_critical = 0
        high_covered = 0
        total_high = 0

        for kw in jd_analysis.keywords:
            term_lower = kw.term.lower().strip()
            if kw.category == "critical":
                total_critical += 1
            elif kw.category == "high":
                total_high += 1

            # 1. Check if explicitly in skills
            found_in_skill = None
            for s, cat in all_skills_flat.items():
                if term_lower in s or s in term_lower:
                    found_in_skill = f"Skills ({cat}: {s})"
                    break

            # 2. Check occurrences in bullets
            found_bullets = []
            for exp in resume.experience:
                for b in exp.bullets:
                    if re.search(rf"\b{re.escape(term_lower)}\b", b.text.lower()):
                        found_bullets.append(b.id)

            for proj in resume.projects:
                for b in proj.bullets:
                    if re.search(rf"\b{re.escape(term_lower)}\b", b.text.lower()):
                        found_bullets.append(b.id)
                for tech in proj.technologies:
                    if term_lower in tech.lower() or tech.lower() in term_lower:
                        found_bullets.append(f"{proj.name} ({tech})")

            # 3. Classify keyword status
            if found_in_skill:
                match_item = KeywordMatch(
                    term=kw.term,
                    category=kw.category,
                    status="present",
                    found_in=found_in_skill,
                    suggestion="Already prominently featured in Skills section.",
                )
                keywords_present.append(match_item)
                if kw.category == "critical":
                    critical_covered += 1
                elif kw.category == "high":
                    high_covered += 1

            elif len(found_bullets) >= 2 or term_lower in summary_lower:
                match_item = KeywordMatch(
                    term=kw.term,
                    category=kw.category,
                    status="present",
                    found_in=f"Mentioned in summary or {len(found_bullets)} bullets",
                    suggestion="Ensure prominent visibility in target role bullets.",
                )
                keywords_present.append(match_item)
                if kw.category == "critical":
                    critical_covered += 1
                elif kw.category == "high":
                    high_covered += 1

            elif len(found_bullets) == 1:
                # Buried in single bullet -> promotable
                match_item = KeywordMatch(
                    term=kw.term,
                    category=kw.category,
                    status="promotable",
                    found_in=f"Found in bullet {found_bullets[0]}",
                    suggestion=f"Promote '{kw.term}' into technical skills or highlight in professional summary.",
                )
                keywords_promotable.append(match_item)
                # Counted as covered because candidate possesses it
                if kw.category == "critical":
                    critical_covered += 1
                elif kw.category == "high":
                    high_covered += 1

            else:
                # Check for synonym/addable or gap
                synonym = TECH_SYNONYMS.get(term_lower)
                if synonym and (synonym in all_skills_flat or any(synonym in b.lower() for exp in resume.experience for b in [x.text for x in exp.bullets])):
                    match_item = KeywordMatch(
                        term=kw.term,
                        category=kw.category,
                        status="addable",
                        found_in=f"Synonym '{synonym}' found in candidate background",
                        suggestion=f"Use standard JD terminology '{kw.term}' alongside '{synonym}'.",
                    )
                    keywords_addable.append(match_item)
                    if kw.category == "critical":
                        critical_covered += 0.5
                    elif kw.category == "high":
                        high_covered += 0.5
                else:
                    match_item = KeywordMatch(
                        term=kw.term,
                        category=kw.category,
                        status="gap",
                        found_in=None,
                        suggestion=f"Skill '{kw.term}' not demonstrated in master resume. Do not fabricate.",
                    )
                    keywords_gap.append(match_item)

        # Coverage score calculation
        denominator = (total_critical * 1.0) + (total_high * 0.7)
        if denominator > 0:
            coverage = ((critical_covered * 1.0) + (high_covered * 0.7)) / denominator
        else:
            coverage = 1.0
        coverage_score = round(min(1.0, max(0.0, coverage)), 4)

        # Section recommendations
        recommendations = self._generate_recommendations(
            jd_analysis=jd_analysis,
            keywords_promotable=keywords_promotable,
            keywords_present=keywords_present,
            resume=resume,
        )

        report = MatchReport(
            job_id=jd_analysis.job_id,
            application_url=jd_analysis.application_url,
            coverage_score=coverage_score,
            keywords_present=keywords_present,
            keywords_promotable=keywords_promotable,
            keywords_addable=keywords_addable,
            keywords_gap=keywords_gap,
            section_recommendations=recommendations,
        )

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_file = output_dir / "match_report.json"
            out_file.write_text(json.dumps(report.model_dump(), indent=2, default=str), encoding="utf-8")

        return report

    def _generate_recommendations(
        self,
        jd_analysis: JDAnalysis,
        keywords_promotable: list[KeywordMatch],
        keywords_present: list[KeywordMatch],
        resume: ResumeData,
    ) -> list[SectionRecommendation]:
        """Generate deterministic recommendations for resume tailoring."""
        recs: list[SectionRecommendation] = []

        # Recommend rewriting summary for role title
        recs.append(
            SectionRecommendation(
                section="Professional Summary",
                action="Align summary with role focus",
                reason=f"Tailor opening statements to highlight experience relevant to {jd_analysis.job_title}.",
            )
        )

        # Recommend skill promotion
        if keywords_promotable:
            promotable_terms = ", ".join(m.term for m in keywords_promotable[:4])
            recs.append(
                SectionRecommendation(
                    section="Technical Skills",
                    action=f"Promote buried keywords: {promotable_terms}",
                    reason="These skills exist in experience bullets but are not prominent in the skills matrix.",
                )
            )

        # Recommend reordering skill groups if relevant
        recs.append(
            SectionRecommendation(
                section="Technical Skills",
                action="Reorder skill groups",
                reason="Place the most relevant technical domains at the top of the skills grid.",
            )
        )

        return recs
