"""Unit tests for generic ATS client and aggregator."""

import json
from unittest.mock import AsyncMock, patch
import pytest

from src.ats.aggregator import ATSAggregator
from src.ats.generic_client import GenericATSClient, load_platform_configs
from src.models.job_listing import JobListing
from src.models.preferences import SearchPreferences


# --- Platform configs for testing ---

LEVER_PLATFORM_CONFIG = {
    "request": {
        "method": "GET",
        "url_template": "https://api.lever.co/v0/postings/{slug}?mode=json",
        "headers": {},
        "body": None,
    },
    "response": {
        "listings_path": "$",
        "id_field": "id",
        "title_field": "text",
        "description_html_field": "description",
        "description_text_field": "descriptionPlain",
        "location_field": "categories.location",
        "department_field": ["categories.department", "categories.team"],
        "remote_field": None,
        "posted_date_field": "createdAt",
        "date_format": "epoch_ms",
        "application_url_field": "applyUrl",
        "application_url_fallback": "https://jobs.lever.co/{slug}/{id}/apply",
        "extra_description_field": "additional",
    },
}

GREENHOUSE_PLATFORM_CONFIG = {
    "request": {
        "method": "GET",
        "url_template": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
        "headers": {},
        "body": None,
    },
    "response": {
        "listings_path": "$.jobs",
        "id_field": "id",
        "title_field": "title",
        "description_html_field": "content",
        "description_text_field": None,
        "location_field": "location.name",
        "department_field": "departments[0].name",
        "remote_field": None,
        "posted_date_field": "updated_at",
        "date_format": "iso",
        "application_url_field": "absolute_url",
        "application_url_fallback": "https://boards.greenhouse.io/{slug}/jobs/{id}",
        "extra_description_field": None,
    },
}

ASHBY_PLATFORM_CONFIG = {
    "request": {
        "method": "GET",
        "url_template": "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true",
        "headers": {},
        "body": None,
    },
    "response": {
        "listings_path": "$.jobs",
        "listings_path_fallback": ["$.postings", "$"],
        "id_field": "id",
        "title_field": "title",
        "description_html_field": "descriptionHtml",
        "description_text_field": "descriptionPlain",
        "location_field": ["locationName", "location"],
        "department_field": ["departmentName", "department"],
        "remote_field": "isRemote",
        "posted_date_field": ["publishedAt", "updatedAt"],
        "date_format": "iso",
        "application_url_field": ["applyUrl", "applicationUrl", "jobUrl"],
        "application_url_fallback": "https://jobs.ashbyhq.com/{slug}/{id}/application",
        "extra_description_field": None,
    },
}


# --- Fixtures ---

@pytest.fixture
def sample_lever_response():
    return [
        {
            "id": "lever-123",
            "text": "Senior Data Engineer",
            "description": "<p>We are seeking a Senior Data Engineer with Python experience.</p>",
            "descriptionPlain": "We are seeking a Senior Data Engineer with Python experience.",
            "categories": {
                "location": "San Francisco, CA",
                "team": "Data Platform",
                "commitment": "Full-time",
            },
            "applyUrl": "https://jobs.lever.co/stripe/lever-123/apply",
            "hostedUrl": "https://jobs.lever.co/stripe/lever-123",
            "createdAt": 1700000000000,
        }
    ]


@pytest.fixture
def sample_greenhouse_response():
    return {
        "jobs": [
            {
                "id": 456789,
                "title": "Staff Data Engineer",
                "content": "<p>Build data pipelines at scale.</p>",
                "location": {"name": "Remote, US"},
                "departments": [{"name": "Data Engineering"}],
                "absolute_url": "https://boards.greenhouse.io/gitlab/jobs/456789",
                "updated_at": "2026-10-15T12:00:00Z",
            }
        ]
    }


@pytest.fixture
def sample_ashby_response():
    return {
        "jobs": [
            {
                "id": "ashby-999",
                "title": "Data Platform Engineer",
                "descriptionHtml": "<p>Maintain Kafka and Spark infrastructure.</p>",
                "location": "New York, NY",
                "department": "Infrastructure",
                "isRemote": True,
                "applicationUrl": "https://jobs.ashbyhq.com/ramp/ashby-999/application",
                "publishedAt": "2026-10-20T08:00:00Z",
            }
        ]
    }


# --- Generic client tests ---

@pytest.mark.asyncio
async def test_generic_lever_client(sample_lever_response):
    client = GenericATSClient(
        platform_name="lever",
        platform_config=LEVER_PLATFORM_CONFIG,
        rate_limit_delay_seconds=0,
    )
    with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None
        mock_resp.json = lambda: sample_lever_response
        mock_get.return_value = mock_resp

        jobs = await client.fetch_jobs("stripe", "Stripe")
        assert len(jobs) == 1
        job = jobs[0]
        assert job.ats_source == "lever"
        assert job.company == "Stripe"
        assert job.title == "Senior Data Engineer"
        assert job.api_posting_id == "lever-123"
        assert job.application_url == "https://jobs.lever.co/stripe/lever-123/apply"
        assert "Python" in job.description_text
        assert job.department == "Data Platform"


@pytest.mark.asyncio
async def test_generic_greenhouse_client(sample_greenhouse_response):
    client = GenericATSClient(
        platform_name="greenhouse",
        platform_config=GREENHOUSE_PLATFORM_CONFIG,
        rate_limit_delay_seconds=0,
    )
    with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None
        mock_resp.json = lambda: sample_greenhouse_response
        mock_get.return_value = mock_resp

        jobs = await client.fetch_jobs("gitlab", "GitLab", force_refresh=True)
        assert len(jobs) == 1
        job = jobs[0]
        assert job.ats_source == "greenhouse"
        assert job.company == "GitLab"
        assert job.title == "Staff Data Engineer"
        assert job.remote is True
        assert job.department == "Data Engineering"
        assert job.application_url == "https://boards.greenhouse.io/gitlab/jobs/456789"


@pytest.mark.asyncio
async def test_generic_ashby_client(sample_ashby_response):
    client = GenericATSClient(
        platform_name="ashby",
        platform_config=ASHBY_PLATFORM_CONFIG,
        rate_limit_delay_seconds=0,
    )
    with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None
        mock_resp.json = lambda: sample_ashby_response
        mock_get.return_value = mock_resp

        jobs = await client.fetch_jobs("ramp", "Ramp", force_refresh=True)
        assert len(jobs) == 1
        job = jobs[0]
        assert job.ats_source == "ashby"
        assert job.company == "Ramp"
        assert job.title == "Data Platform Engineer"
        assert job.remote is True
        assert job.department == "Infrastructure"
        assert job.application_url == "https://jobs.ashbyhq.com/ramp/ashby-999/application"


@pytest.mark.asyncio
async def test_generic_client_with_custom_platform():
    """Test that a completely new ATS platform works via config only."""
    custom_config = {
        "request": {
            "method": "GET",
            "url_template": "https://api.customats.com/boards/{slug}/jobs",
            "headers": {},
            "body": None,
        },
        "response": {
            "listings_path": "$.results",
            "id_field": "jobId",
            "title_field": "jobTitle",
            "description_html_field": "htmlDescription",
            "description_text_field": None,
            "location_field": "city",
            "department_field": "team",
            "remote_field": "isFullyRemote",
            "posted_date_field": "postedOn",
            "date_format": "iso",
            "application_url_field": "applyLink",
            "application_url_fallback": "https://customats.com/{slug}/apply/{id}",
            "extra_description_field": None,
        },
    }

    fake_response = {
        "results": [
            {
                "jobId": "custom-001",
                "jobTitle": "ML Engineer",
                "htmlDescription": "<p>Build ML pipelines</p>",
                "city": "Austin, TX",
                "team": "AI/ML",
                "isFullyRemote": True,
                "postedOn": "2026-10-25T09:00:00Z",
                "applyLink": "https://customats.com/acme/apply/custom-001",
            }
        ]
    }

    client = GenericATSClient(
        platform_name="customats",
        platform_config=custom_config,
        rate_limit_delay_seconds=0,
    )
    with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None
        mock_resp.json = lambda: fake_response
        mock_get.return_value = mock_resp

        jobs = await client.fetch_jobs("acme", "Acme Corp")
        assert len(jobs) == 1
        job = jobs[0]
        assert job.ats_source == "customats"
        assert job.company == "Acme Corp"
        assert job.title == "ML Engineer"
        assert job.department == "AI/ML"
        assert job.remote is True
        assert job.application_url == "https://customats.com/acme/apply/custom-001"
        assert job.location == "Austin, TX"


def test_aggregator_preferences_filtering():
    aggregator = ATSAggregator()
    prefs = SearchPreferences(
        target_roles=["Senior Data Engineer"],
        target_keywords=["Python"],
        locations=["San Francisco"],
        remote_only=False,
        companies_exclude=["blacklist-inc"],
    )

    job1 = JobListing(
        id="job-1",
        ats_source="lever",
        company="Stripe",
        company_slug="stripe",
        title="Senior Data Engineer",
        location="San Francisco, CA",
        remote=False,
        description_html="<p>Python</p>",
        description_text="Python",
        application_url="https://jobs.lever.co/stripe/1/apply",
        api_posting_id="1",
    )

    job2_excluded = JobListing(
        id="job-2",
        ats_source="lever",
        company="Blacklist Inc",
        company_slug="blacklist-inc",
        title="Senior Data Engineer",
        location="San Francisco, CA",
        remote=False,
        description_html="<p>Python</p>",
        description_text="Python",
        application_url="https://jobs.lever.co/bl/2/apply",
        api_posting_id="2",
    )

    job3_wrong_role = JobListing(
        id="job-3",
        ats_source="lever",
        company="Stripe",
        company_slug="stripe",
        title="HR Specialist",
        location="San Francisco, CA",
        remote=False,
        description_html="<p>HR</p>",
        description_text="HR",
        application_url="https://jobs.lever.co/stripe/3/apply",
        api_posting_id="3",
    )

    assert aggregator._matches_preferences(job1, prefs) is True
    assert aggregator._matches_preferences(job2_excluded, prefs) is False
    assert aggregator._matches_preferences(job3_wrong_role, prefs) is False


def test_aggregator_deduplication():
    aggregator = ATSAggregator()
    job_gh = JobListing(
        id="job-gh",
        ats_source="greenhouse",
        company="Stripe",
        company_slug="stripe",
        title="Senior Data Engineer",
        location="San Francisco",
        description_html="<p>A</p>",
        description_text="A",
        application_url="https://boards.greenhouse.io/stripe/jobs/1",
        api_posting_id="1",
    )
    job_lever = JobListing(
        id="job-lever",
        ats_source="lever",
        company="Stripe",
        company_slug="stripe",
        title="Senior Data Engineer",
        location="San Francisco",
        description_html="<p>A</p>",
        description_text="A",
        application_url="https://jobs.lever.co/stripe/1/apply",
        api_posting_id="1",
    )

    deduped = aggregator._deduplicate([job_gh, job_lever])
    assert len(deduped) == 1
    # Check that the direct apply URL is preferred
    assert "apply" in deduped[0].application_url


def test_parse_ats_url():
    from src.ats.base import parse_ats_url

    # Lever
    res_lever = parse_ats_url("https://jobs.lever.co/spotify")
    assert res_lever == ("lever", "spotify", "Spotify")

    # Greenhouse boards
    res_gh = parse_ats_url("https://boards.greenhouse.io/airbnb")
    assert res_gh == ("greenhouse", "airbnb", "Airbnb")

    # Greenhouse modern job-boards
    res_gh2 = parse_ats_url("https://job-boards.greenhouse.io/cloudflare/")
    assert res_gh2 == ("greenhouse", "cloudflare", "Cloudflare")

    # Greenhouse embed query
    res_gh3 = parse_ats_url("https://boards.greenhouse.io/embed/job_board?for=hashicorp")
    assert res_gh3 == ("greenhouse", "hashicorp", "Hashicorp")

    # Ashby
    res_ashby = parse_ats_url("https://jobs.ashbyhq.com/linear", custom_name="Linear App")
    assert res_ashby == ("ashby", "linear", "Linear App")

    # Unknown
    assert parse_ats_url("https://example.com/careers") is None
    assert parse_ats_url("") is None


def test_aggregator_normalize_config():
    aggregator = ATSAggregator()

    # Case A: Top-level list of URLs
    config_list = [
        "https://jobs.lever.co/stripe",
        "https://boards.greenhouse.io/airbnb",
        "https://jobs.ashbyhq.com/ramp",
    ]
    normalized_a = aggregator._normalize_config(config_list)
    assert len(normalized_a["lever"]["companies"]) == 1
    assert normalized_a["lever"]["companies"][0]["slug"] == "stripe"
    assert len(normalized_a["greenhouse"]["companies"]) == 1
    assert normalized_a["greenhouse"]["companies"][0]["slug"] == "airbnb"
    assert len(normalized_a["ashby"]["companies"]) == 1
    assert normalized_a["ashby"]["companies"][0]["slug"] == "ramp"

    # Case B: Object with 'links' key
    config_links = {
        "links": [
            "https://jobs.lever.co/spotify",
            {"url": "https://boards.greenhouse.io/gitlab", "name": "GitLab Inc"},
        ]
    }
    normalized_b = aggregator._normalize_config(config_links)
    assert len(normalized_b["lever"]["companies"]) == 1
    assert normalized_b["lever"]["companies"][0]["slug"] == "spotify"
    assert len(normalized_b["greenhouse"]["companies"]) == 1
    assert normalized_b["greenhouse"]["companies"][0]["slug"] == "gitlab"
    assert normalized_b["greenhouse"]["companies"][0]["name"] == "GitLab Inc"


def test_generic_client_field_resolution():
    """Test dot notation, array index, and fallback field resolution."""
    client = GenericATSClient(
        platform_name="test",
        platform_config={"request": {}, "response": {}},
        rate_limit_delay_seconds=0,
    )

    data = {
        "title": "Engineer",
        "location": {"name": "NYC", "country": "US"},
        "departments": [{"name": "Engineering"}, {"name": "Data"}],
        "tags": ["python", "sql"],
    }

    # Simple key
    assert client._resolve_path(data, "title") == "Engineer"

    # Dot notation
    assert client._resolve_path(data, "location.name") == "NYC"

    # Array index
    assert client._resolve_path(data, "departments[0].name") == "Engineering"
    assert client._resolve_path(data, "departments[1].name") == "Data"

    # Missing path
    assert client._resolve_path(data, "nonexistent.field") is None
    assert client._resolve_path(data, "departments[5].name") is None

    # Fallback list
    assert client._get_field(data, ["missing", "also_missing", "title"]) == "Engineer"
    assert client._get_field(data, ["missing"]) is None
    assert client._get_field(data, None) is None


@pytest.mark.asyncio
async def test_rippling_client_with_detail():
    """Test Rippling client fetching list + detail, combining company and role description, and extracting payRangeDetails."""
    configs = load_platform_configs()
    rippling_cfg = configs["rippling"]
    client = GenericATSClient(
        platform_name="rippling",
        platform_config=rippling_cfg,
        rate_limit_delay_seconds=0,
    )

    list_response = {
        "items": [
            {
                "id": "rip-job-1",
                "name": "Senior Product Designer",
                "url": "https://ats.rippling.com/rippling/jobs/rip-job-1",
                "department": {"name": "Design"},
                "locations": [
                    {
                        "name": "San Francisco, CA",
                        "country": "United States",
                        "workplaceType": "HYBRID",
                    }
                ],
            }
        ]
    }

    detail_response = {
        "uuid": "rip-job-1",
        "name": "Senior Product Designer",
        "description": {
            "company": "<p>About Rippling: Building the future of workforce management.</p>",
            "role": "<p>Responsibilities: Design intuitive employee workflows.</p>",
        },
        "workLocations": ["San Francisco, CA", "New York, NY"],
        "employmentType": {"id": "Salaried, full-time", "label": "SALARIED_FT"},
        "payRangeDetails": [
            {
                "location": "US",
                "currency": "USD",
                "frequency": "YEAR",
                "rangeStart": 180000.0,
                "rangeEnd": 230000.0,
            }
        ],
        "createdOn": "2026-06-15T10:00:00Z",
    }

    from unittest.mock import MagicMock

    async def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = lambda: None
        if "rip-job-1" in url:
            resp.json = lambda: detail_response
        else:
            resp.json = lambda: list_response
        return resp

    with patch.object(client.client, "get", side_effect=mock_get):
        jobs = await client.fetch_jobs("rippling", "Rippling", force_refresh=True)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior Product Designer"
    assert job.ats_source == "rippling"
    assert "About Rippling" in job.description_html
    assert "Responsibilities: Design intuitive employee workflows" in job.description_html
    assert job.workplace_type == "Hybrid"
    assert job.employment_type == "Full-time"
    assert "San Francisco, CA" in job.locations
    assert "New York, NY" in job.locations
    assert job.salary_raw is not None

    # Test salary extraction
    from src.salary_extractor import SalaryExtractor
    salary = SalaryExtractor.extract(job.description_text, job.metadata)
    assert salary.min_salary == 180000
    assert salary.max_salary == 230000
    assert salary.display == "$180K-$230K"


@pytest.mark.asyncio
async def test_ats_prefiltering_and_cache(tmp_path):
    """Test that pre-filtering reduces detail calls and TTL caching avoids repeat network requests."""
    from unittest.mock import MagicMock, PropertyMock
    from src.models.preferences import SearchPreferences
    from config.settings import settings

    configs = load_platform_configs()
    rippling_cfg = configs["rippling"]
    client = GenericATSClient(
        platform_name="rippling",
        platform_config=rippling_cfg,
        rate_limit_delay_seconds=0,
    )

    list_response = {
        "items": [
            {"id": "job-sales", "name": "Account Executive", "url": "https://example.com/1"},
            {"id": "job-data", "name": "Senior Data Engineer", "url": "https://example.com/2"},
            {"id": "job-legal", "name": "Corporate Counsel", "url": "https://example.com/3"},
        ]
    }
    data_detail = {
        "uuid": "job-data",
        "name": "Senior Data Engineer",
        "description": {"company": "Company intro", "role": "Build ETL pipelines"},
        "locations": [{"name": "Remote", "workplaceType": "REMOTE"}],
        "workLocations": ["Remote"],
    }

    detail_calls = []

    async def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = lambda: None
        if "job-data" in url:
            detail_calls.append(url)
            resp.json = lambda: data_detail
        elif "job-sales" in url or "job-legal" in url:
            detail_calls.append(url)
            resp.json = lambda: {"uuid": "unmatched", "description": {}}
        else:
            resp.json = lambda: list_response
        return resp

    prefs = SearchPreferences(target_roles=["Data Engineer"])

    with patch.object(type(settings), "ats_cache_dir", new_callable=PropertyMock, return_value=tmp_path), patch.object(client.client, "get", side_effect=mock_get) as net_mock:
        # First call with target role preferences
        jobs = await client.fetch_jobs("testco", "TestCo", preferences=prefs)

        # Pre-filter should ONLY have called detail for job-data, NOT job-sales or job-legal
        assert len(jobs) == 1
        assert jobs[0].title == "Senior Data Engineer"
        assert len(detail_calls) == 1
        assert "job-data" in detail_calls[0]

        # Second call should load from disk cache without additional list network request
        call_count_before = net_mock.call_count
        jobs_cached = await client.fetch_jobs("testco", "TestCo", preferences=prefs)
        assert len(jobs_cached) == 1
        # Net mock should not have been called for list URL again
        assert net_mock.call_count == call_count_before


