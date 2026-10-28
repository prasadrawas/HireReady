"""Similar Role Suggestions: detects titles you might be missing in your search preferences."""

import difflib
import logging
import re
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

# Common title variations grouped by role family
ROLE_FAMILIES = {
    "data_engineer": [
        "Data Engineer", "Senior Data Engineer", "Staff Data Engineer",
        "Data Platform Engineer", "Data Infrastructure Engineer",
        "Analytics Engineer", "ETL Engineer", "Pipeline Engineer",
        "Data Integration Engineer", "Big Data Engineer",
        "Cloud Data Engineer", "Streaming Data Engineer",
    ],
    "backend_engineer": [
        "Backend Engineer", "Software Engineer - Backend",
        "Server Engineer", "Platform Engineer",
        "API Engineer", "Systems Engineer",
        "Software Engineer", "Software Developer",
        "Senior Software Engineer", "Staff Software Engineer",
    ],
    "ml_engineer": [
        "Machine Learning Engineer", "ML Engineer", "MLOps Engineer",
        "AI Engineer", "Applied ML Engineer", "Deep Learning Engineer",
        "NLP Engineer", "Computer Vision Engineer",
        "ML Infrastructure Engineer", "ML Platform Engineer",
    ],
    "data_scientist": [
        "Data Scientist", "Senior Data Scientist",
        "Applied Scientist", "Research Scientist",
        "Quantitative Analyst", "Statistician",
        "Decision Scientist", "Product Data Scientist",
    ],
    "devops_sre": [
        "DevOps Engineer", "Site Reliability Engineer", "SRE",
        "Infrastructure Engineer", "Cloud Engineer",
        "Platform Engineer", "Reliability Engineer",
        "Production Engineer", "Systems Engineer",
    ],
    "frontend_engineer": [
        "Frontend Engineer", "Front-End Developer",
        "UI Engineer", "Web Developer",
        "JavaScript Engineer", "React Engineer",
        "Software Engineer - Frontend",
    ],
    "fullstack_engineer": [
        "Full Stack Engineer", "Fullstack Developer",
        "Software Engineer", "Web Engineer",
        "Product Engineer",
    ],
    "security_engineer": [
        "Security Engineer", "Application Security Engineer",
        "InfoSec Engineer", "Cybersecurity Engineer",
        "Cloud Security Engineer", "Security Analyst",
    ],
    "engineering_manager": [
        "Engineering Manager", "Software Engineering Manager",
        "Tech Lead Manager", "Director of Engineering",
        "VP of Engineering", "Head of Engineering",
    ],
}


class RoleSuggester:
    """Suggests additional role titles the user might want to search for."""

    @classmethod
    def suggest(cls, current_roles: list[str], seen_titles: list[str] | None = None) -> dict[str, Any]:
        """Analyze current target roles and suggest related titles.

        Args:
            current_roles: User's configured target_roles from preferences.yaml
            seen_titles: Titles from recent scan results that matched (optional)

        Returns:
            Dict with suggestions grouped by category
        """
        suggestions: list[dict] = []
        matched_families: set[str] = set()

        # Find which role families the user's current roles belong to
        for role in current_roles:
            role_lower = role.lower()
            for family_name, family_titles in ROLE_FAMILIES.items():
                for title in family_titles:
                    if cls._is_similar(role_lower, title.lower()):
                        matched_families.add(family_name)
                        break

        # For each matched family, find titles NOT in the user's current list
        current_lower = {r.lower() for r in current_roles}
        for family_name in matched_families:
            for title in ROLE_FAMILIES[family_name]:
                if not any(cls._is_similar(title.lower(), c) for c in current_lower):
                    suggestions.append({
                        "title": title,
                        "family": family_name.replace("_", " ").title(),
                        "reason": f"Related to your '{cls._closest_match(title, current_roles)}' target",
                    })

        # Analyze seen titles for patterns not in current targets
        scan_suggestions = []
        if seen_titles:
            title_counter = Counter()
            for t in seen_titles:
                # Extract the core role pattern (remove company-specific prefixes)
                core = re.sub(r"^(?:senior|staff|lead|principal|junior|sr\.?|jr\.?)\s+", "", t, flags=re.IGNORECASE).strip()
                title_counter[core] += 1

            for title_pattern, count in title_counter.most_common(10):
                if count >= 2 and not any(cls._is_similar(title_pattern.lower(), c) for c in current_lower):
                    scan_suggestions.append({
                        "title": title_pattern,
                        "seen_count": count,
                        "reason": f"Appeared {count} times in scan results but not in your target roles",
                    })

        return {
            "current_roles": current_roles,
            "matched_families": list(matched_families),
            "family_suggestions": suggestions[:15],  # cap suggestions
            "scan_suggestions": scan_suggestions[:10],
            "total_suggestions": len(suggestions) + len(scan_suggestions),
        }

    @staticmethod
    def _is_similar(a: str, b: str, threshold: float = 0.65) -> bool:
        """Check if two role titles are similar enough to be considered the same family."""
        if a in b or b in a:
            return True
        # Word overlap
        words_a = set(a.split())
        words_b = set(b.split())
        overlap = words_a & words_b
        if len(overlap) >= 2:
            return True
        # Fuzzy match
        return difflib.SequenceMatcher(None, a, b).ratio() >= threshold

    @staticmethod
    def _closest_match(title: str, current_roles: list[str]) -> str:
        """Find the closest matching role from current targets."""
        best_match = current_roles[0] if current_roles else title
        best_ratio = 0.0
        for role in current_roles:
            ratio = difflib.SequenceMatcher(None, title.lower(), role.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = role
        return best_match
