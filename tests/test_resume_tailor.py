"""Unit tests for resume tailor."""

from unittest.mock import MagicMock
import pytest

from src.models.jd import JDAnalysis, Keyword
from src.models.match import MatchReport
from src.models.resume import (
    BulletPoint,
    ContactInfo,
    Education,
    Experience,
    Project,
    ResumeData,
    SkillGroup,
)
from src.models.tailored import ChangeRecord, TailoredResume
from src.resume_tailor import ResumeTailor


@pytest.fixture
def master_resume():
    return ResumeData(
        contact=ContactInfo(name="Candidate", email="c@test.com", phone="123456789"),
        summary="Data Engineer with 5 years experience.",
        skills=[SkillGroup(category="Languages", skills=["Python", "SQL"])],
        experience=[
            Experience(
                company="Stripe",
                title="Senior Data Engineer",
                start_date="2022",
                end_date="Present",
                bullets=[
                    BulletPoint(id="bullet_exp_01_01", text="Built real-time data pipelines with Python."),
                    BulletPoint(id="bullet_exp_01_02", text="Reduced query latency by 40%."),
                ],
            )
        ],
        projects=[
            Project(
                name="ETL Pipeline",
                description="Distributed pipeline",
                bullets=[BulletPoint(id="bullet_proj_01_01", text="Engineered Kafka producer.")],
                technologies=["Kafka", "Python"],
            )
        ],
        education=[Education(institution="MGM Institute", degree="B.Sc IT")],
        certifications=["AWS Certified"],
    )


@pytest.fixture
def jd_analysis():
    return JDAnalysis(
        job_id="stripe-123",
        job_title="Senior Data Engineer",
        company="Stripe",
        application_url="https://jobs.lever.co/stripe/123/apply",
        experience_level="senior",
        keywords=[
            Keyword(term="Python", category="critical", evidence="Python required", relevance_score=1.0),
            Keyword(term="Spark", category="critical", evidence="Spark required", relevance_score=0.9),
        ],
        responsibilities=[],
        qualifications_required=[],
        qualifications_preferred=[],
        raw_text="...",
    )


@pytest.fixture
def match_report():
    return MatchReport(
        job_id="stripe-123",
        application_url="https://jobs.lever.co/stripe/123/apply",
        coverage_score=0.85,
        keywords_present=[],
        keywords_promotable=[],
        keywords_addable=[],
        keywords_gap=[],
        section_recommendations=[],
    )


def test_evidence_linking_and_validation(master_resume, jd_analysis, match_report):
    # Mock LLM returning valid tailored resume with 1 valid bullet and 1 unlinked fabricated bullet
    mock_llm = MagicMock()
    mock_llm.generate_structured.return_value = TailoredResume(
        job_id="stripe-123",
        application_url="https://jobs.lever.co/stripe/123/apply",
        contact=master_resume.contact,
        summary="Senior Data Engineer specialized in Python and cloud streaming systems.",
        skills=master_resume.skills,
        experience=[
            Experience(
                company="Altered Name Inc",  # LLM attempted to change company name!
                title="Senior Data Engineer",
                start_date="2020",  # LLM attempted to change date!
                bullets=[
                    BulletPoint(
                        id="bullet_exp_01_01",
                        source_id="bullet_exp_01_01",
                        text="Engineered real-time streaming data pipelines with Python processing large workloads.",
                    ),
                    BulletPoint(
                        id="fake_bullet",
                        source_id="non_existent_source_id",  # Fabricated bullet!
                        text="Invented 500% revenue increase with Spark.",
                    ),
                ],
            )
        ],
        projects=master_resume.projects,
        education=master_resume.education,
        certifications=master_resume.certifications,
        changes=[
            ChangeRecord(
                section="Experience",
                original="Built real-time data pipelines with Python.",
                tailored="Engineered real-time streaming data pipelines with Python processing large workloads.",
                source_bullet_id="bullet_exp_01_01",
                keywords_integrated=["Python"],
                change_type="rewrite",
            )
        ],
        needs_review=[],
    )

    tailor = ResumeTailor(client=mock_llm)
    result = tailor.tailor(master_resume, jd_analysis, match_report)

    # 1. Company name and date must be strictly restored to master
    assert result.experience[0].company == "Stripe"
    assert result.experience[0].start_date == "2022"

    # 2. Fabricated unlinked bullet must NOT be in bullets list
    bullet_ids = [b.id for b in result.experience[0].bullets]
    assert "fake_bullet" not in bullet_ids

    # 3. Fabricated bullet must be in needs_review
    assert len(result.needs_review) > 0
    assert any("Invented 500%" in item for item in result.needs_review)

    # 4. Valid bullet must be preserved with valid source_id
    assert result.experience[0].bullets[0].source_id == "bullet_exp_01_01"


def test_change_summary_generation(master_resume, jd_analysis, match_report, tmp_path):
    tailor = ResumeTailor()
    result = tailor.tailor(master_resume, jd_analysis, match_report, output_dir=tmp_path)

    change_file = tmp_path / "change_summary.md"
    assert change_file.exists()
    content = change_file.read_text(encoding="utf-8")
    assert "Stripe — Senior Data Engineer" in content
    assert "https://jobs.lever.co/stripe/123/apply" in content
