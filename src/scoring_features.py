"""Feature extraction, NLP tokenization, and synonym mapping for job scoring."""

import re
from typing import Any

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

SYNONYM_MAP: dict[str, set[str]] = {}
for group in _SYNONYM_GROUPS:
    normalized = set(t.lower() for t in group)
    for term in normalized:
        SYNONYM_MAP[term] = normalized

TITLE_FAMILIES: dict[str, set[str]] = {}
try:
    from src.role_suggester import ROLE_FAMILIES
    for _family_name, titles in ROLE_FAMILIES.items():
        normalized_titles = set(t.lower() for t in titles)
        for t in normalized_titles:
            TITLE_FAMILIES[t] = normalized_titles
except ImportError:
    pass


def tokenize(text: str) -> set[str]:
    """Tokenize text into cleaned words, bigrams, and trigrams."""
    if not text:
        return set()
    cleaned = re.sub(r"[^\w\s\+\#\./]", " ", text.lower())
    words = [w.strip() for w in cleaned.split() if w.strip() and w not in STOPWORDS and len(w) > 1]
    tokens = set(words)

    for i in range(len(words) - 1):
        tokens.add(f"{words[i]} {words[i+1]}")
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
    """Split JD text into (required_section, preferred_section, rest)."""
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
        w = 1.0

        if len(words) >= 2:
            w *= 1.5
        if len(words) >= 3:
            w *= 1.3

        if token in SYNONYM_MAP:
            w *= 2.0

        if any(word in _GENERIC_TERMS for word in words):
            w *= 0.4

        if len(token) <= 2 and token not in SYNONYM_MAP:
            w *= 0.3

        weights[token] = w
    return weights


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

