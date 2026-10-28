"""Auto-Apply module for HireReady.

Automates job application submissions across ATS platforms using Playwright
with supervised review and LLM-assisted custom question answering.
"""

from src.auto_apply.profile import ApplicantProfile, load_applicant_profile
from src.auto_apply.question_solver import QuestionSolver
from src.auto_apply.runner import AutoApplyRunner

__all__ = [
    "ApplicantProfile",
    "load_applicant_profile",
    "QuestionSolver",
    "AutoApplyRunner",
]

