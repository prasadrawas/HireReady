"""Automated ATS job application runner using Playwright."""

import logging
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from config.settings import settings
from src.api.service import APIService
from src.auto_apply.form_filler import FormFiller
from src.auto_apply.profile import ApplicantProfile, load_applicant_profile
from src.auto_apply.question_solver import QuestionSolver
from src.auto_apply.supervisor import ReviewSupervisor
from src.models.job_listing import JobListing
from src.tracker import ApplicationTracker

logger = logging.getLogger(__name__)


class AutoApplyRunner:
    """Coordinates automated job application execution across ATS platforms."""

    def __init__(
        self,
        profile: ApplicantProfile | None = None,
        service: APIService | None = None,
        tracker: ApplicationTracker | None = None,
        form_filler: FormFiller | None = None,
        supervisor: ReviewSupervisor | None = None,
    ):
        self.profile = profile or load_applicant_profile()
        self.service = service or APIService()
        self.tracker = tracker or ApplicationTracker()
        self.form_filler = form_filler or FormFiller()
        self.supervisor = supervisor or ReviewSupervisor()

    def apply(
        self,
        job_id: str,
        headed: bool = True,
        auto_submit: bool = False,
        review_timeout_sec: int = 15,
    ) -> dict[str, Any]:
        """Apply to a job using Playwright.

        Args:
            job_id: ID of the job listing.
            headed: If True, launches visible browser for user supervision.
            auto_submit: If True, submits automatically. If False, pauses for review.
            review_timeout_sec: Seconds to wait for user to review/submit in supervised mode.

        Returns:
            Dictionary with application execution status, fields filled, and custom answers.
        """
        # 1. Fetch job listing metadata
        jobs_data = self.service.get_jobs()
        job_dict = next((j for j in jobs_data.get("jobs", []) if j["id"] == job_id), None)
        if not job_dict:
            raise ValueError(f"Job {job_id} not found in scan results.")

        job = JobListing.model_validate(job_dict)
        app_url = job.application_url or ""
        if not app_url:
            raise ValueError(f"Job {job_id} has no application URL.")

        # 2. Ensure tailored resume PDF and cover letter exist
        pdf_path, cover_letter_text = self._prepare_assets(job_id)

        # 3. Setup question solver
        solver = self._init_question_solver(job)

        fields_filled: list[str] = []
        questions_answered: list[dict[str, str]] = []
        submission_status = "prepared"
        message = ""

        # 4. Launch Playwright browser session
        logger.info("Launching Playwright (headed=%s) for %s at %s", headed, job.company, app_url)
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=not headed,
                slow_mo=80 if headed else 0,
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            try:
                page.goto(app_url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2000)

                # Check if we need to click "Apply" on landing page
                self.form_filler.navigate_to_form(page)

                # Fill standard personal contact info
                filled_contact = self.form_filler.fill_contact_info(page, self.profile)
                fields_filled.extend(filled_contact)

                # Upload tailored resume PDF
                if pdf_path.exists():
                    uploaded = self.form_filler.upload_resume(page, pdf_path)
                    if uploaded:
                        fields_filled.append("resume_pdf")

                # Fill cover letter if text available
                if cover_letter_text:
                    cl_filled = self.form_filler.fill_cover_letter(page, cover_letter_text)
                    if cl_filled:
                        fields_filled.append("cover_letter")

                # Fill custom questions (work authorization, EEOC, essays, selects)
                answered = self.form_filler.fill_custom_questions(page, solver)
                questions_answered.extend(answered)

                # Scroll submit button into view
                submit_button = self.supervisor.find_submit_button(page)
                if submit_button:
                    try:
                        submit_button.scroll_into_view_if_needed()
                    except Exception:
                        pass

                # Supervised review or auto-submit
                submission_status, message = self.supervisor.supervise(
                    page=page,
                    submit_button=submit_button,
                    auto_submit=auto_submit,
                    review_timeout_sec=review_timeout_sec,
                    company_name=job.company,
                    headed=headed,
                )

            except Exception as e:
                logger.error("Error during auto-apply execution: %s", e)
                submission_status = "error"
                message = f"Auto-apply error: {str(e)}"
            finally:
                try:
                    browser.close()
                except Exception:
                    pass

        # 5. Update Application Tracker
        tracker_status = "submitted" if submission_status == "submitted" else "ready_for_review"
        self.tracker.record_application(
            job_id=job.id,
            company=job.company,
            title=job.title,
            application_url=job.application_url,
            status=tracker_status,
        )

        return {
            "success": submission_status in ["submitted", "ready_for_review"],
            "job_id": job.id,
            "company": job.company,
            "title": job.title,
            "status": submission_status,
            "message": message,
            "fields_filled": fields_filled,
            "questions_answered": questions_answered,
        }

    def _prepare_assets(self, job_id: str) -> tuple[Path, str]:
        """Ensure tailored PDF and cover letter exist for the job."""
        pdf_path = settings.output_dir / job_id / "resume.pdf"
        cover_letter_path = settings.output_dir / job_id / "cover_letter.txt"

        if not pdf_path.exists():
            logger.info("Tailored PDF not found for %s. Generating on the fly...", job_id)
            try:
                self.service.tailor_job(job_id, generate_cover_letter=True)
            except Exception as e:
                logger.warning("Could not auto-tailor resume for %s: %s. Using master fallback.", job_id, e)
                pdf_path = settings.input_dir / "master_resume.pdf"

        if not pdf_path.exists() and (settings.input_dir / "master_resume.pdf").exists():
            pdf_path = settings.input_dir / "master_resume.pdf"

        cover_letter_text = ""
        if cover_letter_path.exists():
            cover_letter_text = cover_letter_path.read_text(encoding="utf-8").strip()

        return pdf_path, cover_letter_text

    def _init_question_solver(self, job: JobListing) -> QuestionSolver:
        """Initialize the QuestionSolver with candidate and job context."""
        resume = None
        try:
            resume = self.service.get_resume()
        except Exception as e:
            logger.debug("Could not load resume data for question solver: %s", e)

        return QuestionSolver(
            profile=self.profile,
            resume=resume,
            job_title=job.title,
            company=job.company,
            job_description=job.description_text or job.description_html or "",
        )
