"""Intelligent question solver for job application forms.

Combines deterministic heuristic rules for standard compliance/demographic questions
with Google Gemini LLM generation for open-ended, essay, and custom job-specific questions.
"""

import logging
import re
from typing import Any
from pydantic import BaseModel

from config.settings import settings
from src.auto_apply.profile import ApplicantProfile, load_applicant_profile
from src.llm_client import LLMClient, llm_client
from src.models.resume import ResumeData

logger = logging.getLogger(__name__)


class SolveResult(BaseModel):
    """Result of solving a job application question."""

    answer: str
    category: str
    source: str  # "rule", "profile", "llm", "default"
    selected_option: str | None = None


class QuestionSolver:
    """Answers job application questions using profile data, rules, and Gemini LLM."""

    def __init__(
        self,
        profile: ApplicantProfile | None = None,
        resume: ResumeData | None = None,
        job_title: str = "",
        company: str = "",
        job_description: str = "",
        llm: LLMClient | None = None,
    ):
        self.profile = profile or load_applicant_profile()
        self.resume = resume
        self.job_title = job_title
        self.company = company
        self.job_description = job_description
        self.llm = llm or llm_client

    def solve(
        self,
        question_text: str,
        options: list[str] | None = None,
        is_textarea: bool = False,
        is_numeric: bool = False,
    ) -> SolveResult:
        """Determine the best answer for an application question.

        Args:
            question_text: The label or prompt text of the question.
            options: List of available option choices (for select/radio inputs).
            is_textarea: True if the input is a multi-line textarea (usually essay).
            is_numeric: True if the input only accepts numbers.

        Returns:
            SolveResult containing the answer string and metadata.
        """
        q_norm = question_text.strip().lower()
        cleaned_options = [opt.strip() for opt in options] if options else []

        # 1. Sponsorship question: "Will you now or in the future require visa sponsorship?"
        if any(kw in q_norm for kw in ["require sponsorship", "require visa sponsorship", "sponsorship now or in the future", "visa sponsorship"]):
            val = "Yes" if self.profile.work_authorization.requires_sponsorship else "No"
            best_opt = self._match_option(val, cleaned_options, is_boolean=True)
            return SolveResult(
                answer=best_opt or val,
                category="sponsorship",
                source="profile",
                selected_option=best_opt,
            )

        # 2. Work authorization: "Are you legally authorized to work..."
        if any(kw in q_norm for kw in [
            "authorized to work", "legally authorized", "legal right to work",
            "eligible to work", "work authorization", "authorized for employment"
        ]):
            val = "Yes" if self.profile.work_authorization.authorized_to_work else "No"
            best_opt = self._match_option(val, cleaned_options, is_boolean=True)
            return SolveResult(
                answer=best_opt or val,
                category="work_authorization",
                source="profile",
                selected_option=best_opt,
            )

        # 3. Citizenship / Immigration status
        if any(kw in q_norm for kw in ["citizenship", "immigration status", "resident status"]):
            val = self.profile.work_authorization.citizenship_status
            best_opt = self._match_option(val, cleaned_options)
            return SolveResult(
                answer=best_opt or val,
                category="citizenship",
                source="profile",
                selected_option=best_opt,
            )

        # 4. Salary / Desired compensation
        if any(kw in q_norm for kw in ["salary", "desired compensation", "target compensation", "pay expectation", "expected annual salary", "hourly rate"]):
            raw_salary = self.profile.employment_preferences.target_salary
            if is_numeric:
                digits = re.sub(r"[^\d]", "", raw_salary)
                val = digits or "180000"
            else:
                val = raw_salary
            best_opt = self._match_option(val, cleaned_options)
            return SolveResult(
                answer=best_opt or val,
                category="salary",
                source="profile",
                selected_option=best_opt,
            )

        # 5. Availability / Notice period / Start date
        if any(kw in q_norm for kw in [
            "notice period", "earliest start", "when can you start",
            "start date", "how soon can you start", "availability to start"
        ]):
            val = self.profile.employment_preferences.earliest_start_date
            best_opt = self._match_option(val, cleaned_options)
            return SolveResult(
                answer=best_opt or val,
                category="notice_period",
                source="profile",
                selected_option=best_opt,
            )

        # 6. Relocation
        if any(kw in q_norm for kw in ["relocat", "willing to move", "willing to relocate"]):
            val = "Yes" if self.profile.employment_preferences.willing_to_relocate else "No"
            best_opt = self._match_option(val, cleaned_options, is_boolean=True)
            return SolveResult(
                answer=best_opt or val,
                category="relocation",
                source="profile",
                selected_option=best_opt,
            )

        # 7. How did you hear about this role?
        if any(kw in q_norm for kw in ["how did you hear", "where did you find", "referral source", "how did you find out"]):
            val = "LinkedIn"
            best_opt = self._match_option(val, cleaned_options)
            return SolveResult(
                answer=best_opt or val,
                category="source",
                source="rule",
                selected_option=best_opt,
            )

        # 8. EEOC - Gender
        if "gender" in q_norm or q_norm == "sex":
            val = self.profile.eeoc_demographics.gender
            best_opt = self._match_option(val, cleaned_options)
            return SolveResult(
                answer=best_opt or val,
                category="eeoc_gender",
                source="profile",
                selected_option=best_opt,
            )

        # 9. EEOC - Race / Ethnicity
        if any(kw in q_norm for kw in ["race", "ethnicity", "hispanic", "latino"]):
            val = self.profile.eeoc_demographics.race_ethnicity
            best_opt = self._match_option(val, cleaned_options)
            return SolveResult(
                answer=best_opt or val,
                category="eeoc_race",
                source="profile",
                selected_option=best_opt,
            )

        # 10. EEOC - Veteran
        if "veteran" in q_norm or "military" in q_norm:
            val = self.profile.eeoc_demographics.veteran_status
            best_opt = self._match_option(val, cleaned_options)
            return SolveResult(
                answer=best_opt or val,
                category="eeoc_veteran",
                source="profile",
                selected_option=best_opt,
            )

        # 11. EEOC - Disability
        if "disability" in q_norm or "handicap" in q_norm:
            val = self.profile.eeoc_demographics.disability_status
            best_opt = self._match_option(val, cleaned_options)
            return SolveResult(
                answer=best_opt or val,
                category="eeoc_disability",
                source="profile",
                selected_option=best_opt,
            )

        # 12. Multiple Choice / Dropdown without specific rule
        if cleaned_options:
            matched = self._solve_options_via_llm_or_heuristic(question_text, cleaned_options)
            return SolveResult(
                answer=matched,
                category="choice",
                source="heuristic_or_llm",
                selected_option=matched,
            )

        # 13. Open-ended / Essay Question (or textarea)
        return self._solve_open_ended_via_llm(question_text, is_textarea=is_textarea)

    def _match_option(self, target_val: str, options: list[str], is_boolean: bool = False) -> str | None:
        """Find the best matching option from a dropdown or radio list."""
        if not options:
            return None

        target_norm = target_val.lower().strip()

        # Direct exact match
        for opt in options:
            if opt.lower().strip() == target_norm:
                return opt

        # Boolean match
        if is_boolean:
            is_yes = target_norm in ["yes", "true", "authorized", "eligible"]
            for opt in options:
                opt_norm = opt.lower().strip()
                if is_yes and (opt_norm in ["yes", "y", "true", "i am"] or opt_norm.startswith("yes")):
                    return opt
                if not is_yes and (opt_norm in ["no", "n", "false", "i am not"] or opt_norm.startswith("no")):
                    return opt

        # Decline / Prefer not to say
        if "decline" in target_norm or "prefer not" in target_norm:
            for opt in options:
                opt_norm = opt.lower()
                if any(w in opt_norm for w in ["decline", "prefer not", "choose not", "not to answer", "wish to disclose"]):
                    return opt

        # Substring / fuzzy match
        for opt in options:
            opt_norm = opt.lower()
            if target_norm in opt_norm or opt_norm in target_norm:
                return opt

        # Default fallback: return first option that doesn't say "Select..."
        valid_opts = [o for o in options if not o.lower().startswith("select") and o.strip() != ""]
        return valid_opts[0] if valid_opts else options[0]

    def _solve_options_via_llm_or_heuristic(self, question: str, options: list[str]) -> str:
        """Match options using resume keywords or LLM."""
        q_lower = question.lower()

        # Experience / Years of experience
        if "years of experience" in q_lower or "how many years" in q_lower:
            # Most Senior roles match 5-8+ or the highest realistic tier
            for opt in options:
                if any(marker in opt for marker in ["5+", "5-7", "6+", "7+", "8+", "5 years"]):
                    return opt

        # Education degree match
        if "degree" in q_lower or "education" in q_lower:
            for opt in options:
                if any(deg in opt.lower() for deg in ["bachelor", "master", "bs", "ms"]):
                    return opt

        # Attempt quick LLM selection
        try:
            options_text = "\n".join(f"- {o}" for o in options)
            prompt = (
                f"You are applying for the role of {self.job_title} at {self.company}.\n"
                f"Candidate: {self.profile.contact.full_name}\n"
                f"Question: {question}\n\n"
                f"Options:\n{options_text}\n\n"
                f"Select the single most appropriate option from the list. Return ONLY the exact text of the option, nothing else."
            )
            raw = self.llm.generate_text(prompt, temperature=0.1)
            cleaned = raw.strip().strip('"').strip("'")
            for opt in options:
                if opt.strip().lower() == cleaned.lower():
                    return opt
        except Exception as e:
            logger.debug("LLM option resolution error: %s", e)

        # Fallback to first non-empty option
        for opt in options:
            if opt.strip() and not opt.lower().startswith("select"):
                return opt
        return options[0]

    def _solve_open_ended_via_llm(self, question: str, is_textarea: bool = True) -> SolveResult:
        """Generate tailored authentic answer to custom open-ended questions using Gemini."""
        resume_summary = ""
        if self.resume:
            skills_flat = []
            skill_list = getattr(self.resume, "skills", None) or getattr(self.resume, "skill_groups", [])
            for g in skill_list:
                skills_flat.extend(g.skills[:5])
            recent_bullets = []
            for exp in (self.resume.experience or [])[:2]:
                for b in exp.bullets[:2]:
                    recent_bullets.append(b.text)
            resume_summary = (
                f"Key Skills: {', '.join(skills_flat[:15])}\n"
                f"Recent Highlights:\n" + "\n".join(f"- {b}" for b in recent_bullets)
            )

        prompt = (
            f"You are writing an authentic, highly persuasive job application answer for {self.profile.contact.full_name}.\n"
            f"Job Position: {self.job_title} at {self.company}\n\n"
            f"Candidate Background:\n{resume_summary}\n\n"
            f"Application Question:\n\"{question}\"\n\n"
            f"Instructions:\n"
            f"- Write in first person ('I') as the candidate.\n"
            f"- Answer the question directly and professionally.\n"
            f"- Keep it concise: 2 to 4 sentences maximum (approx 50-80 words).\n"
            f"- Ground the answer in solid engineering/data practice and genuine enthusiasm.\n"
            f"- Do not use generic buzzwords or hollow placeholders.\n"
            f"- Return ONLY the final answer text."
        )

        try:
            answer = self.llm.generate_text(prompt, temperature=0.3)
            return SolveResult(
                answer=answer.strip(),
                category="custom_essay",
                source="llm",
            )
        except Exception as e:
            logger.warning("LLM generation failed for question '%s': %s", question, e)
            # Reliable deterministic fallback
            return SolveResult(
                answer=(
                    f"With my proven track record in software engineering and scalable data platforms, "
                    f"I am eager to contribute to {self.company}. I look forward to discussing how my experience "
                    f"aligns with your team's goals."
                ),
                category="custom_essay",
                source="default",
            )
