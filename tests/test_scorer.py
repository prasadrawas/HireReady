"""Unit tests for scorer."""

from unittest.mock import MagicMock
import pytest

from src.models.job_listing import DeepScore, JobListing
from src.models.preferences import SearchPreferences
from src.models.resume import (
    BulletPoint,
    ContactInfo,
    Experience,
    ResumeData,
    SkillGroup,
)
from src.scorer import Scorer, tokenize


@pytest.fixture
def mock_resume():
    return ResumeData(
        contact=ContactInfo(name="Test Candidate", email="test@example.com", phone="1234567890"),
        summary="Senior Data Engineer specializing in Python, Spark, and AWS cloud pipelines.",
        skills=[
            SkillGroup(category="Languages", skills=["Python", "SQL", "Scala"]),
            SkillGroup(category="Cloud", skills=["AWS", "Terraform", "Docker"]),
        ],
        experience=[
            Experience(
                company="Data Corp",
                title="Senior Data Engineer",
                start_date="2020",
                bullets=[
                    BulletPoint(id="b1", text="Built real-time streaming pipelines using Python and Spark."),
                    BulletPoint(id="b2", text="Optimized ETL throughput by 35% on AWS."),
                ],
            )
        ],
        projects=[],
        education=[],
    )


@pytest.fixture
def sample_preferences():
    return SearchPreferences(
        target_roles=["Senior Data Engineer", "Data Platform Engineer"],
        target_keywords=["Python", "Spark", "AWS"],
        locations=["Remote"],
    )


def test_tokenize():
    tokens = tokenize("Python and Spark data pipelines!")
    assert "python" in tokens
    assert "spark" in tokens
    assert "data pipelines" in tokens


def test_quick_score_exact_match(mock_resume, sample_preferences):
    scorer = Scorer()
    job = JobListing(
        id="job-match",
        ats_source="lever",
        company="Stripe",
        company_slug="stripe",
        title="Senior Data Engineer",
        location="Remote",
        description_html="<p>We need a Senior Data Engineer skilled in Python, Spark, and AWS.</p>",
        description_text="We need a Senior Data Engineer skilled in Python, Spark, and AWS.",
        application_url="https://jobs.lever.co/stripe/1/apply",
        api_posting_id="1",
    )

    score = scorer.quick_score(job, mock_resume, sample_preferences)

    assert score.title_match == 1.0
    assert score.seniority_match == 1.0
    assert score.keyword_overlap > 0.0
    # Composite score formula: 0.5 * kw + 0.3 * title + 0.2 * seniority
    expected = round(score.keyword_overlap * 0.5 + 1.0 * 0.3 + 1.0 * 0.2, 4)
    assert abs(score.composite_score - expected) < 1e-4
    assert score.pass_to_deep_scoring is True


def test_quick_score_mismatch(mock_resume, sample_preferences):
    scorer = Scorer()
    job = JobListing(
        id="job-mismatch",
        ats_source="lever",
        company="Stripe",
        company_slug="stripe",
        title="Junior Graphic Designer",
        location="Remote",
        description_html="<p>Photoshop, Illustrator, Figma design.</p>",
        description_text="Photoshop, Illustrator, Figma design.",
        application_url="https://jobs.lever.co/stripe/2/apply",
        api_posting_id="2",
    )

    score = scorer.quick_score(job, mock_resume, sample_preferences)
    assert score.composite_score < 0.4
    assert score.pass_to_deep_scoring is False


def test_deep_score_batch(mock_resume):
    mock_llm = MagicMock()
    mock_llm.generate_structured_list.return_value = [
        DeepScore(
            job_id="job-1",
            semantic_match=0.92,
            role_fit="Direct match for data platform work.",
            key_gaps=[],
            recommendation="strong_match",
        )
    ]

    scorer = Scorer(client=mock_llm)
    job = JobListing(
        id="job-1",
        ats_source="lever",
        company="Stripe",
        company_slug="stripe",
        title="Senior Data Engineer",
        location="Remote",
        description_html="<p>Python</p>",
        description_text="Python",
        application_url="https://jobs.lever.co/stripe/1/apply",
        api_posting_id="1",
    )

    results = scorer.deep_score_batch([job], mock_resume)
    assert len(results) == 1
    assert results[0].semantic_match == 0.92
    assert results[0].recommendation == "strong_match"
