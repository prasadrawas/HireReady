"""Unit tests for MongoDB document normalization, query builder, and ingestion."""

from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from src.db.mongo import build_mongo_query, is_mongo_configured, upsert_jobs_bulk
from src.db.normalizer import _extract_skills, normalize_job_for_db
from src.models.job_listing import JobListing
from src.services.job_query_service import JobQueryService


def test_extract_skills_canonical():
    text = "We are seeking a Senior Backend Engineer proficient in Python, FastAPI, and PostgreSQL with Docker & AWS."
    skills = _extract_skills(text)
    assert "Python" in skills
    assert "Postgresql" in skills or "PostgreSQL" in skills
    assert "Docker" in skills
    assert "Aws" in skills or "AWS" in skills


def test_normalize_job_for_db():
    job = JobListing(
        id="ashby_supabase_test123",
        ats_source="ashby",
        company="Supabase",
        company_slug="supabase",
        title="Staff Engineer, Database Infrastructure",
        location="Remote, US",
        locations=["Remote, US", "San Francisco, CA"],
        remote=True,
        workplace_type="Remote",
        employment_type="Full-time",
        experience_level="Lead",
        department="Engineering",
        team="Core DB",
        country="US",
        posted_date=date(2026, 10, 1),
        description_html="<p>Looking for a Postgres expert with Go and Kubernetes.</p>",
        description_text="Looking for a Postgres expert with Go and Kubernetes. Compensation: $180,000 - $220,000 USD/yr.",
        application_url="https://jobs.ashbyhq.com/supabase/test123",
        job_url="https://supabase.com/careers/test123",
        salary_raw="$180,000 - $220,000",
        has_equity=True,
        api_posting_id="test123",
    )

    doc = normalize_job_for_db(job)

    assert doc["_id"] == "ashby_supabase_test123"
    assert doc["ats_source"] == "ashby"
    assert doc["company"] == "Supabase"
    assert doc["remote"] is True
    assert doc["workplace_type"] == "Remote"
    assert "Remote, US" in doc["locations"]
    assert doc["has_equity"] is True
    assert doc["posted_date"] == "2026-10-01"

    # Salary structure
    salary = doc["salary"]
    assert salary["min"] == 180000
    assert salary["max"] == 220000
    assert salary["currency"] == "USD"

    # Skills extraction
    assert "Go" in doc["skills_extracted"] or "Golang" in doc["skills_extracted"]
    assert "Postgresql" in doc["skills_extracted"] or "PostgreSQL" in doc["skills_extracted"]
    assert "Kubernetes" in doc["skills_extracted"]


def test_build_mongo_query():
    # Empty query
    q_empty = build_mongo_query()
    assert q_empty == {}

    # Remote only
    q_remote = build_mongo_query(remote_only=True)
    assert q_remote == {"remote": True}

    # Platform & Company
    q_plat = build_mongo_query(platform="ashby", company="supabase")
    assert q_plat["ats_source"] == "ashby"
    assert q_plat["company_slug"] == "supabase"

    # Min salary
    q_salary = build_mongo_query(min_salary=150000)
    assert q_salary == {"salary.min": {"$gte": 150000}}

    # Search keyword
    q_search = build_mongo_query(search="postgres")
    assert "$or" in q_search
    assert len(q_search["$or"]) == 4


def test_upsert_jobs_bulk_mocked():
    mock_coll = MagicMock()
    mock_result = MagicMock()
    mock_result.upserted_count = 5
    mock_result.matched_count = 10
    mock_coll.bulk_write.return_value = mock_result

    jobs = [
        {"_id": f"job_{i}", "title": f"Title {i}", "company": "Acme"}
        for i in range(15)
    ]

    inserted, updated = upsert_jobs_bulk(jobs, collection=mock_coll)
    assert inserted == 5
    assert updated == 10
    assert mock_coll.bulk_write.called
    ops = mock_coll.bulk_write.call_args[0][0]
    assert len(ops) == 15


def test_job_query_service_fallback_when_mongo_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("src.services.job_query_service.is_mongo_configured", lambda: False)
    service = JobQueryService()
    res = service.get_jobs(page=1, page_size=10)
    assert "jobs" in res
    assert "total" in res
    assert res["source"] == "local_json"

