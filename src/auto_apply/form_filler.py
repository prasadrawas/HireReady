"""Form interaction and field-filling engine for job applications."""

import logging
from pathlib import Path
from typing import Any

from playwright.sync_api import Page

from src.auto_apply.profile import ApplicantProfile
from src.auto_apply.question_solver import QuestionSolver

logger = logging.getLogger(__name__)


class FormFiller:
    """Handles locating and populating form elements across ATS platforms."""

    @staticmethod
    def navigate_to_form(page: Page) -> None:
        """Check if an 'Apply' or 'Apply for this job' button exists on landing page and click it."""
        try:
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

    @staticmethod
    def fill_contact_info(page: Page, profile: ApplicantProfile) -> list[str]:
        """Fill candidate contact information."""
        c = profile.contact
        filled: list[str] = []

        field_mappings = [
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

    @staticmethod
    def upload_resume(page: Page, pdf_path: Path) -> bool:
        """Find the resume file input and upload the tailored PDF."""
        file_inputs = page.locator("input[type='file']")
        if file_inputs.count() == 0:
            return False

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

        try:
            file_inputs.first.set_input_files(str(pdf_path))
            return True
        except Exception as e:
            logger.debug("Failed setting file on first input[type='file']: %s", e)
            return False

    @staticmethod
    def fill_cover_letter(page: Page, text: str) -> bool:
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

    def fill_custom_questions(self, page: Page, solver: QuestionSolver) -> list[dict[str, str]]:
        """Inspect and answer custom form questions (selects, textareas, un-filled text inputs, radios)."""
        answered: list[dict[str, str]] = []

        # 1. Process Select / Dropdowns
        selects = page.locator("select")
        for i in range(selects.count()):
            try:
                sel = selects.nth(i)
                if not sel.is_visible(timeout=200):
                    continue

                prompt = self._extract_label_text(page, sel)
                if not prompt:
                    continue

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

        # 2. Process Textareas
        textareas = page.locator("textarea")
        for i in range(textareas.count()):
            try:
                ta = textareas.nth(i)
                if not ta.is_visible(timeout=200):
                    continue
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
                checked = any(r.is_checked() for r in group.all())
                if checked:
                    continue

                first_r = group.first
                prompt = self._extract_group_prompt(page, first_r)
                if not prompt:
                    continue

                opt_labels = []
                r_list = group.all()
                for r in r_list:
                    lbl = self._extract_radio_label(page, r)
                    opt_labels.append(lbl)

                res = solver.solve(prompt, options=opt_labels)
                if res.selected_option:
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

