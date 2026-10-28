"""Unit tests for resume matcher."""

import pytest

from src.models.jd import JDAnalysis, Keyword
from src.models.resume import (
    BulletPoint,
    ContactInfo,
    Experience,
    ResumeData,
    SkillGroup,
)
from src.resume_matcher import ResumeMatcher


@pytest.fixture
def sample_resume():
    return ResumeData(
        contact=ContactInfo(name="Candidate", email="c@test.com", phone="123456789"),
        summary="Experienced Python developer.",
        skills=[
            SkillGroup(category="Languages", skills=["Python", "SQL"]),
            SkillGroup(category="Cloud", skills=["AWS", "Kubernetes"]),
        ],
        experience=[
            Experience(
                company="TechCo",
                title="Software Engineer",
                start_date="2022",
                bullets=[
                    BulletPoint(id="b_01_01", text="Built REST APIs in Python."),
                    BulletPoint(id="b_01_02", text="Used Celery for background job processing."),
                ],
            )
        ],
        projects=[],
        education=[],
    )


def test_keyword_matching_statuses(sample_resume):
    matcher = ResumeMatcher()
    analysis = JDAnalysis(
        job_id="test-job",
        job_title="Backend Engineer",
        company="Stripe",
        application_url="https://jobs.lever.co/stripe/test/apply",
        experience_level="mid",
        keywords=[
            # Present in skills
            Keyword(term="Python", category="critical", evidence="Python required", relevance_score=1.0),
            # Promotable (only in 1 bullet, not in skills)
            Keyword(term="Celery", category="high", evidence="Celery tasks", relevance_score=0.8),
            # Addable (synonym for Kubernetes)
            Keyword(term="K8s", category="high", evidence="K8s cluster management", relevance_score=0.7),
            # Gap (not in resume)
            Keyword(term="Rust", category="critical", evidence="Rust services", relevance_score=0.9),
        ],
        responsibilities=[],
        qualifications_required=[],
        qualifications_preferred=[],
        raw_text="...",
    )

    report = matcher.match(analysis, sample_resume)

    present_terms = [k.term for k in report.keywords_present]
    promotable_terms = [k.term for k in report.keywords_promotable]
    addable_terms = [k.term for k in report.keywords_addable]
    gap_terms = [k.term for k in report.keywords_gap]

    assert "Python" in present_terms
    assert "Celery" in promotable_terms
    assert "K8s" in addable_terms
    assert "Rust" in gap_terms
    assert 0.0 < report.coverage_score < 1.0


def test_coverage_score_full_overlap(sample_resume):
    matcher = ResumeMatcher()
    analysis = JDAnalysis(
        job_id="test-job-full",
        job_title="Python Engineer",
        company="Acme",
        application_url="https://acme.com/apply",
        experience_level="mid",
        keywords=[
            Keyword(term="Python", category="critical", evidence="Python", relevance_score=1.0),
            Keyword(term="AWS", category="high", evidence="AWS", relevance_score=0.9),
        ],
        responsibilities=[],
        qualifications_required=[],
        qualifications_preferred=[],
        raw_text="...",
    )

    report = matcher.match(analysis, sample_resume)
    assert report.coverage_score == 1.0
    assert len(report.keywords_gap) == 0


def test_coverage_score_zero_overlap(sample_resume):
    matcher = ResumeMatcher()
    analysis = JDAnalysis(
        job_id="test-job-zero",
        job_title="Embedded Engineer",
        company="HardwareCorp",
        application_url="https://hw.com/apply",
        experience_level="mid",
        keywords=[
            Keyword(term="Verilog", category="critical", evidence="Verilog", relevance_score=1.0),
            Keyword(term="FPGA", category="high", evidence="FPGA", relevance_score=0.9),
        ],
        responsibilities=[],
        qualifications_required=[],
        qualifications_preferred=[],
        raw_text="...",
    )

    report = matcher.match(analysis, sample_resume)
    assert report.coverage_score == 0.0
    assert len(report.keywords_gap) == 2
