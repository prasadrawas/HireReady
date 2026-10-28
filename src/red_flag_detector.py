"""JD Red Flag Detector: identifies warning signs in job descriptions."""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


class RedFlag:
    """A single red flag detected in a JD."""

    def __init__(self, category: str, signal: str, evidence: str, severity: str = "warning"):
        self.category = category      # e.g. "unrealistic_requirements", "culture_warning"
        self.signal = signal          # e.g. "Requires 10+ years in a 5-year-old technology"
        self.evidence = evidence      # the actual text from the JD
        self.severity = severity      # "warning" or "critical"

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "signal": self.signal,
            "evidence": self.evidence,
            "severity": self.severity,
        }


class RedFlagDetector:
    """Scans JD text for common red flags that indicate a problematic role."""

    # --- Pattern groups ---

    OVERWORK_PATTERNS = [
        (r"wear\s+many\s+hats", "Expects one person to fill multiple roles"),
        (r"fast[- ]paced\s+environment", "\"Fast-paced\" often means understaffed or chaotic"),
        (r"thrive\s+under\s+pressure", "Pressure-focused culture"),
        (r"comfortable\s+with\s+ambiguity", "May lack clear direction or structure"),
        (r"startup\s+mentality", "May expect long hours without startup equity"),
        (r"hit\s+the\s+ground\s+running", "No onboarding or ramp-up time expected"),
        (r"self[- ]starter", "May mean minimal mentorship or management support"),
        (r"work\s+independently\s+with\s+(?:little|no|minimal)\s+(?:supervision|guidance)", "Little support structure"),
        (r"(?:24/7|on[- ]call|nights?\s+and\s+weekends?)", "Expects availability outside business hours"),
        (r"unlimited\s+(?:pto|vacation|time[- ]off)", "Often means no one actually takes time off"),
    ]

    UNREALISTIC_REQ_PATTERNS = [
        (r"(\d+)\+?\s+years?\s+(?:of\s+)?(?:experience\s+)?(?:with\s+|in\s+)(\w+)", None),  # handled by logic
        (r"must\s+have\s+(?:a\s+)?(?:phd|doctorate)", "PhD required — often unnecessary for the role"),
        (r"expert\s+(?:level\s+)?(?:in|with)\s+(?:\w+\s*,?\s*){5,}", "Requires expert-level in 5+ technologies"),
        (r"unicorn", "Looking for an impossibly perfect candidate"),
        (r"rockstar|ninja|guru|wizard|hacker", "Informal language often masks unrealistic expectations"),
    ]

    COMPENSATION_RED_FLAGS = [
        (r"(?:salary|compensation)\s+(?:is\s+)?(?:commensurate|competitive|negotiable)\s+with\s+experience", "Vague compensation — no range given"),
        (r"equity[- ]only|unpaid\s+internship", "No salary or unpaid work"),
        (r"stipend\s+(?:only|based)", "Stipend instead of proper salary"),
    ]

    TURNOVER_SIGNALS = [
        (r"recently\s+(?:vacated|opened|created)\s+(?:due\s+to|after)", "Position opened due to someone leaving"),
        (r"growing\s+(?:rapidly|quickly|fast)\s+and\s+need", "Rapid growth can mean chaos"),
        (r"immediate\s+(?:start|hire|need)", "Urgency may indicate high turnover"),
    ]

    VAGUE_ROLE_PATTERNS = [
        (r"other\s+duties\s+as\s+(?:assigned|needed|required)", "Open-ended scope — role boundaries unclear"),
        (r"and\s+(?:anything|everything)\s+(?:else|in\s+between)", "Unlimited scope"),
        (r"jack\s+of\s+all\s+trades", "Expects breadth over depth"),
    ]

    # Technologies and their rough inception years (for unrealistic experience checks)
    TECH_YEARS = {
        "kubernetes": 2014, "k8s": 2014, "docker": 2013, "terraform": 2014,
        "react": 2013, "vue": 2014, "svelte": 2016, "nextjs": 2016, "next.js": 2016,
        "typescript": 2012, "rust": 2010, "go": 2009, "golang": 2009,
        "swift": 2014, "kotlin": 2011, "flutter": 2017, "dbt": 2016,
        "snowflake": 2014, "databricks": 2013, "airflow": 2014,
        "graphql": 2015, "grpc": 2015, "kafka": 2011,
        "chatgpt": 2022, "openai": 2020, "langchain": 2022,
        "copilot": 2021, "llm": 2020, "generative ai": 2022,
    }

    @classmethod
    def scan(cls, description_text: str, title: str = "") -> list[RedFlag]:
        """Scan a JD for red flags. Returns list of RedFlag objects."""
        if not description_text:
            return []

        flags: list[RedFlag] = []
        text_lower = description_text.lower()
        combined = f"{title}\n{description_text}".lower()

        # 1. Overwork / culture warnings
        for pattern, signal in cls.OVERWORK_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                flags.append(RedFlag(
                    category="culture_warning",
                    signal=signal,
                    evidence=cls._extract_context(description_text, match),
                ))

        # 2. Unrealistic requirements
        for pattern, signal in cls.UNREALISTIC_REQ_PATTERNS:
            if signal is None:
                # Special handling for years-of-experience check
                for match in re.finditer(pattern, text_lower):
                    years_required = int(match.group(1))
                    tech = match.group(2).lower()
                    inception = cls.TECH_YEARS.get(tech)
                    if inception:
                        current_year = 2026
                        max_possible = current_year - inception
                        if years_required > max_possible:
                            flags.append(RedFlag(
                                category="unrealistic_requirements",
                                signal=f"Requires {years_required}+ years of {tech}, but it's only existed since {inception} ({max_possible} years)",
                                evidence=cls._extract_context(description_text, match),
                                severity="critical",
                            ))
                        elif years_required > max_possible - 2:
                            flags.append(RedFlag(
                                category="unrealistic_requirements",
                                signal=f"Requires {years_required}+ years of {tech} — near the technology's entire existence ({max_possible} years)",
                                evidence=cls._extract_context(description_text, match),
                                severity="warning",
                            ))
            else:
                match = re.search(pattern, text_lower)
                if match:
                    flags.append(RedFlag(
                        category="unrealistic_requirements",
                        signal=signal,
                        evidence=cls._extract_context(description_text, match),
                    ))

        # 3. Compensation red flags
        for pattern, signal in cls.COMPENSATION_RED_FLAGS:
            match = re.search(pattern, text_lower)
            if match:
                flags.append(RedFlag(
                    category="compensation_concern",
                    signal=signal,
                    evidence=cls._extract_context(description_text, match),
                ))

        # Check for missing salary entirely
        salary_patterns = [r"\$\s*[\d,]+", r"salary", r"compensation\s*(?:range|:)", r"pay\s*(?:range|:)"]
        has_salary = any(re.search(p, text_lower) for p in salary_patterns)
        if not has_salary:
            flags.append(RedFlag(
                category="compensation_concern",
                signal="No salary or compensation range mentioned",
                evidence="(not found in JD)",
                severity="warning",
            ))

        # 4. Turnover signals
        for pattern, signal in cls.TURNOVER_SIGNALS:
            match = re.search(pattern, text_lower)
            if match:
                flags.append(RedFlag(
                    category="turnover_signal",
                    signal=signal,
                    evidence=cls._extract_context(description_text, match),
                ))

        # 5. Vague role definition
        for pattern, signal in cls.VAGUE_ROLE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                flags.append(RedFlag(
                    category="vague_role",
                    signal=signal,
                    evidence=cls._extract_context(description_text, match),
                ))

        # 6. Excessive requirements count
        requirement_bullets = len(re.findall(r"(?:^|\n)\s*[-•*]\s+", description_text))
        must_have_count = len(re.findall(r"(?:must\s+have|required|mandatory|essential)", text_lower))
        if must_have_count > 15:
            flags.append(RedFlag(
                category="unrealistic_requirements",
                signal=f"Extremely high requirement count ({must_have_count} mandatory items) — likely a wish list, not a real requirement",
                evidence=f"{must_have_count} 'must have'/'required' mentions",
                severity="warning",
            ))

        return flags

    @classmethod
    def summarize(cls, flags: list[RedFlag]) -> dict[str, Any]:
        """Summarize red flags into a report."""
        if not flags:
            return {"total": 0, "critical": 0, "warnings": 0, "flags": [], "verdict": "clean"}

        critical = sum(1 for f in flags if f.severity == "critical")
        warnings = sum(1 for f in flags if f.severity == "warning")

        if critical >= 2:
            verdict = "avoid"
        elif critical >= 1 or warnings >= 4:
            verdict = "proceed_with_caution"
        elif warnings >= 2:
            verdict = "minor_concerns"
        else:
            verdict = "mostly_clean"

        return {
            "total": len(flags),
            "critical": critical,
            "warnings": warnings,
            "verdict": verdict,
            "flags": [f.to_dict() for f in flags],
        }

    @staticmethod
    def _extract_context(full_text: str, match: re.Match, window: int = 60) -> str:
        """Extract surrounding context around a regex match."""
        start = max(0, match.start() - window)
        end = min(len(full_text), match.end() + window)
        snippet = full_text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(full_text):
            snippet = snippet + "..."
        return snippet
