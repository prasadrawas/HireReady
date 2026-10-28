"""Salary intelligence: extract salary ranges from JD text and ATS compensation data."""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


class SalaryInfo:
    """Parsed salary information."""

    def __init__(
        self,
        min_salary: int | None = None,
        max_salary: int | None = None,
        currency: str = "USD",
        period: str = "year",
        source: str = "jd_text",
        raw_text: str = "",
    ):
        self.min_salary = min_salary
        self.max_salary = max_salary
        self.currency = currency
        self.period = period
        self.source = source
        self.raw_text = raw_text

    @property
    def display(self) -> str:
        """Human-readable salary string."""
        if not self.min_salary and not self.max_salary:
            return "Not listed"

        def fmt(n: int) -> str:
            if n >= 1000:
                return f"${n // 1000}K"
            return f"${n}"

        if self.min_salary and self.max_salary:
            return f"{fmt(self.min_salary)}-{fmt(self.max_salary)}"
        elif self.min_salary:
            return f"{fmt(self.min_salary)}+"
        elif self.max_salary:
            return f"Up to {fmt(self.max_salary)}"
        return "Not listed"

    def meets_minimum(self, minimum: int) -> bool:
        """Check if the salary range meets a minimum threshold."""
        if not self.min_salary and not self.max_salary:
            return True  # Unknown salary, don't filter out
        max_offered = self.max_salary or self.min_salary or 0
        return max_offered >= minimum

    def to_dict(self) -> dict:
        return {
            "min_salary": self.min_salary,
            "max_salary": self.max_salary,
            "currency": self.currency,
            "period": self.period,
            "source": self.source,
            "display": self.display,
            "raw_text": self.raw_text,
        }


class SalaryExtractor:
    """Extract salary information from job descriptions and ATS metadata."""

    # Patterns for common salary formats
    SALARY_PATTERNS = [
        # $150,000 - $200,000 / $150k - $200k
        r"\$\s*([\d,]+\.?\d*)\s*[kK]?\s*[-–—to]+\s*\$?\s*([\d,]+\.?\d*)\s*[kK]?",
        # $150,000+
        r"\$\s*([\d,]+\.?\d*)\s*[kK]?\s*\+",
        # Salary: 150000 - 200000
        r"(?:salary|compensation|pay|range)[:\s]*\$?\s*([\d,]+\.?\d*)\s*[kK]?\s*[-–—to]+\s*\$?\s*([\d,]+\.?\d*)\s*[kK]?",
        # USD 150,000 - 200,000
        r"(?:USD|GBP|EUR|CAD|AUD)\s*([\d,]+\.?\d*)\s*[kK]?\s*[-–—to]+\s*\$?\s*([\d,]+\.?\d*)\s*[kK]?",
    ]

    HOURLY_PATTERNS = [
        r"\$\s*([\d,]+\.?\d*)\s*[-–—to]+\s*\$?\s*([\d,]+\.?\d*)\s*(?:per\s*hour|/\s*hr|/\s*hour|hourly)",
        r"\$\s*([\d,]+\.?\d*)\s*(?:per\s*hour|/\s*hr|/\s*hour|hourly)",
    ]

    @classmethod
    def extract_from_text(cls, text: str) -> SalaryInfo:
        """Extract salary from JD text using regex patterns."""
        if not text:
            return SalaryInfo()

        text_lower = text.lower()

        # Check for hourly rates first
        for pattern in cls.HOURLY_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                groups = match.groups()
                min_val = cls._parse_number(groups[0])
                max_val = cls._parse_number(groups[1]) if len(groups) > 1 else None
                return SalaryInfo(
                    min_salary=min_val,
                    max_salary=max_val,
                    period="hour",
                    source="jd_text",
                    raw_text=match.group(0),
                )

        # Check annual salary patterns
        for pattern in cls.SALARY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                min_val = cls._parse_number(groups[0])
                max_val = cls._parse_number(groups[1]) if len(groups) > 1 else None

                # Handle "k" suffix
                raw = match.group(0).lower()
                if "k" in raw:
                    if min_val and min_val < 1000:
                        min_val *= 1000
                    if max_val and max_val < 1000:
                        max_val *= 1000

                # Sanity check: annual salary should be > $10,000
                if min_val and min_val < 10000:
                    continue
                if max_val and max_val < 10000:
                    continue

                return SalaryInfo(
                    min_salary=min_val,
                    max_salary=max_val,
                    period="year",
                    source="jd_text",
                    raw_text=match.group(0),
                )

        return SalaryInfo()

    @classmethod
    def extract_from_metadata(cls, metadata: dict) -> SalaryInfo:
        """Extract salary from ATS-provided compensation metadata."""
        if not metadata:
            return SalaryInfo()

        # Rippling payRangeDetails (list of dicts) or generic salary_raw list
        pay_ranges = metadata.get("payRangeDetails") or metadata.get("salary_raw")
        if isinstance(pay_ranges, list) and pay_ranges:
            first_range = pay_ranges[0]
            if isinstance(first_range, dict):
                min_val = first_range.get("rangeStart") or first_range.get("min")
                max_val = first_range.get("rangeEnd") or first_range.get("max")
                curr = first_range.get("currency", "USD")
                freq = (first_range.get("frequency") or "year").lower()
                period = "year" if "year" in freq else "hour" if "hour" in freq else "month" if "month" in freq else "year"
                if min_val or max_val:
                    return SalaryInfo(
                        min_salary=int(min_val) if min_val else None,
                        max_salary=int(max_val) if max_val else None,
                        currency=curr,
                        period=period,
                        source="ats_metadata",
                    )

        # Ashby / structured compensation data
        compensation = metadata.get("compensation") or metadata.get("salary") or {}
        if isinstance(compensation, dict):
            # Try Ashby compensation tiers
            tiers = compensation.get("compensationTiers", [])
            for tier in tiers:
                for comp_item in tier.get("components", []):
                    if comp_item.get("compensationType") == "Salary":
                        min_val = comp_item.get("minValue")
                        max_val = comp_item.get("maxValue")
                        curr = comp_item.get("currencyCode", "USD")
                        interval = comp_item.get("interval", "1 YEAR")
                        period = "year" if "year" in str(interval).lower() else "hour" if "hour" in str(interval).lower() else "year"
                        if min_val or max_val:
                            return SalaryInfo(
                                min_salary=int(min_val) if min_val else None,
                                max_salary=int(max_val) if max_val else None,
                                currency=curr,
                                period=period,
                                source="ats_metadata",
                            )

            summary = compensation.get("scrapeableCompensationSalarySummary")
            if summary:
                parsed = cls.extract_from_text(summary)
                if parsed.min_salary or parsed.max_salary:
                    parsed.source = "ats_metadata"
                    return parsed

            min_val = compensation.get("min") or compensation.get("rangeStart") or compensation.get("minimum")
            max_val = compensation.get("max") or compensation.get("rangeEnd") or compensation.get("maximum")
            currency = compensation.get("currency", "USD")
            period = compensation.get("period") or compensation.get("frequency", "year")

            if min_val or max_val:
                return SalaryInfo(
                    min_salary=int(min_val) if min_val else None,
                    max_salary=int(max_val) if max_val else None,
                    currency=currency,
                    period=period,
                    source="ats_metadata",
                )

        # Recruitee salary object
        salary_obj = metadata.get("salary")
        if isinstance(salary_obj, dict) and (salary_obj.get("min") or salary_obj.get("max")):
            return SalaryInfo(
                min_salary=int(salary_obj["min"]) if salary_obj.get("min") else None,
                max_salary=int(salary_obj["max"]) if salary_obj.get("max") else None,
                currency=salary_obj.get("currency", "USD"),
                period=salary_obj.get("period", "year"),
                source="ats_metadata",
            )

        # Pinpoint compensation fields
        comp_min = metadata.get("compensation_minimum")
        comp_max = metadata.get("compensation_maximum")
        if comp_min or comp_max:
            return SalaryInfo(
                min_salary=int(comp_min) if comp_min else None,
                max_salary=int(comp_max) if comp_max else None,
                currency=metadata.get("compensation_currency", "USD"),
                period=metadata.get("compensation_frequency", "year"),
                source="ats_metadata",
            )

        return SalaryInfo()

    @classmethod
    def extract(cls, description_text: str, metadata: dict | None = None) -> SalaryInfo:
        """Extract salary from all available sources, preferring structured data."""
        # Try structured metadata first (more reliable)
        if metadata:
            meta_salary = cls.extract_from_metadata(metadata)
            if meta_salary.min_salary or meta_salary.max_salary:
                return meta_salary

        # Fall back to text extraction
        return cls.extract_from_text(description_text)

    @staticmethod
    def _parse_number(s: str) -> int | None:
        """Parse a number string, handling commas and decimals."""
        if not s:
            return None
        try:
            cleaned = s.replace(",", "").strip()
            return int(float(cleaned))
        except (ValueError, TypeError):
            return None
