"""Resume tailoring and application asset generation orchestrator."""

import json
import logging
from pathlib import Path
from typing import Any

from config.settings import settings
from src.ats_validator import ATSValidator
from src.company_research import CompanyResearcher
from src.cover_letter_generator import CoverLetterGenerator
from src.html_generator import HTMLGenerator
from src.linkedin_detector import LinkedInDetector
from src.models.job_listing import JobListing
from src.models.resume import ResumeData
from src.pdf_generator import PDFGenerator
from src.red_flag_detector import RedFlagDetector
from src.resume_matcher import ResumeMatcher
from src.resume_tailor import ResumeTailor
from src.salary_extractor import SalaryExtractor
from src.tracker import ApplicationTracker

logger = logging.getLogger(__name__)


class TailoringService:
    """Orchestrates end-to-end tailoring: JD analysis, resume customization, PDF generation, and validation."""

    def __init__(self, tracker: ApplicationTracker | None = None):
        self.tracker = tracker or ApplicationTracker()

    def tailor(
        self,
        job: JobListing,
        resume: ResumeData,
        generate_cover_letter: bool = False,
    ) -> Path:
        """Execute full tailoring pipeline for a job and return the output directory path."""
        output_folder = settings.output_dir / job.id
        output_folder.mkdir(parents=True, exist_ok=True)

        tailor = ResumeTailor()
        html_gen = HTMLGenerator()
        pdf_gen = PDFGenerator()
        matcher = ResumeMatcher()
        validator = ATSValidator(pdf_generator=pdf_gen)

        # 1. Combined JD Analysis + Resume Tailoring
        jd_analysis, tailored = tailor.analyze_and_tailor(
            resume=resume,
            job_description=job.description_text or job.description_html,
            job_id=job.id,
            company=job.company,
            job_title=job.title,
            application_url=job.application_url,
            output_dir=output_folder,
        )

        # 2. Match report
        match_report = matcher.match(jd_analysis, resume, output_dir=output_folder)

        # 3. HTML generation
        html_file = output_folder / "resume.html"
        html_gen.generate(tailored, target_role=job.title, output_path=html_file)

        # 4. PDF generation
        pdf_file = output_folder / "resume.pdf"
        pdf_gen.generate_pdf(html_path=html_file, pdf_path=pdf_file)

        # 5. ATS Validation
        val_report = validator.validate(
            pdf_path=pdf_file,
            html_path=html_file,
            tailored_resume=tailored,
            master_resume=resume,
            jd_analysis=jd_analysis,
            output_dir=output_folder,
        )

        # 6. Red flags scan
        red_flags = RedFlagDetector.scan(job.description_text, job.title)
        flag_summary = RedFlagDetector.summarize(red_flags)
        (output_folder / "red_flags.json").write_text(json.dumps(flag_summary, indent=2), encoding="utf-8")

        # 7. Company research
        company_researcher = CompanyResearcher()
        company_researcher.research(job.company, job.title, job.description_text, output_dir=output_folder)

        # 8. Cover letter (opt-in)
        if generate_cover_letter:
            cover_letter_gen = CoverLetterGenerator()
            cover_letter_gen.generate(
                resume=resume,
                jd_analysis=jd_analysis,
                match_report=match_report,
                output_dir=output_folder,
            )

        # 9. Salary + LinkedIn info
        salary = SalaryExtractor.extract(job.description_text, job.metadata)
        linkedin_info = LinkedInDetector.get_linkedin_info(job.company, job.title, job.description_text)

        (output_folder / "salary_info.json").write_text(json.dumps(salary.to_dict(), indent=2), encoding="utf-8")

        url_lines = [
            f"ATS Apply: {job.application_url.strip()}",
            f"LinkedIn Easy Apply: {linkedin_info['linkedin_easy_apply_search']}",
            f"LinkedIn Search: {linkedin_info['linkedin_job_search']}",
        ]
        if linkedin_info.get("linkedin_direct_url"):
            url_lines.append(f"LinkedIn Direct: {linkedin_info['linkedin_direct_url']}")
        (output_folder / "application_url.txt").write_text("\n".join(url_lines) + "\n", encoding="utf-8")

        # 10. Record in tracker
        self.tracker.record_application(
            job_id=job.id,
            company=job.company,
            title=job.title,
            application_url=job.application_url,
            output_dir=str(output_folder),
            coverage_score=match_report.coverage_score,
            validation_passed=val_report.passed,
            needs_review_count=len(tailored.needs_review),
            status="ready_for_review" if val_report.passed else "validation_failed",
            salary=salary.display,
            linkedin_url=linkedin_info["linkedin_easy_apply_search"],
        )

        return output_folder
