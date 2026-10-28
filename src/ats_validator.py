"""ATS validation module: PyMuPDF-based text, structure, keyword, and integrity verification."""

import difflib
import json
import logging
from pathlib import Path
import re
from typing import Any
import pymupdf

from config.settings import settings
from src.jd_parser import JDParser
from src.models.jd import JDAnalysis
from src.models.resume import ResumeData
from src.models.tailored import TailoredResume
from src.models.validation import CheckResult, ValidationReport
from src.pdf_generator import PDFGenerator

logger = logging.getLogger(__name__)


class ATSValidator:
    """Validates generated PDF against ATS criteria, keyword coverage, and evidence integrity."""

    def __init__(self, pdf_generator: PDFGenerator | None = None):
        self.pdf_generator = pdf_generator or PDFGenerator()

    def validate(
        self,
        pdf_path: str | Path,
        html_path: str | Path,
        tailored_resume: TailoredResume,
        master_resume: ResumeData,
        jd_analysis: JDAnalysis,
        output_dir: Path | None = None,
        auto_fix: bool = True,
    ) -> ValidationReport:
        """Run all ATS validation checks, attempting automated CSS/margin fix on failure."""
        pdf_p = Path(pdf_path)
        html_p = Path(html_path)

        report = self._run_all_checks(pdf_p, html_p, tailored_resume, master_resume, jd_analysis)

        # Automated fix attempt if page count exceeded or formatting failed
        if not report.passed and auto_fix:
            page_count_failed = any(not c.passed and c.check == "page_count" for c in report.checks)
            if page_count_failed and report.page_count > settings.max_resume_pages:
                logger.info("Attempting automated fix for PDF overflow (reducing margins)...")
                try:
                    fix_generator = PDFGenerator(
                        margin_top="10mm",
                        margin_bottom="10mm",
                        margin_left="10mm",
                        margin_right="10mm",
                    )
                    fix_generator.generate_pdf(html_path=html_p, pdf_path=pdf_p)
                    # Re-run validation
                    report = self._run_all_checks(
                        pdf_p, html_p, tailored_resume, master_resume, jd_analysis
                    )
                except Exception as e:
                    logger.warning("Automated fix failed: %s", e)

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_file = output_dir / "validation_report.json"
            out_file.write_text(json.dumps(report.model_dump(), indent=2, default=str), encoding="utf-8")

        return report

    def _run_all_checks(
        self,
        pdf_path: Path,
        html_path: Path,
        tailored: TailoredResume,
        master: ResumeData,
        jd_analysis: JDAnalysis,
    ) -> ValidationReport:
        """Run each individual ATS check."""
        checks: list[CheckResult] = []
        warnings: list[str] = []
        kw_verification: dict[str, bool] = {}
        unsupported_claims: list[str] = list(tailored.needs_review)

        # 1. pdf_opens
        doc = None
        pdf_opens = False
        try:
            doc = pymupdf.open(str(pdf_path))
            pdf_opens = True
            checks.append(CheckResult(check="pdf_opens", passed=True))
        except Exception as e:
            checks.append(CheckResult(check="pdf_opens", passed=False, detail=str(e)))
            return ValidationReport(
                job_id=tailored.job_id,
                application_url=tailored.application_url,
                checks=checks,
                keyword_verification={},
                page_count=0,
                unsupported_claims=unsupported_claims,
                warnings=[f"Could not open PDF: {e}"],
                passed=False,
            )

        extracted_text = ""
        page_count = len(doc)
        try:
            extracted_text = "\n".join(page.get_text() for page in doc)
        finally:
            doc.close()

        # 2. text_extractable
        has_text = len(extracted_text.strip()) >= 150
        checks.append(
            CheckResult(
                check="text_extractable",
                passed=has_text,
                detail=f"Extracted {len(extracted_text.strip())} chars",
            )
        )

        # 3. section_headings_intact
        text_lower = extracted_text.lower()
        required_headings = ["summary", "skills", "experience", "education"]
        missing_headings = [h for h in required_headings if h not in text_lower]
        headings_pass = len(missing_headings) == 0
        checks.append(
            CheckResult(
                check="section_headings_intact",
                passed=headings_pass,
                detail=f"Missing: {', '.join(missing_headings)}" if missing_headings else "All headings found",
            )
        )

        # 4. contact_info_present
        missing_contact = []
        if tailored.contact.name.lower() not in text_lower:
            missing_contact.append("name")
        if tailored.contact.email.lower() not in text_lower:
            missing_contact.append("email")
        if tailored.contact.phone and tailored.contact.phone != "N/A":
            clean_phone = re.sub(r"\D", "", tailored.contact.phone)
            clean_text = re.sub(r"\D", "", extracted_text)
            if clean_phone and clean_phone not in clean_text:
                missing_contact.append("phone")
        if tailored.contact.linkedin and "linkedin" not in text_lower:
            missing_contact.append("linkedin")

        contact_pass = len(missing_contact) == 0
        checks.append(
            CheckResult(
                check="contact_info_present",
                passed=contact_pass,
                detail=f"Missing contact items: {', '.join(missing_contact)}" if missing_contact else "Contact info verified",
            )
        )

        # 5. keyword_verification
        critical_keywords = [k for k in jd_analysis.keywords if k.category == "critical"]
        for kw in critical_keywords:
            term_clean = kw.term.lower().strip()
            present = term_clean in text_lower
            kw_verification[kw.term] = present

        kw_pass = True
        if critical_keywords:
            missing_crit = [term for term, present in kw_verification.items() if not present]
            if len(missing_crit) > max(1, len(critical_keywords) // 4):
                kw_pass = False
            if missing_crit:
                warnings.append(f"Critical keywords not found in PDF text: {', '.join(missing_crit)}")

        checks.append(
            CheckResult(
                check="keyword_verification",
                passed=kw_pass,
                detail=f"{sum(1 for v in kw_verification.values() if v)}/{len(kw_verification)} critical keywords verified",
            )
        )

        # 6. no_unsupported_claims
        claims_pass = len(unsupported_claims) == 0
        checks.append(
            CheckResult(
                check="no_unsupported_claims",
                passed=claims_pass,
                detail=f"{len(unsupported_claims)} flagged unlinked claims" if not claims_pass else "All claims linked to master",
            )
        )

        # 7. page_count
        pages_pass = 1 <= page_count <= settings.max_resume_pages
        checks.append(
            CheckResult(
                check="page_count",
                passed=pages_pass,
                detail=f"PDF has {page_count} page(s) (limit: {settings.max_resume_pages})",
            )
        )

        # 8. no_garbled_text
        has_mojibake = "\ufffd" in extracted_text or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", extracted_text) is not None
        checks.append(
            CheckResult(
                check="no_garbled_text",
                passed=not bool(has_mojibake),
                detail="No garbled encoding detected" if not has_mojibake else "Garbled characters or control codes found",
            )
        )

        # 9. html_pdf_consistency
        html_text = ""
        if html_path.exists():
            html_text = JDParser.clean_html(html_path.read_text(encoding="utf-8"))

        consistency_pass = True
        if html_text:
            ratio = difflib.SequenceMatcher(None, html_text[:2000].lower(), extracted_text[:2000].lower()).ratio()
            consistency_pass = ratio >= 0.70
            checks.append(
                CheckResult(
                    check="html_pdf_consistency",
                    passed=consistency_pass,
                    detail=f"Text similarity score: {round(ratio, 2)}",
                )
            )
        else:
            checks.append(CheckResult(check="html_pdf_consistency", passed=True, detail="HTML file skipped"))

        overall_passed = all(c.passed for c in checks)

        return ValidationReport(
            job_id=tailored.job_id,
            application_url=tailored.application_url,
            checks=checks,
            keyword_verification=kw_verification,
            page_count=page_count,
            unsupported_claims=unsupported_claims,
            warnings=warnings,
            passed=overall_passed,
        )
