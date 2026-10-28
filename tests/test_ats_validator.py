"""Unit tests for ATS validator."""

from pathlib import Path
import pytest

from src.ats_validator import ATSValidator
from src.html_generator import HTMLGenerator
from src.models.jd import JDAnalysis, Keyword
from src.models.resume import (
    BulletPoint,
    ContactInfo,
    Education,
    Experience,
    Project,
    ResumeData,
    SkillGroup,
)
from src.models.tailored import TailoredResume
from src.pdf_generator import PDFGenerator


@pytest.fixture
def test_setup(tmp_path):
    contact = ContactInfo(
        name="Alex Smith",
        email="alex@example.com",
        phone="555-010-9988",
        linkedin="https://linkedin.com/in/alexsmith",
        location="New York, NY",
    )
    master = ResumeData(
        contact=contact,
        summary="Senior Backend Engineer with Python and AWS experience.",
        skills=[SkillGroup(category="Backend", skills=["Python", "FastAPI", "AWS", "SQL"])],
        experience=[
            Experience(
                company="DataStream",
                title="Senior Backend Engineer",
                start_date="2021",
                end_date="Present",
                bullets=[BulletPoint(id="b1", text="Built scalable REST APIs with Python.")],
            )
        ],
        projects=[],
        education=[Education(institution="NYU", degree="B.S. in Computer Science")],
    )

    tailored = TailoredResume(
        job_id="test-job-1",
        application_url="https://example.com/apply",
        contact=contact,
        summary=master.summary,
        skills=master.skills,
        experience=master.experience,
        projects=[],
        education=master.education,
        changes=[],
        needs_review=[],
    )

    jd_analysis = JDAnalysis(
        job_id="test-job-1",
        job_title="Senior Backend Engineer",
        company="DataStream",
        application_url="https://example.com/apply",
        experience_level="senior",
        keywords=[
            Keyword(term="Python", category="critical", evidence="Python", relevance_score=1.0),
            Keyword(term="AWS", category="critical", evidence="AWS", relevance_score=0.9),
        ],
        responsibilities=[],
        qualifications_required=[],
        qualifications_preferred=[],
        raw_text="...",
    )

    # Generate real HTML and PDF files
    html_file = tmp_path / "resume.html"
    pdf_file = tmp_path / "resume.pdf"

    html_gen = HTMLGenerator()
    html_gen.generate(tailored, output_path=html_file)

    pdf_gen = PDFGenerator()
    pdf_gen.generate_pdf(html_path=html_file, pdf_path=pdf_file)

    return {
        "html_file": html_file,
        "pdf_file": pdf_file,
        "tailored": tailored,
        "master": master,
        "jd_analysis": jd_analysis,
    }


def test_validator_passes_valid_pdf(test_setup):
    validator = ATSValidator()
    report = validator.validate(
        pdf_path=test_setup["pdf_file"],
        html_path=test_setup["html_file"],
        tailored_resume=test_setup["tailored"],
        master_resume=test_setup["master"],
        jd_analysis=test_setup["jd_analysis"],
    )

    assert report.passed is True
    assert report.page_count in [1, 2]
    check_names = {c.check for c in report.checks if c.passed}
    assert "pdf_opens" in check_names
    assert "text_extractable" in check_names
    assert "contact_info_present" in check_names
    assert "no_unsupported_claims" in check_names


def test_validator_fails_unsupported_claims(test_setup):
    validator = ATSValidator()
    tailored_with_review = test_setup["tailored"].model_copy(deep=True)
    tailored_with_review.needs_review = ["Unlinked claim about quantum computing"]

    report = validator.validate(
        pdf_path=test_setup["pdf_file"],
        html_path=test_setup["html_file"],
        tailored_resume=tailored_with_review,
        master_resume=test_setup["master"],
        jd_analysis=test_setup["jd_analysis"],
    )

    assert report.passed is False
    unsupported_check = next(c for c in report.checks if c.check == "no_unsupported_claims")
    assert unsupported_check.passed is False


def test_validator_fails_missing_pdf(test_setup, tmp_path):
    validator = ATSValidator()
    missing_pdf = tmp_path / "does_not_exist.pdf"

    report = validator.validate(
        pdf_path=missing_pdf,
        html_path=test_setup["html_file"],
        tailored_resume=test_setup["tailored"],
        master_resume=test_setup["master"],
        jd_analysis=test_setup["jd_analysis"],
    )

    assert report.passed is False
    assert any(c.check == "pdf_opens" and not c.passed for c in report.checks)
