"""Two-pass job scoring module: smart deterministic scoring + Gemini semantic analysis.

Pass 1 improvements over naive keyword matching:
1. Tech synonym map — "ETL" matches "data pipeline", "k8s" matches "Kubernetes"
2. TF-IDF weighting — rare terms (Kafka, dbt) matter more than common ones (data, team)
3. Recency weighting — skills from your latest job count 3x, oldest job counts 1x
4. Title family matching — reuses role families so "Data Platform Engineer" matches "Data Engineer"
5. JD section awareness — "Required" keywords count 2x vs "Nice to have"
"""

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
    "looking", "work", "working", "team", "role", "company", "experience", "ability", "using",
    "including", "also", "well", "new", "help", "join", "build", "building", "strong", "good",
    "great", "like", "need", "want", "make", "ensure", "responsible", "opportunity", "ideal",
}

SENIORITY_LEVELS = {
    "intern": 1, "entry": 1, "junior": 1, "associate": 1,
    "mid": 2, "intermediate": 2,
    "senior": 3, "sr": 3, "lead": 3,
    "staff": 4, "principal": 4, "architect": 4,
    "director": 5, "vp": 5, "head": 5,
}

# ---------------------------------------------------------------------------
# 1. TECH SYNONYM MAP — connects equivalent terms
# ---------------------------------------------------------------------------
# Each group shares the same canonical key. When any term in a group appears,
# all terms in that group are considered "matched".
_SYNONYM_GROUPS = [
    # Languages & runtimes
    ["python", "python3", "cpython"],
    ["javascript", "js", "ecmascript", "es6", "es2015"],
    ["typescript", "ts"],
    ["golang", "go"],
    ["c#", "csharp", "dotnet", ".net"],
    ["c++", "cpp"],
    ["ruby", "rails", "ruby on rails"],
    ["java", "jvm", "spring", "spring boot"],
    ["rust", "rustlang"],
    ["scala", "jvm"],
    ["r", "rstats"],
    ["php", "laravel"],
    ["swift", "swiftui"],
    ["kotlin", "android"],

    # Data & ETL
    ["etl", "data pipeline", "data pipelines", "data integration", "data ingestion"],
    ["apache spark", "spark", "pyspark"],
    ["apache kafka", "kafka", "event streaming", "message queue", "message broker"],
    ["apache airflow", "airflow", "dag", "workflow orchestration"],
    ["apache flink", "flink", "stream processing"],
    ["dbt", "data build tool", "analytics engineering"],
    ["data warehouse", "dwh", "data warehousing", "olap"],
    ["data lake", "data lakehouse", "delta lake"],
    ["data modeling", "dimensional modeling", "star schema", "data models"],
    ["batch processing", "batch jobs", "batch pipeline"],
    ["real-time", "real time", "streaming", "stream processing"],

    # Databases
    ["postgresql", "postgres", "psql"],
    ["mysql", "mariadb"],
    ["mongodb", "mongo", "nosql"],
    ["redis", "cache", "in-memory"],
    ["elasticsearch", "elastic", "opensearch", "elk"],
    ["cassandra", "scylladb"],
    ["dynamodb", "dynamo"],
    ["snowflake", "snowflake db"],
    ["bigquery", "bq", "google bigquery"],
    ["redshift", "amazon redshift"],
    ["databricks", "databricks lakehouse"],
    ["sql", "structured query language"],

    # Cloud
    ["aws", "amazon web services", "amazon cloud"],
    ["gcp", "google cloud", "google cloud platform"],
    ["azure", "microsoft azure", "microsoft cloud"],
    ["s3", "amazon s3", "object storage"],
    ["ec2", "amazon ec2", "compute instance"],
    ["lambda", "aws lambda", "serverless function"],
    ["iam", "identity access management"],
    ["cloudformation", "cdk", "aws cdk"],

    # Infrastructure & DevOps
    ["kubernetes", "k8s", "container orchestration"],
    ["docker", "containers", "containerization", "container"],
    ["terraform", "infrastructure as code", "iac"],
    ["ansible", "configuration management"],
    ["ci/cd", "ci cd", "cicd", "continuous integration", "continuous deployment", "continuous delivery"],
    ["github actions", "github ci"],
    ["jenkins", "jenkins ci"],
    ["gitlab ci", "gitlab cicd"],
    ["helm", "helm charts"],
    ["argocd", "argo cd", "gitops"],
    ["prometheus", "grafana", "monitoring", "observability"],
    ["datadog", "apm"],

    # ML / AI
    ["machine learning", "ml", "statistical learning"],
    ["deep learning", "dl", "neural networks", "neural network"],
    ["nlp", "natural language processing", "text processing"],
    ["computer vision", "cv", "image recognition"],
    ["pytorch", "torch"],
    ["tensorflow", "tf"],
    ["llm", "large language model", "large language models", "generative ai", "genai"],
    ["mlops", "ml ops", "ml engineering"],
    ["feature store", "feature engineering"],

    # Frontend
    ["react", "reactjs", "react.js"],
    ["vue", "vuejs", "vue.js"],
    ["angular", "angularjs"],
    ["next.js", "nextjs", "next"],
    ["svelte", "sveltekit"],
    ["html", "html5"],
    ["css", "css3", "tailwind", "tailwindcss"],

    # APIs & Protocols
    ["rest", "restful", "rest api", "restful api"],
    ["graphql", "gql"],
    ["grpc", "protobuf", "protocol buffers"],
    ["websocket", "websockets", "ws"],
    ["api", "apis", "web services"],
    ["microservices", "micro services", "service oriented"],

    # Data formats
    ["json", "json data"],
    ["parquet", "apache parquet", "columnar"],
    ["avro", "apache avro"],
    ["protobuf", "protocol buffers"],

    # Testing
    ["unit testing", "unit tests", "pytest", "jest", "junit"],
    ["integration testing", "integration tests"],
    ["tdd", "test driven development"],

    # Methodologies
    ["agile", "scrum", "kanban", "sprint"],
    ["distributed systems", "distributed computing", "distributed architecture"],
    ["event driven", "event-driven architecture", "eda"],
    ["data governance", "data quality", "data catalog"],
    ["version control", "git", "github", "gitlab", "bitbucket"],
]

# Build a lookup: term → set of all synonyms (including itself)
SYNONYM_MAP: dict[str, set[str]] = {}
for group in _SYNONYM_GROUPS:
    normalized = set(t.lower() for t in group)
    for term in normalized:
        SYNONYM_MAP[term] = normalized

# ---------------------------------------------------------------------------
# 5. TITLE FAMILY MAP — reuse role families from role_suggester
# ---------------------------------------------------------------------------
TITLE_FAMILIES: dict[str, set[str]] = {}
try:
    from src.role_suggester import ROLE_FAMILIES
    for _family_name, titles in ROLE_FAMILIES.items():
        normalized_titles = set(t.lower() for t in titles)
        for t in normalized_titles:
            TITLE_FAMILIES[t] = normalized_titles
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------
def tokenize(text: str) -> set[str]:
    """Tokenize text into cleaned words and bigrams."""
    if not text:
        return set()
    cleaned = re.sub(r"[^\w\s\+\#\./]", " ", text.lower())
    words = [w.strip() for w in cleaned.split() if w.strip() and w not in STOPWORDS and len(w) > 1]
    tokens = set(words)

    # Generate 2-word ngrams
    for i in range(len(words) - 1):
        tokens.add(f"{words[i]} {words[i+1]}")
    # Generate 3-word ngrams for compound terms
    for i in range(len(words) - 2):
        tokens.add(f"{words[i]} {words[i+1]} {words[i+2]}")
    return tokens


def expand_synonyms(tokens: set[str]) -> set[str]:
    """Expand a token set with all known synonyms."""
    expanded = set(tokens)
    for token in tokens:
        if token in SYNONYM_MAP:
            expanded.update(SYNONYM_MAP[token])
    return expanded


# ---------------------------------------------------------------------------
# JD section detection — "Required" keywords count more than "Nice to have"
# ---------------------------------------------------------------------------
_REQUIRED_HEADERS = re.compile(
    r"(?:requirements?|required|qualifications?|must.have|what you.ll need|what we.re looking for|"
    r"minimum qualifications?|basic qualifications?|essential|you have|you bring)",
    re.IGNORECASE,
)
_PREFERRED_HEADERS = re.compile(
    r"(?:nice.to.have|preferred|bonus|plus|ideal|desired|additional|not required|good to have)",
    re.IGNORECASE,
)


def split_jd_sections(text: str) -> tuple[str, str, str]:
    """Split JD text into (required_section, preferred_section, rest).

    Returns the text portions that fall under required headings,
    preferred headings, and everything else.
    """
    if not text:
        return ("", "", "")

    lines = text.split("\n")
    required_lines: list[str] = []
    preferred_lines: list[str] = []
    rest_lines: list[str] = []
    current_bucket = rest_lines

    for line in lines:
        stripped = line.strip()
        if _REQUIRED_HEADERS.search(stripped):
            current_bucket = required_lines
        elif _PREFERRED_HEADERS.search(stripped):
            current_bucket = preferred_lines
        current_bucket.append(line)

    return (
        "\n".join(required_lines),
        "\n".join(preferred_lines),
        "\n".join(rest_lines),
    )


# ---------------------------------------------------------------------------
# TF-IDF helpers
# ---------------------------------------------------------------------------
# Pre-computed IDF-like weights for common tech terms.
# Rare/specific terms get higher weight, generic terms get lower.
_GENERIC_TERMS = {
    "software", "engineer", "engineering", "developer", "development", "senior",
    "staff", "lead", "manager", "design", "develop", "system", "systems",
    "service", "services", "platform", "product", "support", "solution",
    "solutions", "project", "process", "technical", "technology", "tools",
    "code", "application", "applications", "performance", "quality",
    "collaborate", "collaboration", "cross-functional", "stakeholders",
    "communicate", "communication", "problem", "solving", "analytical",
}


def compute_token_weights(tokens: set[str], is_jd: bool = False) -> dict[str, float]:
    """Assign weights to tokens. Rare/technical terms get higher weight."""
    weights: dict[str, float] = {}
    for token in tokens:
        words = token.split()
        # Base weight
        w = 1.0

        # Boost multi-word terms (more specific)
        if len(words) >= 2:
            w *= 1.5
        if len(words) >= 3:
            w *= 1.3

        # Boost if it's a known tech synonym (means it's a real technology, not generic)
        if token in SYNONYM_MAP:
            w *= 2.0

        # Penalize generic terms
        if any(word in _GENERIC_TERMS for word in words):
            w *= 0.4

        # Penalize very short tokens (likely noise)
        if len(token) <= 2 and token not in SYNONYM_MAP:
            w *= 0.3

        weights[token] = w
    return weights


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

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
