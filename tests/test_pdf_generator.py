"""Unit tests for PDF generator."""

from pathlib import Path
import pymupdf
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
from src.pdf_generator import PDFGenerator


@pytest.fixture
def sample_resume():
    return ResumeData(
        contact=ContactInfo(
            name="John Developer",
            email="john@example.com",
            phone="1234567890",
            location="San Francisco, CA",
        ),
        summary="Senior Software Engineer with 7 years of backend expertise.",
        skills=[SkillGroup(category="Backend", skills=["Python", "FastAPI", "PostgreSQL"])],
        experience=[
            Experience(
                company="TechCo",
                title="Lead Engineer",
                start_date="2020",
                end_date="Present",
                bullets=[
                    BulletPoint(id="b1", text="Designed enterprise microservices architecture."),
                    BulletPoint(id="b2", text="Scaled distributed messaging queues to 1M events daily."),
                ],
            )
        ],
        projects=[],
        education=[Education(institution="University of Technology", degree="B.S. Computer Engineering")],
    )


def test_pdf_generation_and_text_extraction(sample_resume, tmp_path):
    html_gen = HTMLGenerator()
    html_file = tmp_path / "resume.html"
    pdf_file = tmp_path / "resume.pdf"

    html_gen.generate(sample_resume, output_path=html_file)
    assert html_file.exists()

    pdf_gen = PDFGenerator()
    generated_pdf = pdf_gen.generate_pdf(html_path=html_file, pdf_path=pdf_file)

    assert generated_pdf.exists()
    assert generated_pdf.stat().st_size > 1000

    # Extract text with PyMuPDF
    doc = pymupdf.open(str(generated_pdf))
    try:
        assert len(doc) >= 1
        assert len(doc) <= 2  # Page count within 1-2 pages

        full_text = "\n".join(page.get_text() for page in doc)
        assert "John Developer" in full_text
        assert "Lead Engineer" in full_text
        assert "microservices architecture" in full_text
        assert "john@example.com" in full_text
    finally:
        doc.close()
