"""Automated ATS job application runner using Playwright."""

import logging
import re
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

from config.settings import settings
from src.api.service import APIService
from src.auto_apply.profile import ApplicantProfile, load_applicant_profile
from src.auto_apply.question_solver import QuestionSolver
from src.models.job_listing import JobListing
from src.tracker import ApplicationTracker

logger = logging.getLogger(__name__)


class AutoApplyRunner:
    """Executes supervised or automated job applications via Playwright."""

    def __init__(
        self,
        profile: ApplicantProfile | None = None,
        service: APIService | None = None,
        tracker: ApplicationTracker | None = None,
    ):
        self.profile = profile or load_applicant_profile()
        self.service = service or APIService()
        self.tracker = tracker or ApplicationTracker()

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
        pdf_path = settings.output_dir / job_id / "resume.pdf"
        cover_letter_path = settings.output_dir / job_id / "cover_letter.txt"

        if not pdf_path.exists():
            logger.info("Tailored PDF not found for %s. Generating on the fly...", job_id)
            try:
                self.service.tailor_job(job_id, generate_cover_letter=True)
            except Exception as e:
                logger.warning("Could not auto-tailor resume for %s: %s. Using master PDF fallback.", job_id, e)
                pdf_path = settings.input_dir / "master_resume.pdf"

        # If still no PDF, try master_resume.pdf
        if not pdf_path.exists() and (settings.input_dir / "master_resume.pdf").exists():
            pdf_path = settings.input_dir / "master_resume.pdf"

        cover_letter_text = ""
        if cover_letter_path.exists():
            cover_letter_text = cover_letter_path.read_text(encoding="utf-8").strip()

        # 3. Setup question solver
        resume = None
        try:
            resume = self.service.get_resume()
        except Exception as e:
            logger.debug("Could not load resume data for question solver: %s", e)

        solver = QuestionSolver(
            profile=self.profile,
            resume=resume,
            job_title=job.title,
            company=job.company,
            job_description=job.description_text or job.description_html or "",
        )

        fields_filled: list[str] = []
        questions_answered: list[dict[str, str]] = []
        submission_status = "prepared"
        message = ""

        # 4. Launch Playwright
        logger.info("Launching Playwright (headed=%s) for %s at %s", headed, job.company, app_url)
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=not headed,
                slow_mo=80 if headed else 0,
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            try:
                page.goto(app_url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2000)

                # Check if we need to click an "Apply" button to open the application form
                self._navigate_to_form(page)

                # Fill standard personal contact info
                filled_contact = self._fill_contact_info(page, self.profile)
                fields_filled.extend(filled_contact)

                # Upload resume and handle cover letter
                if pdf_path.exists():
                    uploaded = self._upload_resume(page, pdf_path)
                    if uploaded:
                        fields_filled.append("resume_pdf")

                if cover_letter_text:
                    cl_filled = self._fill_cover_letter(page, cover_letter_text)
                    if cl_filled:
                        fields_filled.append("cover_letter")

                # Fill custom questions (work authorization, EEOC, essays, selects)
                answered = self._fill_custom_questions(page, solver)
                questions_answered.extend(answered)

                # Scroll submit button into view
                submit_button = self._find_submit_button(page)
                if submit_button:
                    try:
                        submit_button.scroll_into_view_if_needed()
                    except Exception:
                        pass

                # Supervised review or auto-submit
                if auto_submit:
                    if submit_button:
                        logger.info("Auto-submitting application for %s...", job.company)
                        submit_button.click()
                        page.wait_for_timeout(4000)
                        submission_status = "submitted"
                        message = f"Application for {job.company} submitted successfully!"
                    else:
                        submission_status = "filled_needs_click"
                        message = f"Form filled, but submit button could not be safely clicked automatically."
                else:
                    submission_status = "ready_for_review"
                    message = f"Form successfully filled for {job.company}. Supervised review window active."

                    # In headed mode, wait for candidate review / captcha or manual submit click
                    if headed and review_timeout_sec > 0:
                        start_time = time.time()
                        initial_url = page.url
                        while time.time() - start_time < review_timeout_sec:
                            page.wait_for_timeout(500)
                            # Detect manual submit: url change or success indicators
                            if page.url != initial_url:
                                submission_status = "submitted"
                                message = f"Application for {job.company} was submitted by user!"
                                break
                            if self._detect_submission_success(page):
                                submission_status = "submitted"
                                message = f"Application for {job.company} detected as successfully submitted!"
                                break

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

    def _navigate_to_form(self, page: Page) -> None:
        """Check if an 'Apply' or 'Apply for this job' button exists on landing page and click it."""
        try:
            # Check if form is already present
            if page.locator("input[type='email'], input#email, input[name='email']").count() > 0:
                return

            apply_selectors = [
                "a:has-text('Apply for this job')",
                "button:has-text('Apply for this job')",
                "a:has-text('Apply Now')",
                "button:has-text('Apply Now')",
                "a[data-qa='apply-button']",
                "button[data-qa='apply-button']",
                "a.postings-btn",
                "button.postings-btn",
            ]

            for sel in apply_selectors:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=800):
                    loc.click()
                    page.wait_for_timeout(1500)
                    break
        except Exception as e:
            logger.debug("Navigate to form non-blocking check: %s", e)

    def _fill_contact_info(self, page: Page, profile: ApplicantProfile) -> list[str]:
        """Fill candidate contact information."""
        c = profile.contact
        filled = []

        field_mappings = [
            # First Name
            (
                "first_name",
                c.first_name,
                [
                    "input[name='first_name' i]",
                    "input#first_name",
                    "input[id*='firstName' i]",
                    "input[name*='firstName' i]",
                    "input[data-qa='first-name']",
                    "input[aria-label*='first name' i]",
                    "input[placeholder*='first name' i]",
                ],
            ),
            # Last Name
            (
                "last_name",
                c.last_name,
                [
                    "input[name='last_name' i]",
                    "input#last_name",
                    "input[id*='lastName' i]",
                    "input[name*='lastName' i]",
                    "input[data-qa='last-name']",
                    "input[aria-label*='last name' i]",
                    "input[placeholder*='last name' i]",
                ],
            ),
            # Full Name (fallback if no first/last name field found)
            (
                "full_name",
                c.full_name,
                [
                    "input[name='name' i]",
                    "input#name",
                    "input[id*='full_name' i]",
                    "input[id*='fullName' i]",
                    "input[placeholder*='full name' i]",
                ],
            ),
            # Email
            (
                "email",
                c.email,
                [
                    "input[type='email']",
                    "input[name*='email' i]",
                    "input#email",
                    "input[placeholder*='email' i]",
                    "input[aria-label*='email' i]",
                ],
            ),
            # Phone
            (
                "phone",
                c.phone,
                [
                    "input[type='tel']",
                    "input[name*='phone' i]",
                    "input#phone",
                    "input[placeholder*='phone' i]",
                    "input[aria-label*='phone' i]",
                ],
            ),
            # Location
            (
                "location",
                c.location,
                [
                    "input[name*='location' i]",
                    "input#location",
                    "input[placeholder*='location' i]",
                    "input[placeholder*='city' i]",
                    "input[aria-label*='location' i]",
                ],
            ),
            # Current Company
            (
                "current_company",
                c.current_company,
                [
                    "input[name='org' i]",
                    "input[name*='company' i]",
                    "input#org",
                    "input#company",
                    "input[placeholder*='current company' i]",
                ],
            ),
            # LinkedIn
            (
                "linkedin",
                c.linkedin,
                [
                    "input[name*='urls[LinkedIn]' i]",
                    "input[name*='linkedin' i]",
                    "input[id*='linkedin' i]",
                    "input[placeholder*='linkedin' i]",
                ],
            ),
            # GitHub
            (
                "github",
                c.github,
                [
                    "input[name*='urls[GitHub]' i]",
                    "input[name*='github' i]",
                    "input[id*='github' i]",
                    "input[placeholder*='github' i]",
                ],
            ),
            # Website / Portfolio
            (
                "website",
                c.website,
                [
                    "input[name*='urls[Portfolio]' i]",
                    "input[name*='urls[Other]' i]",
                    "input[name*='website' i]",
                    "input[name*='portfolio' i]",
                    "input[id*='website' i]",
                    "input[id*='portfolio' i]",
                    "input[placeholder*='website' i]",
                    "input[placeholder*='portfolio' i]",
                ],
            ),
        ]

        for field_name, value, selectors in field_mappings:
            if not value:
                continue

            # If first and last name were already filled, skip full_name
            if field_name == "full_name" and ("first_name" in filled or "last_name" in filled):
                continue

            for sel in selectors:
                try:
                    loc = page.locator(sel).first
                    if loc.is_visible(timeout=300):
                        current_val = loc.input_value()
                        if not current_val:
                            loc.fill(value)
                            filled.append(field_name)
                            break
                except Exception:
                    continue

        return filled

    def _upload_resume(self, page: Page, pdf_path: Path) -> bool:
        """Find the resume file input and upload the tailored PDF."""
        file_inputs = page.locator("input[type='file']")
        count = file_inputs.count()
        if count == 0:
            return False

        # Try specific resume input first
        resume_selectors = [
            "input[type='file'][name*='resume' i]",
            "input[type='file'][id*='resume' i]",
            "input[type='file'][data-qa*='resume' i]",
            "input#resume-upload-input",
        ]
        for sel in resume_selectors:
            loc = page.locator(sel).first
            if loc.count() > 0:
                try:
                    loc.set_input_files(str(pdf_path))
                    return True
                except Exception as e:
                    logger.debug("Failed setting file on selector %s: %s", sel, e)

        # Fallback to the first file input
        try:
            file_inputs.first.set_input_files(str(pdf_path))
            return True
        except Exception as e:
            logger.debug("Failed setting file on first input[type='file']: %s", e)
            return False

    def _fill_cover_letter(self, page: Page, text: str) -> bool:
        """Fill cover letter textarea if present."""
        cl_selectors = [
            "textarea[name*='comments' i]",
            "textarea[name*='cover' i]",
            "textarea[id*='cover' i]",
            "textarea[placeholder*='cover letter' i]",
            "textarea[aria-label*='cover letter' i]",
        ]
        for sel in cl_selectors:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=300):
                    loc.fill(text)
                    return True
            except Exception:
                continue
        return False

    def _fill_custom_questions(self, page: Page, solver: QuestionSolver) -> list[dict[str, str]]:
        """Inspect and answer custom form questions (selects, textareas, un-filled text inputs, radios)."""
        answered: list[dict[str, str]] = []

        # 1. Process Select / Dropdowns
        selects = page.locator("select")
        select_count = selects.count()
        for i in range(select_count):
            try:
                sel = selects.nth(i)
                if not sel.is_visible(timeout=200):
                    continue

                prompt = self._extract_label_text(page, sel)
                if not prompt:
                    continue

                # Get options
                option_locators = sel.locator("option")
                opt_texts = [opt.inner_text().strip() for opt in option_locators.all()]
                res = solver.solve(prompt, options=opt_texts)

                if res.selected_option:
                    sel.select_option(label=res.selected_option)
                    answered.append({
                        "question": prompt[:80],
                        "answer": res.selected_option,
                        "type": "select",
                    })
            except Exception as e:
                logger.debug("Select question processing error: %s", e)

        # 2. Process Textareas (Essay / open-ended questions)
        textareas = page.locator("textarea")
        ta_count = textareas.count()
        for i in range(ta_count):
            try:
                ta = textareas.nth(i)
                if not ta.is_visible(timeout=200):
                    continue
                # Skip if already filled (e.g. cover letter)
                if ta.input_value().strip():
                    continue

                prompt = self._extract_label_text(page, ta)
                if not prompt:
                    continue

                res = solver.solve(prompt, is_textarea=True)
                ta.fill(res.answer)
                answered.append({
                    "question": prompt[:80],
                    "answer": res.answer[:100] + "..." if len(res.answer) > 100 else res.answer,
                    "type": "textarea",
                })
            except Exception as e:
                logger.debug("Textarea question processing error: %s", e)

        # 3. Process Radio Groups
        try:
            radios = page.locator("input[type='radio']")
            radio_names = set()
            for r in radios.all():
                name = r.get_attribute("name")
                if name:
                    radio_names.add(name)

            for rname in radio_names:
                group = page.locator(f"input[type='radio'][name='{rname}']")
                # Check if any in group is already checked
                checked = False
                for r in group.all():
                    if r.is_checked():
                        checked = True
                        break
                if checked:
                    continue

                # Find prompt and options for this radio group
                first_r = group.first
                prompt = self._extract_group_prompt(page, first_r)
                if not prompt:
                    continue

                # Gather option labels for each radio
                opt_labels = []
                r_list = group.all()
                for r in r_list:
                    lbl = self._extract_radio_label(page, r)
                    opt_labels.append(lbl)

                res = solver.solve(prompt, options=opt_labels)
                if res.selected_option:
                    # Click the matching radio
                    for idx, lbl in enumerate(opt_labels):
                        if lbl.lower() == res.selected_option.lower():
                            r_list[idx].click()
                            answered.append({
                                "question": prompt[:80],
                                "answer": res.selected_option,
                                "type": "radio",
                            })
                            break
        except Exception as e:
            logger.debug("Radio question processing error: %s", e)

        # 4. Process custom unfilled text / number inputs
        text_inputs = page.locator("input[type='text'], input[type='number'], input:not([type])")
        for i in range(text_inputs.count()):
            try:
                inp = text_inputs.nth(i)
                if not inp.is_visible(timeout=150):
                    continue
                if inp.input_value().strip():
                    continue

                prompt = self._extract_label_text(page, inp)
                if not prompt:
                    continue

                # Skip basic contact questions if they were somehow missed
                if any(w in prompt.lower() for w in ["name", "email", "phone"]):
                    continue

                is_num = inp.get_attribute("type") == "number" or "number" in (inp.get_attribute("inputmode") or "")
                res = solver.solve(prompt, is_numeric=is_num)
                inp.fill(res.answer)
                answered.append({
                    "question": prompt[:80],
                    "answer": res.answer,
                    "type": "text",
                })
            except Exception as e:
                logger.debug("Custom text input error: %s", e)

        return answered

    def _extract_label_text(self, page: Page, element: Any) -> str:
        """Extract associated label or prompt text for a form element."""
        try:
            elem_id = element.get_attribute("id")
            if elem_id:
                lbl = page.locator(f"label[for='{elem_id}']").first
                if lbl.count() > 0:
                    text = lbl.inner_text().strip()
                    if text:
                        return text

            aria = element.get_attribute("aria-label")
            if aria and aria.strip():
                return aria.strip()

            placeholder = element.get_attribute("placeholder")
            if placeholder and placeholder.strip():
                return placeholder.strip()

            # Enclosing label parent
            parent_text = element.evaluate(
                "el => { const p = el.closest('label') || el.closest('.field') || el.closest('.application-question'); return p ? p.innerText : ''; }"
            )
            if parent_text:
                return parent_text.split("\n")[0].strip()
        except Exception:
            pass
        return ""

    def _extract_group_prompt(self, page: Page, element: Any) -> str:
        """Extract question prompt for a radio/checkbox group."""
        try:
            return element.evaluate(
                "el => { const g = el.closest('fieldset') || el.closest('.application-question') || el.closest('.field'); if (!g) return ''; const leg = g.querySelector('legend') || g.querySelector('.question-label') || g.querySelector('label'); return leg ? leg.innerText : ''; }"
            ).strip()
        except Exception:
            return ""

    def _extract_radio_label(self, page: Page, radio_elem: Any) -> str:
        """Extract label for an individual radio button."""
        try:
            rid = radio_elem.get_attribute("id")
            if rid:
                lbl = page.locator(f"label[for='{rid}']").first
                if lbl.count() > 0:
                    return lbl.inner_text().strip()
            return radio_elem.evaluate(
                "el => { const p = el.closest('label'); return p ? p.innerText : (el.value || ''); }"
            ).strip()
        except Exception:
            return radio_elem.get_attribute("value") or ""

    def _find_submit_button(self, page: Page) -> Any:
        """Locate the submit application button."""
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button#btn-submit",
            "button#submit_app",
            "button:has-text('Submit Application')",
            "button:has-text('Submit application')",
            "button:has-text('Submit')",
        ]
        for sel in submit_selectors:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=300):
                return loc
        return None

    def _detect_submission_success(self, page: Page) -> bool:
        """Detect whether submission succeeded via confirmation text or URL."""
        success_signals = [
            "thank you",
            "application submitted",
            "application received",
            "received your application",
            "we have received",
        ]
        try:
            content = page.content().lower()
            return any(sig in content for sig in success_signals)
        except Exception:
            return False

