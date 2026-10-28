"""Unit tests for JD parser."""

import pymupdf
import pytest

from src.jd_parser import JDParser


def test_clean_html_strips_tags_and_formats_lines():
    html = """
    <div>
      <h1>Senior Data Engineer</h1>
      <p>Requirements:</p>
      <ul>
        <li>5+ years of Python experience.</li>
        <li>Strong knowledge of distributed SQL databases.</li>
      </ul>
      <style>body { color: red; }</style>
      <script>console.log("tracking");</script>
    </div>
    """
    cleaned = JDParser.clean_html(html)
    assert "Senior Data Engineer" in cleaned
    assert "5+ years of Python experience." in cleaned
    assert "tracking" not in cleaned
    assert "<style>" not in cleaned
    assert "<li>" not in cleaned


def test_clean_html_removes_boilerplate():
    html = """
    <div>
      <h1>Backend Engineer</h1>
      <p>Build high scale services with Go and Kubernetes.</p>
      <p>Equal Opportunity Employer: We celebrate diversity and are committed to creating an inclusive environment.</p>
    </div>
    """
    cleaned = JDParser.clean_html(html)
    assert "Backend Engineer" in cleaned
    assert "Build high scale services" in cleaned
    assert "Equal Opportunity Employer" not in cleaned


def test_clean_text_handles_encoding_and_empty():
    assert JDParser.clean_html("") == ""
    assert JDParser.clean_html("   ") == ""
    assert JDParser.clean_text(None) == ""

    # Non-breaking space and smart quotes
    text_with_nbsp = "Senior\xa0Engineer\u2019s\xa0Role"
    cleaned = JDParser.clean_text(text_with_nbsp)
    assert "Senior Engineer's Role" in cleaned or "Senior Engineer" in cleaned


def test_extract_from_text_file(tmp_path):
    txt_file = tmp_path / "sample_jd.txt"
    txt_file.write_text("Senior Full Stack Developer\n\nFastAPI and React expertise required.", encoding="utf-8")

    extracted = JDParser.extract_from_file(txt_file)
    assert "Senior Full Stack Developer" in extracted
    assert "FastAPI and React" in extracted


def test_extract_from_pdf_file(tmp_path):
    pdf_file = tmp_path / "sample_jd.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Cloud Platform Engineer\nTerraform and AWS required.")
    doc.save(str(pdf_file))
    doc.close()

    extracted = JDParser.extract_from_file(pdf_file)
    assert "Cloud Platform Engineer" in extracted
    assert "Terraform and AWS" in extracted
