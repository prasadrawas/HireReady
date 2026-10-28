"""Tests for the Auto-Apply module, profile loader, question solver, and runner."""

from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch
import pytest

from config.settings import settings
from src.auto_apply.profile import ApplicantProfile, ContactProfile, load_applicant_profile
from src.auto_apply.question_solver import QuestionSolver, SolveResult
from src.auto_apply.runner import AutoApplyRunner
from src.models.job_listing import JobListing
from src.models.resume import ContactInfo as ResumeContactInfo, ResumeData, BulletPoint, Experience, SkillGroup


@pytest.fixture
def sample_profile() -> ApplicantProfile:
    return ApplicantProfile(
        contact=ContactProfile(
            first_name="Prasad",
            last_name="Rawas",
            full_name="Prasad Rawas",
            email="prasad@example.com",
            phone="+1-555-019-2834",
            location="San Francisco, CA",
            linkedin="https://linkedin.com/in/prasadrawas",
            github="https://github.com/prasadrawas",
            website="https://dev.prasadrawas.online",
            current_company="Acme Corp",
            current_title="Senior Data Engineer",
        )
    )


@pytest.fixture
def sample_resume() -> ResumeData:
    return ResumeData(
        contact=ResumeContactInfo(
            name="Prasad Rawas",
            email="prasad@example.com",
            phone="+1-555-019-2834",
        ),
        summary="Senior Data Engineer with expertise in Apache Spark, Kafka, and Snowflake.",
        skills=[
            SkillGroup(category="Languages", skills=["Python", "SQL"]),
            SkillGroup(category="Frameworks", skills=["Spark", "Kafka", "Airflow"]),
        ],
        experience=[
            Experience(
                company="Acme Corp",
                title="Senior Data Engineer",
                start_date="2022",
                bullets=[
                    BulletPoint(id="b1", text="Built real-time streaming pipeline processing 10TB/day with Kafka and Spark."),
                ],
            ),
        ],
    )


def test_applicant_profile_loading(tmp_path: Path):
    """Test loading applicant profile from YAML file."""
    yaml_content = """
contact:
  first_name: "Jane"
  last_name: "Doe"
  email: "jane@example.com"
  phone: "123-456-7890"

work_authorization:
  authorized_to_work: true
  requires_sponsorship: false

employment_preferences:
  target_salary: "$195,000"
  earliest_start_date: "Immediate"
"""
    yaml_path = tmp_path / "applicant_profile.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")

    profile = load_applicant_profile(yaml_path)
    assert profile.contact.first_name == "Jane"
    assert profile.contact.last_name == "Doe"
    assert profile.contact.full_name == "Jane Doe"
    assert profile.contact.email == "jane@example.com"
    assert profile.work_authorization.authorized_to_work is True
    assert profile.work_authorization.requires_sponsorship is False
    assert profile.employment_preferences.target_salary == "$195,000"
    assert profile.employment_preferences.earliest_start_date == "Immediate"


def test_question_solver_compliance_and_rules(sample_profile: ApplicantProfile, sample_resume: ResumeData):
    """Test question solver handles deterministic compliance, salary, notice period, and EEOC questions."""
    solver = QuestionSolver(
        profile=sample_profile,
        resume=sample_resume,
        job_title="Senior Data Engineer",
        company="TechCorp",
    )

    # 1. Sponsorship question
    res = solver.solve("Will you now or in the future require visa sponsorship?", options=["Yes", "No"])
    assert res.category == "sponsorship"
    assert res.answer == "No"

    # 2. Work authorization question
    res = solver.solve("Are you legally authorized to work in the United States?", options=["Yes", "No"])
    assert res.category == "work_authorization"
    assert res.answer == "Yes"

    # 3. Salary question (string format)
    res = solver.solve("What is your desired annual salary?")
    assert res.category == "salary"
    assert res.answer == "$180,000"

    # 4. Salary question (numeric input)
    res = solver.solve("What is your expected salary (numbers only)?", is_numeric=True)
    assert res.category == "salary"
    assert res.answer == "180000"

    # 5. Notice period / Start date
    res = solver.solve("When can you start / What is your notice period?")
    assert res.category == "notice_period"
    assert res.answer == "2 weeks notice"

    # 6. Relocation
    res = solver.solve("Are you willing to relocate for this position?", options=["Yes", "No"])
    assert res.category == "relocation"
    assert res.answer == "Yes"

    # 7. Referral source
    res = solver.solve("How did you hear about us?", options=["LinkedIn", "Indeed", "Friend"])
    assert res.category == "source"
    assert res.answer == "LinkedIn"

    # 8. EEOC Gender
    res = solver.solve("Please select your gender identity", options=["Male", "Female", "Decline to self-identify"])
    assert res.category == "eeoc_gender"
    assert res.answer == "Decline to self-identify"

    # 9. EEOC Race
    res = solver.solve("What is your race / ethnicity?", options=["Asian", "White", "Decline to self-identify"])
    assert res.category == "eeoc_race"
    assert res.answer == "Decline to self-identify"


def test_question_solver_llm_essay(sample_profile: ApplicantProfile, sample_resume: ResumeData):
    """Test question solver uses Gemini LLM for open-ended essay questions."""
    mock_llm = MagicMock()
    mock_llm.generate_text.return_value = (
        "I have led large-scale distributed streaming pipelines at Acme Corp processing over 10TB daily. "
        "My deep background in Kafka and Spark directly matches TechCorp's high-throughput requirements."
    )

    solver = QuestionSolver(
        profile=sample_profile,
        resume=sample_resume,
        job_title="Senior Data Engineer",
        company="TechCorp",
        llm=mock_llm,
    )

    res = solver.solve("Why do you want to join TechCorp and what experience makes you a fit?", is_textarea=True)
    assert res.category == "custom_essay"
    assert res.source == "llm"
    assert "10TB daily" in res.answer
    assert mock_llm.generate_text.called


def test_question_solver_option_matching(sample_profile: ApplicantProfile):
    """Test option matching logic across case variations and synonyms."""
    solver = QuestionSolver(profile=sample_profile)

    # Boolean affirmative
    opt = solver._match_option("Yes", ["Yes, I am authorized", "No, I need sponsorship"], is_boolean=True)
    assert opt == "Yes, I am authorized"

    # Boolean negative
    opt = solver._match_option("No", ["Yes, I do", "No, I do not"], is_boolean=True)
    assert opt == "No, I do not"

    # Decline option
    opt = solver._match_option("Decline to self-identify", ["Male", "Female", "I prefer not to say"])
    assert opt == "I prefer not to say"


def test_auto_apply_runner_missing_job():
    """Test AutoApplyRunner raises error for unknown job ID."""
    mock_service = MagicMock()
    mock_service.get_jobs.return_value = {"jobs": []}

    runner = AutoApplyRunner(service=mock_service)
    with pytest.raises(ValueError, match="not found in scan results"):
        runner.apply(job_id="unknown_123")


def test_auto_apply_runner_mocked_playwright(tmp_path: Path, sample_profile: ApplicantProfile):
    """Test AutoApplyRunner completes execution against mocked Playwright objects."""
    job_data = {
        "id": "job_test_1",
        "company": "Stripe",
        "company_slug": "stripe",
        "title": "Staff Software Engineer",
        "application_url": "https://jobs.lever.co/stripe/test-job/apply",
        "ats_source": "lever",
        "location": "San Francisco, CA",
        "description_html": "<p>Build payment infrastructure</p>",
        "description_text": "Build payment infrastructure",
        "api_posting_id": "posting_123",
        "score": 0.88,
    }

    mock_service = MagicMock()
    mock_service.get_jobs.return_value = {"jobs": [job_data]}
    mock_service.get_resume.return_value = None

    mock_tracker = MagicMock()

    # Mock PDF and Cover Letter paths
    dummy_pdf = tmp_path / "resume.pdf"
    dummy_pdf.write_text("%PDF-1.4 dummy", encoding="utf-8")
    dummy_cl = tmp_path / "cover_letter.txt"
    dummy_cl.write_text("Dear Hiring Team,\nI am writing to apply...", encoding="utf-8")

    with patch.object(type(settings), "output_dir", new_callable=PropertyMock, return_value=tmp_path.parent), \
         patch.object(type(settings), "input_dir", new_callable=PropertyMock, return_value=tmp_path), \
         patch("src.auto_apply.runner.sync_playwright") as mock_playwright:

        # Mock browser, context, page
        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_p.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        mock_page.url = "https://jobs.lever.co/stripe/test-job/apply"
        mock_page.content.return_value = "<html><body>Application Submitted</body></html>"

        # Mock locators
        mock_locator = MagicMock()
        mock_locator.count.return_value = 0
        mock_locator.first = mock_locator
        mock_locator.is_visible.return_value = False
        mock_page.locator.return_value = mock_locator

        runner = AutoApplyRunner(profile=sample_profile, service=mock_service, tracker=mock_tracker)
        result = runner.apply(
            job_id="job_test_1",
            headed=False,
            auto_submit=False,
            review_timeout_sec=0,
        )

        assert result["success"] is True
        assert result["job_id"] == "job_test_1"
        assert result["company"] == "Stripe"
        assert mock_tracker.record_application.called
        assert mock_browser.close.called


def test_auto_apply_api_endpoint():
    """Test POST /api/jobs/{job_id}/auto-apply route invokes service and returns result."""
    from fastapi.testclient import TestClient
    from src.api.app import app

    client = TestClient(app)
    with patch("src.api.routes.service.auto_apply_job") as mock_apply:
        mock_apply.return_value = {
            "success": True,
            "job_id": "job_123",
            "company": "Figma",
            "title": "Data Engineer",
            "status": "ready_for_review",
            "message": "Form successfully filled",
            "fields_filled": ["first_name", "last_name", "email"],
            "questions_answered": [],
        }

        response = client.post(
            "/api/jobs/job_123/auto-apply",
            json={"headed": True, "auto_submit": False, "review_timeout_sec": 15},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["company"] == "Figma"
        mock_apply.assert_called_once_with(
            job_id="job_123",
            headed=True,
            auto_submit=False,
            review_timeout_sec=15,
        )
