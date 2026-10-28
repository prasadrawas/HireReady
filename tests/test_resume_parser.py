"""Tests for resume parser."""

import pytest
from src.resume_parser import ResumeParser, load_preferences
from src.models.resume import ResumeData


SAMPLE_TEMPLATE_HTML = """<!DOCTYPE html>
<html>
<head><title>Jane Doe — Resume</title></head>
<body>
  <section id="contact">
    <h1>Jane Doe</h1>
    <p>jane@example.com | (555) 123-4567 | linkedin.com/in/janedoe | github.com/janedoe</p>
    <p>San Francisco, CA</p>
  </section>

  <section id="summary">
    <h2>Professional Summary</h2>
    <p>Experienced Data Engineer with 6 years building pipelines.</p>
  </section>

  <section id="skills">
    <h2>Skills</h2>
    <div class="skill-group">
      <strong>Languages:</strong> Python, SQL, Scala
    </div>
    <div class="skill-group">
      <strong>Cloud & Infrastructure:</strong> AWS, GCP, Terraform
    </div>
  </section>

  <section id="experience">
    <h2>Experience</h2>
    <div class="job">
      <h3>Senior Data Engineer</h3>
      <div class="meta">
        <span class="company">Stripe</span>
        <span class="location">San Francisco, CA</span>
        <span class="dates">Jan 2022 – Present</span>
      </div>
      <ul>
        <li>Built and maintained real-time data pipelines processing 2M+ events daily.</li>
        <li>Reduced data warehouse query latency by 40% through optimization.</li>
      </ul>
    </div>
  </section>

  <section id="projects">
    <h2>Projects</h2>
    <div class="project">
      <h3><a href="https://github.com/janedoe/pipeline">Data Platform</a></h3>
      <p>Distributed ETL platform using Spark and Kafka.</p>
      <ul>
        <li>Implemented high-throughput stream processing engine.</li>
      </ul>
    </div>
  </section>

  <section id="education">
    <h2>Education</h2>
    <div class="degree">
      <h3>Bachelor of Science in Computer Science</h3>
      <div class="meta">
        <span class="institution">UC Berkeley</span>
        <span class="dates">2014 – 2018</span>
      </div>
    </div>
  </section>

  <section id="certifications">
    <h2>Certifications</h2>
    <ul>
      <li>AWS Certified Data Analytics — Specialty</li>
    </ul>
  </section>
</body>
</html>
"""


def test_parse_sample_template():
    parser = ResumeParser()
    data: ResumeData = parser.parse(SAMPLE_TEMPLATE_HTML)

    assert data.contact.name == "Jane Doe"
    assert data.contact.email == "jane@example.com"
    assert data.contact.phone == "(555) 123-4567"
    assert "janedoe" in (data.contact.linkedin or "")
    assert data.summary == "Experienced Data Engineer with 6 years building pipelines."

    assert len(data.skills) == 2
    assert data.skills[0].category == "Languages"
    assert "Python" in data.skills[0].skills

    assert len(data.experience) == 1
    exp = data.experience[0]
    assert exp.company == "Stripe"
    assert exp.title == "Senior Data Engineer"
    assert len(exp.bullets) == 2
    assert exp.bullets[0].id == "bullet_exp_01_01"
    assert exp.bullets[1].id == "bullet_exp_01_02"

    assert len(data.projects) == 1
    assert data.projects[0].name == "Data Platform"
    assert data.projects[0].url == "https://github.com/janedoe/pipeline"

    assert len(data.education) == 1
    assert "Computer Science" in data.education[0].degree
    assert data.education[0].institution == "UC Berkeley"

    assert len(data.certifications) == 1
    assert "AWS Certified" in data.certifications[0]


def test_parse_master_resume_file():
    parser = ResumeParser()
    data: ResumeData = parser.parse()

    assert data.contact.name == "Prasad Rawas"
    assert data.contact.email == "contactprasadrawas@gmail.com"
    assert data.contact.linkedin is not None
    assert len(data.summary) > 50
    assert len(data.skills) >= 5
    assert len(data.experience) >= 2
    assert len(data.projects) >= 5
    assert len(data.education) >= 1

    # Determinism check: parse twice and verify all bullet IDs are identical
    data2: ResumeData = parser.parse()
    first_run_ids = [b.id for exp in data.experience for b in exp.bullets]
    second_run_ids = [b.id for exp in data2.experience for b in exp.bullets]
    assert first_run_ids == second_run_ids


def test_load_preferences():
    prefs = load_preferences()
    assert len(prefs.target_roles) > 0
    assert len(prefs.locations) > 0
    assert prefs.max_listing_age_days > 0
