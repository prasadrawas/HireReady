"""Unit tests for HTML generator."""

from bs4 import BeautifulSoup
import pytest

from src.html_generator import HTMLGenerator
from src.models.resume import (
    BulletPoint,
    ContactInfo,
    Education,
    Experience,
    Project,
    ResumeData,
    SkillGroup,
)


@pytest.fixture
def sample_resume():
    return ResumeData(
        contact=ContactInfo(
            name="Jane Doe",
            email="jane@example.com",
            phone="(555) 019-2834",
            linkedin="https://linkedin.com/in/janedoe",
            github="https://github.com/janedoe",
            location="San Francisco, CA",
        ),
        summary="Senior Data Engineer with extensive cloud architecture experience.",
        skills=[
            SkillGroup(category="Languages", skills=["Python", "SQL", "Scala"]),
            SkillGroup(category="Cloud", skills=["AWS", "Terraform"]),
        ],
        experience=[
            Experience(
                company="Stripe",
                title="Senior Data Engineer",
                start_date="2022",
                end_date="Present",
                bullets=[
                    BulletPoint(id="bullet_exp_01_01", text="Engineered real-time pipelines processing 2M events."),
                ],
            )
        ],
        projects=[
            Project(
                name="StreamEngine",
                description="High throughput engine",
                technologies=["Spark", "Kafka"],
                bullets=[BulletPoint(id="bullet_proj_01_01", text="Stream processing cluster.")],
            )
        ],
        education=[Education(institution="UC Berkeley", degree="B.S. in Computer Science", start_date="2016", end_date="2020")],
        certifications=["AWS Certified Data Analytics"],
    )


def test_html_generator_semantic_structure(sample_resume, tmp_path):
    generator = HTMLGenerator()
    out_file = tmp_path / "resume.html"
    html = generator.generate(sample_resume, target_role="Senior Data Engineer", output_path=out_file)

    assert out_file.exists()
    assert html.startswith("<!DOCTYPE html>")

    soup = BeautifulSoup(html, "html.parser")

    # 1. Semantic sections
    assert soup.find("section", id="contact") is not None
    assert soup.find("section", id="summary") is not None
    assert soup.find("section", id="skills") is not None
    assert soup.find("section", id="experience") is not None
    assert soup.find("section", id="projects") is not None
    assert soup.find("section", id="education") is not None
    assert soup.find("section", id="certifications") is not None

    # 2. Content integrity
    assert "Jane Doe" in soup.get_text()
    assert "jane@example.com" in soup.get_text()
    assert "Stripe" in soup.get_text()
    assert "StreamEngine" in soup.get_text()
    assert "UC Berkeley" in soup.get_text()
    assert "AWS Certified Data Analytics" in soup.get_text()

    # 3. Check for ATS anti-patterns:
    # No layout tables
    assert len(soup.find_all("table")) == 0
    # No canvas or svg as text
    assert len(soup.find_all("canvas")) == 0
    # Links work
    links = [a["href"] for a in soup.find_all("a", href=True)]
    assert "mailto:jane@example.com" in links
    assert "https://linkedin.com/in/janedoe" in links
