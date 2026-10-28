"""Two-pass job scoring module: smart deterministic scoring + Gemini semantic analysis."""

import difflib
import logging
import math
import re
from collections import Counter
from typing import Any

from config.settings import settings
from src.llm_client import LLMClient, llm_client
from src.models.job_listing import DeepScore, JobListing, QuickScore
from src.models.preferences import SearchPreferences
from src.models.resume import ResumeData
from src.scoring_features import (
    BULK_SCORING_PROMPT,
    SENIORITY_LEVELS,
    STOPWORDS,
    SYNONYM_MAP,
    TITLE_FAMILIES,
    compute_token_weights,
    expand_synonyms,
    split_jd_sections,
    tokenize,
)

logger = logging.getLogger(__name__)

__all__ = ["Scorer", "tokenize"]


class Scorer:
    """Implements two-pass ranking: smart deterministic score + Gemini deep score."""

    def __init__(self, client: LLMClient | None = None):
        self.client = client or llm_client

    def quick_score(
        self,
        job: JobListing,
        resume: ResumeData,
        preferences: SearchPreferences,
    ) -> QuickScore:
        """Pass 1: smart deterministic composite score with synonym expansion,
        TF-IDF weighting, recency boost, title families, and JD section awareness.
        """
        # ----- Build resume token sets with recency weighting -----
        # Skills section (highest weight — 3x)
        skills_tokens: set[str] = set()
        for group in resume.skills:
            for s in group.skills:
                skills_tokens.update(tokenize(s))

        # Experience bullets with recency weighting
        # Most recent job = weight 3.0, second = 2.5, third = 2.0, older = 1.0
        recency_weights = [3.0, 2.5, 2.0, 1.5]
        weighted_resume_tokens: dict[str, float] = {}

        # Add skills tokens with high weight
        for t in skills_tokens:
            weighted_resume_tokens[t] = weighted_resume_tokens.get(t, 0) + 3.0

        # Add summary tokens
        for t in tokenize(resume.summary):
            weighted_resume_tokens[t] = weighted_resume_tokens.get(t, 0) + 2.0

        # Add experience tokens with recency decay
        for i, exp in enumerate(resume.experience):
            weight = recency_weights[i] if i < len(recency_weights) else 1.0
            for t in tokenize(exp.title):
                weighted_resume_tokens[t] = weighted_resume_tokens.get(t, 0) + weight
            for b in exp.bullets:
                for t in tokenize(b.text):
                    weighted_resume_tokens[t] = weighted_resume_tokens.get(t, 0) + weight

        # Add project tokens (weight 1.5)
        for p in resume.projects:
            for t in tokenize(p.name):
                weighted_resume_tokens[t] = weighted_resume_tokens.get(t, 0) + 1.5
            for t in tokenize(p.description):
                weighted_resume_tokens[t] = weighted_resume_tokens.get(t, 0) + 1.5
            for tech in p.technologies:
                for t in tokenize(tech):
                    weighted_resume_tokens[t] = weighted_resume_tokens.get(t, 0) + 2.0

        # Expand resume tokens with synonyms
        all_resume_tokens = expand_synonyms(set(weighted_resume_tokens.keys()))
        # Carry forward weights for expanded synonyms
        for token in list(all_resume_tokens):
            if token not in weighted_resume_tokens:
                # Find which original token produced this synonym
                for orig, syns in SYNONYM_MAP.items():
                    if token in syns and orig in weighted_resume_tokens:
                        weighted_resume_tokens[token] = weighted_resume_tokens[orig] * 0.8
                        break
                else:
                    weighted_resume_tokens[token] = 1.0

        # ----- Build JD token sets with section awareness -----
        jd_text = job.description_text or job.description_html or ""
        required_text, preferred_text, rest_text = split_jd_sections(jd_text)

        # Tokenize each section
        required_tokens = tokenize(required_text)
        preferred_tokens = tokenize(preferred_text)
        rest_tokens = tokenize(rest_text)
        title_tokens = tokenize(job.title)

        # Assign JD token weights: required=2.0, title=2.5, preferred=0.8, rest=1.0
        weighted_jd_tokens: dict[str, float] = {}
        for t in title_tokens:
            weighted_jd_tokens[t] = 2.5
        for t in required_tokens:
            weighted_jd_tokens[t] = max(weighted_jd_tokens.get(t, 0), 2.0)
        for t in rest_tokens:
            weighted_jd_tokens[t] = max(weighted_jd_tokens.get(t, 0), 1.0)
        for t in preferred_tokens:
            weighted_jd_tokens[t] = max(weighted_jd_tokens.get(t, 0), 0.8)

        # Expand JD tokens with synonyms
        all_jd_tokens = expand_synonyms(set(weighted_jd_tokens.keys()))
        for token in list(all_jd_tokens):
            if token not in weighted_jd_tokens:
                for orig, syns in SYNONYM_MAP.items():
                    if token in syns and orig in weighted_jd_tokens:
                        weighted_jd_tokens[token] = weighted_jd_tokens[orig] * 0.8
                        break
                else:
                    weighted_jd_tokens[token] = 1.0

        # Apply TF-IDF style weights on top
        jd_tfidf = compute_token_weights(all_jd_tokens, is_jd=True)
        resume_tfidf = compute_token_weights(all_resume_tokens, is_jd=False)

        # ----- Compute weighted overlap -----
        if not all_jd_tokens or not all_resume_tokens:
            keyword_overlap = 0.0
        else:
            intersection = all_resume_tokens.intersection(all_jd_tokens)

            # Weighted intersection score
            inter_score = 0.0
            for t in intersection:
                resume_w = weighted_resume_tokens.get(t, 1.0) * resume_tfidf.get(t, 1.0)
                jd_w = weighted_jd_tokens.get(t, 1.0) * jd_tfidf.get(t, 1.0)
                inter_score += min(resume_w, jd_w)  # take the lesser to avoid inflation

            # Weighted JD total (what the JD asks for)
            jd_total = sum(
                weighted_jd_tokens.get(t, 1.0) * jd_tfidf.get(t, 1.0)
                for t in all_jd_tokens
            )

            # Overlap = how much of JD's requirements does the resume cover
            keyword_overlap = inter_score / jd_total if jd_total > 0 else 0.0
            keyword_overlap = min(1.0, keyword_overlap * 1.8)  # gentle scale

        # ----- Title match with family awareness -----
        title_lower = job.title.lower()
        best_title_ratio = 0.0

        for target in preferences.target_roles:
            target_lower = target.lower()

            # Exact substring
            if target_lower in title_lower or title_lower in target_lower:
                ratio = 1.0
            else:
                # Check if they belong to the same role family
                target_family = TITLE_FAMILIES.get(target_lower, set())
                job_family = TITLE_FAMILIES.get(title_lower, set())

                if target_family and (title_lower in target_family or target_lower in job_family):
                    ratio = 0.90  # same family = strong match
                elif target_family & job_family:
                    ratio = 0.85  # overlapping families
                else:
                    ratio = difflib.SequenceMatcher(None, target_lower, title_lower).ratio()

            if ratio > best_title_ratio:
                best_title_ratio = ratio

        # ----- Seniority match -----
        candidate_level = self._estimate_candidate_seniority(resume, preferences.min_seniority)
        job_level = self._estimate_job_seniority(job.title, jd_text)
        diff = abs(candidate_level - job_level)
        if diff == 0:
            seniority_match = 1.0
        elif diff == 1:
            seniority_match = 0.8
        elif diff == 2:
            seniority_match = 0.5
        else:
            seniority_match = 0.2

        # ----- Final composite -----
        composite = (
            keyword_overlap * 0.5 +
            best_title_ratio * 0.3 +
            seniority_match * 0.2
        )
        composite = round(min(1.0, max(0.0, composite)), 4)
        passes = composite >= settings.quick_score_threshold

        return QuickScore(
            job_id=job.id,
            keyword_overlap=round(keyword_overlap, 4),
            title_match=round(best_title_ratio, 4),
            seniority_match=round(seniority_match, 4),
            composite_score=composite,
            pass_to_deep_scoring=passes,
        )

    def _estimate_candidate_seniority(self, resume: ResumeData, preferred_min: str) -> int:
        """Infer candidate seniority level."""
        pref_level = SENIORITY_LEVELS.get(preferred_min.lower(), 3)
        highest_found = pref_level
        for exp in resume.experience:
            for word, level in SENIORITY_LEVELS.items():
                if word in exp.title.lower() and level > highest_found:
                    highest_found = level
        return highest_found

    def _estimate_job_seniority(self, title: str, description: str) -> int:
        """Infer target role seniority level from title and description."""
        title_lower = title.lower()
        for word, level in SENIORITY_LEVELS.items():
            if re.search(rf"\b{word}\b", title_lower):
                return level

        desc_lower = (description or "")[:1000].lower()
        if re.search(r"\b(7\+|8\+|10\+)\s*years", desc_lower):
            return 4
        if re.search(r"\b(4\+|5\+|6\+)\s*years", desc_lower):
            return 3
        if re.search(r"\b(1\+|2\+|3\+)\s*years", desc_lower):
            return 2

        return 3  # default mid-senior

    def rank_quick(
        self,
        jobs: list[JobListing],
        resume: ResumeData,
        preferences: SearchPreferences,
    ) -> list[tuple[JobListing, QuickScore]]:
        """Score and sort all jobs by composite score."""
        scored: list[tuple[JobListing, QuickScore]] = []
        for job in jobs:
            score = self.quick_score(job, resume, preferences)
            scored.append((job, score))
        # Stable sort: composite score desc, then company+title asc as tiebreaker
        scored.sort(key=lambda x: (-x[1].composite_score, x[0].company.lower(), x[0].title.lower()))
        return scored

    def deep_score_batch(
        self,
        candidates: list[JobListing],
        resume: ResumeData,
        batch_size: int = 30,
    ) -> list[DeepScore]:
        """Pass 2: deep semantic scoring with Gemini."""
        if not candidates:
            return []

        resume_summary = (
            f"Candidate: {resume.contact.name}\n"
            f"Summary: {resume.summary}\n"
            f"Key Skills: {', '.join(g.category + ': ' + ', '.join(g.skills) for g in resume.skills[:5])}\n"
            f"Experience: {'; '.join(exp.title + ' at ' + exp.company for exp in resume.experience)}\n"
        )

        all_deep_scores: list[DeepScore] = []

        for i in range(0, len(candidates), batch_size):
            chunk = candidates[i : i + batch_size]
            jobs_list = ""
            for idx, job in enumerate(chunk, start=1):
                clean_desc = (job.description_text or "")[:1200]
                jobs_list += f"\n--- JOB #{idx} (ID: {job.id}) ---\nTitle: {job.title}\nCompany: {job.company}\nDescription:\n{clean_desc}\n"

            prompt = BULK_SCORING_PROMPT.format(
                resume_summary=resume_summary,
                jobs_list=jobs_list,
            )

            try:
                scores = self.client.generate_structured_list(
                    prompt=prompt,
                    item_model=DeepScore,
                )
                all_deep_scores.extend(scores)
            except Exception as e:
                print(f"\n      ⚠️  Gemini deep scoring failed (all models exhausted): {e}")
                print(f"      Models tried: {', '.join(settings.all_models)}")
                print("      Using quick scores as fallback.")
                logger.debug("Deep scoring failed for batch %d: %s", i, e)
                for job in chunk:
                    fallback_score = 0.5
                    all_deep_scores.append(
                        DeepScore(
                            job_id=job.id,
                            semantic_match=fallback_score,
                            role_fit=f"Score estimated without Gemini for {job.title} at {job.company}.",
                            key_gaps=["Unable to analyze — Gemini API unavailable"],
                            recommendation="weak_match",
                        )
                    )

        return all_deep_scores
