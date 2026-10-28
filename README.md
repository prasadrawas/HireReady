# HireReady — AI-Powered Resume Tailoring Pipeline

HireReady is a modular, deterministic Python pipeline that automates the job application preparation process. It takes your master HTML resume, scans job listings from major ATS platforms (Lever, Greenhouse, Ashby), performs two-pass scoring (fast keyword match + Gemini semantic analysis), tailors your resume for selected roles with strict evidence linking, generates ATS-friendly HTML and print-optimized PDF outputs, runs validation checks, and saves the direct application URL so you can review and apply manually.

---

## Core Principles

- **Single Source of Truth:** Your master resume (`input/master_resume.html`) is never modified.
- **Strict Evidence Linking:** Every tailored bullet traces back to a source bullet in the master resume via deterministic IDs (`bullet_{section}_{job_idx}_{bullet_idx}`).
- **No Hallucinations / No Fabrication:** Never invents metrics, percentages, tools, certifications, job titles, employers, or dates. Any unverified claim is moved to `NEEDS_REVIEW`.
- **Minimal LLM Invocations:** Google Gemini is used solely for semantic understanding and content rewriting. All parsing, scoring math, deduplication, HTML rendering, PDF generation, and validation are deterministic Python.
- **Configurable ATS Scanning:** Add or remove target companies directly via `config/ats_companies.json` without code changes.
- **Local JSON Tracking:** All application tracking uses structured JSON files (`data/seen_jobs.json`, `data/tracker.json`) — no database required.

---

## Tech Stack

| Concern | Tool |
|---|---|
| Language | Python 3.11+ (Python 3.12 recommended) |
| HTML Parsing | BeautifulSoup4 |
| HTML Templating | Jinja2 |
| PDF Extraction & Validation | PyMuPDF (`pymupdf`) |
| PDF Rendering | Playwright (Headless Chromium) |
| Schemas & Validation | Pydantic v2 |
| Settings Management | `pydantic-settings` + `python-dotenv` |
| LLM | Google Gemini (`google-genai` SDK) |
| HTTP Client | `httpx` (async support) |
| Configuration | YAML (`pyyaml`) + JSON |
| Testing | `pytest` + `pytest-asyncio` |

---

## Project Structure

```
HireReady/
├── main.py                           # CLI entry point (argparse)
├── requirements.txt                  # Python dependencies
├── .env.example                      # Template for environment variables
├── .env                              # User environment configuration
├── config/
│   ├── __init__.py
│   ├── settings.py                   # Pydantic settings (env vars, defaults)
│   └── ats_companies.json            # Configurable ATS company list
├── src/
│   ├── __init__.py
│   ├── models/                       # Pydantic data contracts
│   │   ├── __init__.py
│   │   ├── jd.py                     # JDAnalysis, Keyword
│   │   ├── resume.py                 # ResumeData, BulletPoint, Experience, etc.
│   │   ├── match.py                  # MatchReport, KeywordMatch, SectionRecommendation
│   │   ├── tailored.py               # TailoredResume, ChangeRecord
│   │   ├── job_listing.py            # JobListing, QuickScore, DeepScore
│   │   ├── preferences.py            # SearchPreferences
│   │   └── validation.py             # ValidationReport, CheckResult
│   ├── ats/                          # ATS API connectors & aggregator
│   │   ├── __init__.py
│   │   ├── base.py                   # Abstract ATS client base class
│   │   ├── lever.py                  # Lever API client
│   │   ├── greenhouse.py             # Greenhouse API client
│   │   ├── ashby.py                  # Ashby API client
│   │   └── aggregator.py             # Multi-source fetch, filter, dedup
│   ├── jd_parser.py                  # HTML, text, and PDF description extraction & cleaning
│   ├── jd_analyzer.py                # Gemini JD semantic analyzer
│   ├── resume_parser.py              # Master HTML resume parser with stable bullet IDs
│   ├── scorer.py                     # Two-pass scoring: deterministic quick score + Gemini deep score
│   ├── resume_matcher.py             # Keyword gap and coverage analysis
│   ├── resume_tailor.py              # Gemini resume tailoring with strict evidence linking
│   ├── html_generator.py             # Jinja2 HTML5 ATS resume generator
│   ├── pdf_generator.py              # Playwright print-to-PDF renderer
│   ├── ats_validator.py              # ATS validation checks with auto-overflow repair
│   ├── tracker.py                    # JSON application status tracker
│   └── llm_client.py                 # Google Gemini API wrapper with validation and retry
├── templates/
│   └── resume.html.j2                # ATS-compliant Jinja2 resume template
├── input/
│   ├── master_resume.html            # Your master resume (single source of truth)
│   └── preferences.yaml              # Job search criteria and preferences
├── output/                           # One directory per application ({company}_{role}_{id}/)
│   └── {company}_{role}_{id}/
│       ├── resume.html               # Tailored HTML resume
│       ├── resume.pdf                # Print-ready tailored PDF
│       ├── job_analysis.json         # Extracted JD keywords and qualifications
│       ├── match_report.json         # Match breakdown & coverage report
│       ├── change_summary.md         # Before/after bullet diffs & evidence citations
│       ├── validation_report.json    # ATS check results & keyword verification
│       └── application_url.txt       # Direct URL to apply manually
├── data/
│   ├── seen_jobs.json                # Scanned jobs cache and deduplication
│   └── tracker.json                  # Tracked application statuses
└── tests/                            # Comprehensive pytest test suite
```

---

## Installation & Setup

### 1. Clone & Create Virtual Environment

```bash
cd /Users/pr/fvm/HireReady

# Create Python 3.12 virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### 2. Configure Environment

Copy the example configuration:
```bash
cp .env.example .env
```

Edit `.env` and add your Google Gemini API key:
```env
GOOGLE_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.0-flash
```

*(Note: If `GOOGLE_API_KEY` is not provided, deterministic steps run normally while LLM steps employ conservative local fallbacks).*

### 3. Verify Setup

Run the setup validator:
```bash
python main.py setup
```

---

## CLI Usage Guide

### 1. Daily Scan & Selection

Scan all configured ATS boards (Lever, Greenhouse, Ashby):
```bash
python main.py scan
```

To automatically tailor the top N matches:
```bash
python main.py scan --auto-tailor-top 3
```

### 2. Tailoring From Previous Scan

Tailor specific jobs by rank number:
```bash
python main.py tailor 1,2,5
```

Tailor the top N matches from the last scan:
```bash
python main.py tailor --top 3
```

### 3. Direct Job Description Mode (Workday, Taleo, Portals)

When applying to companies without public ATS boards, pass the job description file directly (`.pdf`, `.txt`, `.html`):
```bash
python main.py tailor \
  --jd path/to/job_description.pdf \
  --company "Google" \
  --title "Senior Software Engineer" \
  --url "https://careers.google.com/jobs/123"
```

### 4. Application Management

List all tracked applications:
```bash
python main.py list
```

Filter applications by status:
```bash
python main.py list --status ready_for_review
```

Open the application page in your default browser:
```bash
python main.py apply google_senior-software-engineer_ef0499cd
```

Re-run validation on an existing output folder:
```bash
python main.py validate google_senior-software-engineer_ef0499cd
```

### 5. Managing ATS Target Companies & Links

HireReady supports fully configurable ATS job boards. You can supply job board URLs directly without needing to manually look up ATS platform types or slugs.

#### Option A: Quick CLI Add Link (Recommended)
Automatically detects the platform (Lever, Greenhouse, Ashby) and registers it:
```bash
python main.py add-link https://boards.greenhouse.io/airbnb
python main.py add-link https://jobs.lever.co/stripe --name "Stripe"
python main.py add-link https://jobs.ashbyhq.com/ramp
```

#### Option B: Paste URLs in `config/ats_companies.json`
You can configure `config/ats_companies.json` as a simple list of links:
```json
[
  "https://jobs.lever.co/stripe",
  "https://boards.greenhouse.io/airbnb",
  "https://job-boards.greenhouse.io/cloudflare",
  "https://jobs.ashbyhq.com/ramp"
]
```

Or as an object with a `"links"` list:
```json
{
  "links": [
    "https://jobs.lever.co/spotify",
    "https://boards.greenhouse.io/airbnb",
    {"url": "https://jobs.ashbyhq.com/ramp", "name": "Ramp"}
  ]
}
```

#### Option C: Categorized Format & Slug Commands
You can also manage companies by slug or categorize them under platform headers:
```bash
python main.py add-company stripe --ats lever --name "Stripe"
python main.py remove-company stripe --ats lever
```

---

## Output Artifacts

For each tailored job, a dedicated folder is created under `output/{company}_{role}_{id}/`:

1. **`resume.pdf`**: Print-ready, single-column, 1-2 page PDF generated via Playwright Chromium.
2. **`resume.html`**: Clean, semantic HTML5 resume.
3. **`change_summary.md`**: Markdown document containing before/after diffs for every altered bullet, evidence citations (`source_bullet_id`), keywords integrated, and any `NEEDS_REVIEW` items.
4. **`job_analysis.json`**: Structured requirements, critical/high keywords, and quotes extracted from the JD.
5. **`match_report.json`**: Coverage score, present/promotable/addable/gap keywords, and section recommendations.
6. **`validation_report.json`**: Results of 9 automated ATS checks (PDF text extractability, contact info, critical keywords, claim traceability, page count, etc.).
7. **`application_url.txt`**: Plain text file containing solely the direct URL to apply.

---

## Running Tests

Run the full pytest suite:
```bash
./venv/bin/pytest -v
```

Run tests for specific components:
```bash
./venv/bin/pytest tests/test_resume_parser.py -v
./venv/bin/pytest tests/test_ats_clients.py -v
./venv/bin/pytest tests/test_jd_parser.py -v
./venv/bin/pytest tests/test_scorer.py -v
./venv/bin/pytest tests/test_resume_matcher.py -v
./venv/bin/pytest tests/test_resume_tailor.py -v
./venv/bin/pytest tests/test_html_generator.py -v
./venv/bin/pytest tests/test_pdf_generator.py -v
./venv/bin/pytest tests/test_ats_validator.py -v
```

---

## Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| `GOOGLE_API_KEY not set` | Missing API key in `.env` | Add your Gemini key to `.env` |
| `master_resume.html not found` | Resume missing from input folder | Place your HTML resume in `input/master_resume.html` |
| `No jobs found after scan` | Preferences too restrictive | Check `input/preferences.yaml` target roles, locations, or companies exclude |
| `PDF page_count exceeds 2` | Large content overflowing page | Validator automatically retries with tighter margins; adjust `templates/resume.html.j2` if needed |
| `Playwright browser missing` | Chromium not downloaded | Run `./venv/bin/playwright install chromium` |
| `Garbled PDF text` | Font rendering issue | Web-safe and Inter Google fonts are loaded by default in `resume.html.j2` |
