"""Supervision and submission detection for automated job applications."""

import logging
import time
from typing import Any

from playwright.sync_api import Page

logger = logging.getLogger(__name__)


class ReviewSupervisor:
    """Supervises candidate review window and monitors application submission."""

    @staticmethod
    def find_submit_button(page: Page) -> Any:
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

    @staticmethod
    def detect_submission_success(page: Page) -> bool:
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

    def supervise(
        self,
        page: Page,
        submit_button: Any,
        auto_submit: bool,
        review_timeout_sec: int,
        company_name: str,
        headed: bool = True,
    ) -> tuple[str, str]:
        """Supervise the submission or review phase.

        Returns:
            Tuple of (submission_status, message)
        """
        if auto_submit:
            if submit_button:
                logger.info("Auto-submitting application for %s...", company_name)
                submit_button.click()
                page.wait_for_timeout(4000)
                return "submitted", f"Application for {company_name} submitted successfully!"
            return "filled_needs_click", "Form filled, but submit button could not be safely clicked automatically."

        # Supervised review mode
        submission_status = "ready_for_review"
        message = f"Form successfully filled for {company_name}. Supervised review window active."

        if headed and review_timeout_sec > 0:
            start_time = time.time()
            initial_url = page.url
            while time.time() - start_time < review_timeout_sec:
                page.wait_for_timeout(500)
                if page.url != initial_url or self.detect_submission_success(page):
                    submission_status = "submitted"
                    message = f"Application for {company_name} was submitted!"
                    break

        return submission_status, message

