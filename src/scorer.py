"""Two-pass job scoring module: fast deterministic keyword matching + Gemini semantic analysis."""

import difflib
import logging
import re
from typing import Any

from config.settings import settings
from src.llm_client import LLMClient, llm_client
from src.models.job_listing import DeepScore, JobListing, QuickScore
from src.models.preferences import SearchPreferences
from src.models.resume import ResumeData

logger = logging.getLogger(__name__)

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "cannot", "could", "did", "do", "does", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "has", "have", "having", "he", "her", "here",
    "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it",
    "its", "itself", "let's", "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off",
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
    "same", "she", "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who",
    "whom", "why", "with", "would", "you", "your", "yours", "yourself", "yourselves", "will", "shall",
}

SENIORITY_LEVELS = {
    "intern": 1,
    "entry": 1,
    "junior": 1,
    "associate": 1,
    "mid": 2,
    "intermediate": 2,
    "senior": 3,
    "sr": 3,
    "lead": 3,
    "staff": 4,
    "principal": 4,
    "architect": 4,
    "director": 5,
    "vp": 5,
    "head": 5,
}

BULK_SCORING_PROMPT = """You are scoring job descriptions against a candidate's profile. For each job, analyze semantic fit beyond simple keyword matching. Consider: role scope alignment, seniority match, domain relevance, technical stack overlap, and growth trajectory fit.

CANDIDATE PROFILE:
{resume_summary}

JOBS TO SCORE:
{jobs_list}

For each job, return a JSON object with these fields:
- job_id: string — the job ID provided
- semantic_match: float — 0.0 to 1.0, how well the candidate fits this role
- role_fit: string — one sentence explaining why this is or isn't a good fit
- key_gaps: list of strings — skills or qualifications the candidate lacks for this role
- recommendation: one of "strong_match", "good_match", "weak_match", "skip"

Calibration guide:
- strong_match (0.85+): candidate meets 85%+ of requirements, seniority aligns, domain is relevant
- good_match (0.65-0.84): candidate meets most requirements, minor gaps exist
- weak_match (0.40-0.64): significant gaps but transferable experience exists
- skip (below 0.40): fundamental misalignment in seniority, domain, or core skills

Return a JSON array of objects. Be precise and calibrated — do not inflate scores."""


def tokenize(text: str) -> set[str]:
    """Tokenize text into cleaned words and bigrams."""
    if not text:
        return set()
    cleaned = re.sub(r"[^\w\s\+\#\.]", " ", text.lower())
    words = [w.strip() for w in cleaned.split() if w.strip() and w not in STOPWORDS and len(w) > 1]
    tokens = set(words)

    # Generate 2-word ngrams (e.g. 'data engineer', 'machine learning', 'fastapi backend')
    for i in range(len(words) - 1):
        tokens.add(f"{words[i]} {words[i+1]}")
    return tokens


class Scorer:
    """Implements two-pass ranking: fast deterministic keyword score + Gemini deep score."""

    def __init__(self, client: LLMClient | None = None):
        self.client = client or llm_client

    def quick_score(
        self,
        job: JobListing,
        resume: ResumeData,
        preferences: SearchPreferences,
    ) -> QuickScore:
        """Pass 1: fast deterministic composite score."""
        # 1. Keyword overlap
        tech_skills: set[str] = set()
        for group in resume.skills:
            for s in group.skills:
                tech_skills.update(tokenize(s))

        all_resume_tokens: set[str] = set()
        for group in resume.skills:
            for s in group.skills:
                all_resume_tokens.update(tokenize(s))
        all_resume_tokens.update(tokenize(resume.summary))
        for exp in resume.experience:
            all_resume_tokens.update(tokenize(exp.title))
            for b in exp.bullets:
                all_resume_tokens.update(tokenize(b.text))
        for p in resume.projects:
            all_resume_tokens.update(tokenize(p.name))
            all_resume_tokens.update(tokenize(p.description))
            for tech in p.technologies:
                all_resume_tokens.update(tokenize(tech))

        jd_tokens = tokenize(job.description_text or job.description_html)
        jd_tokens.update(tokenize(job.title))

        if not jd_tokens or not all_resume_tokens:
            keyword_overlap = 0.0
        else:
            # Weighted Jaccard
            intersection = all_resume_tokens.intersection(jd_tokens)
            union = all_resume_tokens.union(jd_tokens)

            # Weight tech skills higher (2.0) vs general tokens (1.0)
            inter_weight = sum(2.0 if t in tech_skills else 1.0 for t in intersection)
            union_weight = sum(2.0 if t in tech_skills else 1.0 for t in union)
            keyword_overlap = inter_weight / union_weight if union_weight > 0 else 0.0
            # Scale slightly up for readability since resume union JD is large
            keyword_overlap = min(1.0, keyword_overlap * 2.5)

        # 2. Title match
        title_lower = job.title.lower()
        best_title_ratio = 0.0
        for target in preferences.target_roles:
            target_lower = target.lower()
            if target_lower in title_lower or title_lower in target_lower:
                ratio = 1.0
            else:
                ratio = difflib.SequenceMatcher(None, target_lower, title_lower).ratio()
            if ratio > best_title_ratio:
                best_title_ratio = ratio

        # 3. Seniority match
        candidate_level = self._estimate_candidate_seniority(resume, preferences.min_seniority)
        job_level = self._estimate_job_seniority(job.title, job.description_text)
        diff = abs(candidate_level - job_level)
        if diff == 0:
            seniority_match = 1.0
        elif diff == 1:
            seniority_match = 0.8
        elif diff == 2:
            seniority_match = 0.5
        else:
            seniority_match = 0.2

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
        # Default to preferred seniority if configured
        pref_level = SENIORITY_LEVELS.get(preferred_min.lower(), 3)
        # Check titles in experience
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
        scored.sort(key=lambda x: x[1].composite_score, reverse=True)
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
                # Print error visibly so user knows Gemini scoring failed
                print(f"\n      ⚠️  Gemini deep scoring failed: {e}")
                print("      Using quick scores as fallback. Check your GOOGLE_API_KEY in .env")
                logger.debug("Deep scoring failed for batch %d: %s", i, e)
                # Fallback: use quick score as proxy when Gemini is unavailable
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
