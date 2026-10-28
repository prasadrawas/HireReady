#!/usr/bin/env python3
"""HireReady — AI-Powered Resume Tailoring Pipeline CLI."""

import argparse
import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import sys
import webbrowser

from config.settings import settings
from src.ats.aggregator import ATSAggregator
from src.ats.base import generate_job_id, parse_ats_url, slugify
from src.ats_validator import ATSValidator
from src.cover_letter_generator import CoverLetterGenerator
from src.html_generator import HTMLGenerator
from src.jd_analyzer import JDAnalyzer
from src.jd_parser import JDParser
from src.job_alerts import JobAlertManager, generate_cron_command
from src.linkedin_detector import LinkedInDetector
from src.models.job_listing import DeepScore, JobListing, QuickScore
from src.models.preferences import SearchPreferences
from src.models.resume import ResumeData
from src.pdf_generator import PDFGenerator
from src.resume_matcher import ResumeMatcher
from src.resume_parser import ResumeParser, load_preferences
from src.resume_tailor import ResumeTailor
from src.company_research import CompanyResearcher
from src.red_flag_detector import RedFlagDetector
from src.role_suggester import RoleSuggester
from src.salary_extractor import SalaryExtractor
from src.tracker import ApplicationTracker

# Configure quiet logging: suppress third-party network and SDK noise
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.WARNING), format="%(message)s")
for noisy in ("httpx", "httpcore", "urllib3", "asyncio", "playwright", "google", "google_genai", "google.genai"):
    logging.getLogger(noisy).setLevel(logging.ERROR)
logger = logging.getLogger("hireready")


def run_setup(args):
    """Validate master resume, preferences, and ATS configuration."""
    print("=" * 60)
    print("HireReady — System Setup & Configuration Check")
    print("=" * 60)

    # 1. Check Master Resume
    resume_path = settings.master_resume_path
    if not resume_path.exists():
        print(f"❌ Master resume NOT found at: {resume_path}")
        print("   Please place your HTML resume at input/master_resume.html")
        return 1
    try:
        parser = ResumeParser(resume_path)
        resume: ResumeData = parser.parse()
        print(f"✅ Master Resume: Valid ({resume.contact.name}, {len(resume.experience)} jobs, {len(resume.skills)} skill groups)")
    except Exception as e:
        print(f"❌ Master Resume parsing failed: {e}")
        return 1

    # 2. Check Preferences
    pref_path = settings.preferences_path
    if not pref_path.exists():
        print(f"❌ Preferences file NOT found at: {pref_path}")
        return 1
    try:
        prefs: SearchPreferences = load_preferences(pref_path)
        print(f"✅ Job Preferences: Valid ({len(prefs.target_roles)} target roles, {len(prefs.locations)} locations)")
    except Exception as e:
        print(f"❌ Preferences validation failed: {e}")
        return 1

    # 3. Check ATS Companies Config
    ats_path = settings.ats_companies_path
    if not ats_path.exists():
        print(f"❌ ATS configuration NOT found at: {ats_path}")
        return 1
    try:
        aggregator = ATSAggregator()
        normalized_cfg = aggregator._load_config()
        total_companies = sum(len(c.get("companies", [])) for c in normalized_cfg.values())
        print(f"✅ ATS Config: Valid ({total_companies} companies configured)")
    except Exception as e:
        print(f"❌ ATS config validation failed: {e}")
        return 1

    # 4. Check Google Gemini API Key
    if not settings.google_api_key:
        print("⚠️  GOOGLE_API_KEY: Not set in .env (Deterministic steps will work; Gemini steps will use conservative fallbacks)")
    else:
        print(f"✅ Google Gemini: Configured (Model: {settings.gemini_model})")

    print("\nAll setup checks passed! Run `python main.py scan` to begin scanning.")
    return 0


def run_scan(args):
    """Scan configured ATS platforms, score, rank, and optionally tailor jobs."""
    selected_jobs, resume = asyncio.run(_async_scan(args))
    if selected_jobs and resume:
        tailor_selected_jobs(selected_jobs, resume, cover_letter=getattr(args, "cover_letter", False))


async def _async_scan(args) -> tuple[list[JobListing], ResumeData | None]:
    # Step 1: Load resume and preferences
    try:
        resume = ResumeParser().parse()
        prefs = load_preferences()
    except Exception as e:
        print(f"❌ Error loading setup: {e}. Run `python main.py setup` first.")
        return [], None

    print("=" * 80)
    print("🚀 HireReady — ATS Job Scanner")
    print("=" * 80)

    aggregator = ATSAggregator()
    from src.ats.generic_client import load_platform_configs
    platform_names = list(load_platform_configs().keys())
    enabled_names = [p for p in platform_names if True]  # all loaded platforms
    print(f"\n[1/4] 🔍 Scanning configured ATS platforms ({', '.join(n.capitalize() for n in enabled_names)})...")
    new_jobs, stats = await aggregator.fetch_all(prefs)

    for ats_name in platform_names:
        if ats_name in stats and stats[ats_name] > 0:
            print(f"      • {ats_name.capitalize():<16}: {stats[ats_name]} listings fetched")

    total_fetched = stats.get("total_fetched", 0)
    after_filters = stats.get("after_filters", 0)
    print(f"      Summary: {total_fetched:,} total fetched | {after_filters:,} matched your preferences | {len(new_jobs):,} new")

    # Determine which jobs to score: prefer new_jobs, fall back to matching_jobs
    jobs_to_process = new_jobs if new_jobs else stats.get("matching_jobs", [])

    if not jobs_to_process:
        print("\nℹ️  No job listings found matching your target roles and preferences.")
        print("💡 Tip: Review your target roles or locations in input/preferences.yaml,")
        print("   or add more company boards: python main.py add-link <url>\n")
        return [], None

    # Step 2: Quick scoring
    if new_jobs:
        print(f"\n[2/4] ⚡ Quick scoring {len(new_jobs)} new listings against resume...", end="", flush=True)
    else:
        print(f"\n[2/4] ⚡ Evaluating {len(jobs_to_process)} matched listings against resume...", end="", flush=True)

    from src.scorer import Scorer
    scorer = Scorer()
    scored_pairs = scorer.rank_quick(jobs_to_process, resume, prefs)
    print(" done")

    # Build quick score lookup
    quick_score_map = {job.id: qscore for job, qscore in scored_pairs}

    # All jobs that passed quick score threshold
    all_passing = [job for job, qscore in scored_pairs if qscore.pass_to_deep_scoring]
    if not all_passing:
        all_passing = [job for job, _ in scored_pairs]

    # Pick top N for Gemini deep scoring
    candidates_for_deep = all_passing[:settings.max_deep_score_candidates]
    print(f"      • {len(all_passing)} jobs passed threshold, {len(candidates_for_deep)} selected for deep scoring")

    # Step 3: Deep scoring with Gemini (only top N)
    print(f"\n[3/4] 🧠 Deep scoring top {len(candidates_for_deep)} with Gemini...", end="", flush=True)
    deep_scores = scorer.deep_score_batch(candidates_for_deep, resume)
    print(" done")

    # Build deep score map from Gemini results
    deep_score_map: dict[str, DeepScore] = {}
    for ds in deep_scores:
        if ds.semantic_match == 0.5 and ds.key_gaps and "Gemini API unavailable" in ds.key_gaps[0]:
            qs = quick_score_map.get(ds.job_id)
            if qs:
                ds.semantic_match = qs.composite_score
                ds.role_fit = f"Scored by keyword matching (Gemini unavailable). Title: {qs.title_match:.0%}, overlap: {qs.keyword_overlap:.0%}"
        deep_score_map[ds.job_id] = ds

    # For jobs NOT sent to Gemini, use their quick score as the display score
    for job in all_passing:
        if job.id not in deep_score_map:
            qs = quick_score_map.get(job.id)
            if qs:
                deep_score_map[job.id] = DeepScore(
                    job_id=job.id,
                    semantic_match=qs.composite_score,
                    role_fit=f"Quick score: title {qs.title_match:.0%}, keywords {qs.keyword_overlap:.0%}, seniority {qs.seniority_match:.0%}",
                    key_gaps=[],
                    recommendation="good_match" if qs.composite_score >= 0.6 else "weak_match",
                )

    # Rank ALL passing jobs (Gemini-scored first, then quick-scored)
    ranked_jobs = sorted(
        all_passing,
        key=lambda j: (-deep_score_map.get(j.id, DeepScore(job_id=j.id, semantic_match=0.0, role_fit="", key_gaps=[], recommendation="skip")).semantic_match, j.company.lower(), j.title.lower()),
    )

    # Save scores in seen_jobs.json
    seen_jobs = aggregator._load_seen_jobs()
    for job in ranked_jobs:
        if job.id in seen_jobs:
            ds = deep_score_map.get(job.id)
            seen_jobs[job.id].update({
                "deep_score": ds.semantic_match if ds else None,
                "recommendation": ds.recommendation if ds else None,
                "status": "scored",
                "updated_at": datetime.now().isoformat(),
            })
    aggregator.save_seen_jobs(seen_jobs)

    # Cache ALL ranked jobs (not just top 30)
    last_scan_cache = {
        "jobs": [j.model_dump(mode="json") for j in ranked_jobs],
        "deep_scores": {k: v.model_dump(mode="json") for k, v in deep_score_map.items()},
    }
    (settings.data_dir / "last_scan.json").write_text(json.dumps(last_scan_cache, indent=2, default=str), encoding="utf-8")

    # Extract salary and red flags for each job
    salary_map: dict[str, str] = {}
    red_flag_map: dict[str, int] = {}
    for job in ranked_jobs:
        salary = SalaryExtractor.extract(job.description_text, job.metadata)
        salary_map[job.id] = salary.display
        flags = RedFlagDetector.scan(job.description_text, job.title)
        red_flag_map[job.id] = len(flags)

    # Step 4: Display top matches
    print("\n" + "=" * 110)
    print("🎯 Top Matching Roles")
    print("=" * 110)
    print(f"  {'#':<3} | {'Company':<14} | {'Role':<24} | {'Match':<5} | {'Gaps':<4} | {'Salary':<14} | {'Flags':<5} | {'Apply URL'}")
    print(f"  {'-'*3}-+-{'-'*14}-+-{'-'*24}-+-{'-'*5}-+-{'-'*4}-+-{'-'*14}-+-{'-'*5}-+-{'-'*20}")

    for idx, job in enumerate(ranked_jobs[:15], start=1):
        ds = deep_score_map.get(job.id)
        match_pct = f"{int((ds.semantic_match if ds else 0.5) * 100)}%"
        gaps_count = str(len(ds.key_gaps)) if ds else "0"
        salary_disp = salary_map.get(job.id, "Not listed")[:14]
        flag_count = red_flag_map.get(job.id, 0)
        flag_disp = f"⚠ {flag_count}" if flag_count > 0 else "✓"
        url_snippet = (job.application_url[:20] + "...") if len(job.application_url) > 20 else job.application_url
        print(f"  {idx:<3} | {job.company:<14} | {job.title[:24]:<24} | {match_pct:<5} | {gaps_count:<4} | {salary_disp:<14} | {flag_disp:<5} | {url_snippet}")
    print("=" * 110)

    # Show role suggestions
    prefs = load_preferences()
    seen_titles = [job.title for job in ranked_jobs]
    role_suggestions = RoleSuggester.suggest(prefs.target_roles, seen_titles)
    if role_suggestions["total_suggestions"] > 0:
        print("\n  💡 Role suggestions — you might also search for:")
        for s in role_suggestions["family_suggestions"][:5]:
            print(f"     + \"{s['title']}\" ({s['reason']})")
        for s in role_suggestions["scan_suggestions"][:3]:
            print(f"     + \"{s['title']}\" (seen {s['seen_count']}x in results)")
        print(f"     Add to input/preferences.yaml → target_roles")

    # Send desktop alerts for high-match jobs
    alert_mgr = JobAlertManager()
    alert_jobs = [
        {
            "job_id": job.id,
            "company": job.company,
            "title": job.title,
            "score": deep_score_map.get(job.id, DeepScore(job_id=job.id, semantic_match=0.5, role_fit="", key_gaps=[], recommendation="skip")).semantic_match,
            "application_url": job.application_url,
        }
        for job in ranked_jobs[:15]
    ]
    alerted = alert_mgr.send_alerts(alert_jobs, min_score=0.75)
    if alerted:
        print(f"\n  📬 Desktop alert sent for {len(alerted)} high-match job(s)")

    # Step 5: Selection
    selected_indices = []
    if getattr(args, "auto_tailor_top", None):
        top_n = int(args.auto_tailor_top)
        selected_indices = list(range(1, min(top_n, len(ranked_jobs)) + 1))
        print(f"\nAuto-tailoring top {top_n} job(s)...")
    else:
        try:
            choice = input('\n[4/4] Select jobs to tailor (e.g. "1,2", "top 3", "all", or Enter to exit): ').strip()
            selected_indices = parse_selection_input(choice, len(ranked_jobs))
        except (EOFError, KeyboardInterrupt):
            print("\n✨ Scan completed.")
            return [], None

    if not selected_indices:
        print("\n✨ Scan complete. Run `python main.py tailor 1,2` anytime to tailor matches.\n")
        return [], None

    selected_jobs = [ranked_jobs[i - 1] for i in selected_indices if 1 <= i <= len(ranked_jobs)]
    return selected_jobs, resume


def parse_selection_input(choice: str, total_available: int) -> list[int]:
    """Parse user selection string (e.g. '1,2', 'top 3', 'all')."""
    choice = choice.strip().lower()
    if not choice:
        return []
    if choice == "all":
        return list(range(1, total_available + 1))
    if choice.startswith("top"):
        parts = choice.split()
        if len(parts) >= 2 and parts[1].isdigit():
            n = int(parts[1])
            return list(range(1, min(n, total_available) + 1))
    indices = []
    for part in choice.split(","):
        part = part.strip()
        if part.isdigit():
            indices.append(int(part))
    return indices


def tailor_selected_jobs(jobs: list[JobListing], resume: ResumeData, cover_letter: bool = False):
    """Execute steps (JD analysis, match, tailor, HTML, PDF, validate) on jobs."""
    results_summary = []
    tracker = ApplicationTracker()
    html_gen = HTMLGenerator()
    pdf_gen = PDFGenerator()
    analyzer = JDAnalyzer()
    matcher = ResumeMatcher()
    tailor = ResumeTailor()
    validator = ATSValidator(pdf_generator=pdf_gen)
    cover_letter_gen = CoverLetterGenerator()
    company_researcher = CompanyResearcher()

    generate_cover_letters = cover_letter

    for job in jobs:
        print("\n" + "-" * 70)
        print(f"🎯 Tailoring Resume for: {job.company} — {job.title}")
        print(f"   Destination: output/{job.id}/")
        print("-" * 70)
        output_folder = settings.output_dir / job.id
        output_folder.mkdir(parents=True, exist_ok=True)

        # 1+2. Combined JD Analysis + Resume Tailoring (SINGLE Gemini call)
        print("  [1/8] 📋 Analyzing JD + tailoring resume (Gemini).", end="", flush=True)
        jd_analysis, tailored = tailor.analyze_and_tailor(
            resume=resume,
            job_description=job.description_text or job.description_html,
            job_id=job.id,
            company=job.company,
            job_title=job.title,
            application_url=job.application_url,
            output_dir=output_folder,
        )
        crit_count = sum(1 for k in jd_analysis.keywords if k.category == "critical")
        rewritten_c = sum(1 for c in tailored.changes if c.change_type == "rewrite")
        reordered_c = sum(1 for c in tailored.changes if c.change_type == "reorder")
        flagged_c = len(tailored.needs_review)
        print(f" done ({len(jd_analysis.keywords)} keywords, {rewritten_c} rewritten)")

        # 2. Matching resume to JD (deterministic — no Gemini)
        print("  [2/8] 🔍 Computing match report..................", end="", flush=True)
        match_report = matcher.match(jd_analysis, resume, output_dir=output_folder)
        cov_pct = int(match_report.coverage_score * 100)
        print(f" done ({cov_pct}% coverage)")

        # 3. Generating HTML
        print("  [3/8] 📄 Generating ATS-friendly HTML..........", end="", flush=True)
        html_file = output_folder / "resume.html"
        html_gen.generate(tailored, target_role=job.title, output_path=html_file)
        print(" done (resume.html)")

        # 4. Exporting PDF
        print("  [4/8] 🖨️  Compiling print-ready PDF............", end="", flush=True)
        pdf_file = output_folder / "resume.pdf"
        pdf_gen.generate_pdf(html_path=html_file, pdf_path=pdf_file)
        print(" done (resume.pdf)")

        # 5. Validating
        print("  [5/8] ✅ Running 9 automated ATS checks........", end="", flush=True)
        val_report = validator.validate(
            pdf_path=pdf_file,
            html_path=html_file,
            tailored_resume=tailored,
            master_resume=resume,
            jd_analysis=jd_analysis,
            output_dir=output_folder,
        )
        val_status = "All checks passed ✅" if val_report.passed else f"Passed with {len(val_report.warnings)} warnings ⚠️"
        print(f" done ({val_status})")

        # 6. Red Flag Scan (no Gemini)
        print("  [6/8] 🚩 Scanning JD for red flags............", end="", flush=True)
        red_flags = RedFlagDetector.scan(job.description_text, job.title)
        flag_summary = RedFlagDetector.summarize(red_flags)
        (output_folder / "red_flags.json").write_text(json.dumps(flag_summary, indent=2), encoding="utf-8")
        if red_flags:
            print(f" done ({flag_summary['critical']} critical, {flag_summary['warnings']} warnings — {flag_summary['verdict']})")
        else:
            print(" done (clean — no red flags)")

        # 7. Company Research (Gemini — cached per company)
        print("  [7/8] 🏢 Researching company...................", end="", flush=True)
        company_brief = company_researcher.research(job.company, job.title, job.description_text, output_dir=output_folder)
        verdict = company_brief.get("verdict", "unknown")
        stage = company_brief.get("stage", "Unknown")
        was_cached = company_researcher.cache.get(job.company) is not None
        cache_label = "cached" if was_cached else "Gemini"
        print(f" done ({stage} — {verdict}) [{cache_label}]")

        # Cover letter — only if --cover-letter flag was passed
        cl_result = {"body": ""}
        if generate_cover_letters:
            print("  [+] 📝 Generating cover letter (Gemini)........", end="", flush=True)
            cl_result = cover_letter_gen.generate(resume, jd_analysis, match_report, output_dir=output_folder)
            cl_words = len(cl_result.get("body", "").split())
            print(f" done ({cl_words} words)")

        # 8. LinkedIn & Salary (no Gemini)
        print("  [8/8] 🔗 Extracting salary & LinkedIn info.....", end="", flush=True)
        salary = SalaryExtractor.extract(job.description_text, job.metadata)
        linkedin_info = LinkedInDetector.get_linkedin_info(job.company, job.title, job.description_text)

        # Save application URLs file (ATS + LinkedIn)
        url_lines = [
            f"ATS Apply: {job.application_url.strip()}",
            f"LinkedIn Easy Apply: {linkedin_info['linkedin_easy_apply_search']}",
            f"LinkedIn Search: {linkedin_info['linkedin_job_search']}",
        ]
        if linkedin_info.get("linkedin_direct_url"):
            url_lines.append(f"LinkedIn Direct: {linkedin_info['linkedin_direct_url']}")
        (output_folder / "application_url.txt").write_text("\n".join(url_lines) + "\n", encoding="utf-8")

        # Save salary info
        (output_folder / "salary_info.json").write_text(
            json.dumps(salary.to_dict(), indent=2), encoding="utf-8"
        )
        print(f" done (Salary: {salary.display})")

        # Record in application tracker
        final_status = "ready_for_review" if val_report.passed else "validation_failed"
        tracker.record_application(
            job_id=job.id,
            company=job.company,
            title=job.title,
            application_url=job.application_url,
            output_dir=output_folder,
            coverage_score=match_report.coverage_score,
            validation_passed=val_report.passed,
            needs_review_count=len(tailored.needs_review),
            status=final_status,
            salary=salary.display,
            linkedin_url=linkedin_info["linkedin_easy_apply_search"],
        )

        results_summary.append({
            "job": job,
            "coverage": cov_pct,
            "pdf_path": pdf_file,
            "rewritten": rewritten_c,
            "reordered": reordered_c,
            "flagged": flagged_c,
            "salary": salary.display,
            "linkedin_url": linkedin_info["linkedin_easy_apply_search"],
            "red_flags": flag_summary,
            "company_verdict": verdict,
        })

    # Print terminal summary
    print("\n" + "=" * 80)
    print("🎉 Application Package(s) Ready for Review")
    print("=" * 80)
    for res in results_summary:
        j = res["job"]
        flagged_str = f" | ⚠️  {res['flagged']} item(s) need review" if res["flagged"] > 0 else ""
        rf = res.get("red_flags", {})
        rf_str = ""
        if rf.get("total", 0) > 0:
            rf_str = f" | 🚩 {rf['critical']} critical, {rf['warnings']} warnings ({rf['verdict']})"
        print(f"\n  🏢 {j.company} — {j.title}")
        print(f"     Match:    {res['coverage']}%")
        print(f"     Salary:   {res.get('salary', 'Not listed')}")
        print(f"     Company:  {res.get('company_verdict', 'unknown')}")
        print(f"     Resume:   {res['pdf_path']}")
        cover_file = res['pdf_path'].parent / 'cover_letter.txt'
        if cover_file.exists():
            print(f"     Cover:    {cover_file}")
        else:
            print(f"     Cover:    (skipped — use --cover-letter to generate)")
        print(f"     Brief:    {res['pdf_path'].parent / 'company_brief.md'}")
        print(f"     Changes:  {res['rewritten']} rewritten, {res['reordered']} reordered{flagged_str}{rf_str}")
        print(f"     Apply:    {j.application_url}")
        print(f"     LinkedIn: {res.get('linkedin_url', 'N/A')}")

    # Show pending follow-ups
    tracker = ApplicationTracker()
    pending = tracker.get_pending_followups()
    if pending:
        print(f"\n  📬 You have {len(pending)} pending follow-up(s):")
        for fu in pending[:5]:
            print(f"     - {fu['company']} — {fu['title']} (due {fu['followup_date']})")

    print("\n" + "=" * 80)
    print("💡 Next steps:")
    print("   python main.py apply <job_id>        — Open the application URL")
    print("   python main.py submit <job_id>       — Mark as submitted + set follow-up reminders")
    print("   python main.py stage <job_id> <stage> — Log an interview stage")
    print("   python main.py followups             — View pending follow-ups")
    print("   python main.py cron                  — Get cron command for daily scanning")
    print("=" * 80 + "\n")


def run_tailor_cli(args):
    """Tailor jobs by selection numbers, top N, or direct JD file."""
    # Direct JD input mode
    if getattr(args, "jd", None):
        run_direct_jd(args)
        return

    # Selection mode from last scan
    last_scan_file = settings.data_dir / "last_scan.json"
    if not last_scan_file.exists():
        print("No previous scan found. Please run `python main.py scan` first.")
        return

    with open(last_scan_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = [JobListing.model_validate(j) for j in data.get("jobs", [])]
    if not jobs:
        print("No jobs found in previous scan.")
        return

    selected_indices = []
    if getattr(args, "top", None):
        selected_indices = list(range(1, min(int(args.top), len(jobs)) + 1))
    elif getattr(args, "targets", None):
        selected_indices = parse_selection_input(args.targets, len(jobs))

    if not selected_indices:
        print("No valid jobs specified. Example: `python main.py tailor 1,2` or `python main.py tailor --top 3`")
        return

    resume = ResumeParser().parse()
    selected_jobs = [jobs[i - 1] for i in selected_indices if 1 <= i <= len(jobs)]
    tailor_selected_jobs(selected_jobs, resume, cover_letter=getattr(args, "cover_letter", False))


def run_direct_jd(args):
    """Process a direct JD file (PDF or text) for companies not on Lever/Greenhouse/Ashby."""
    jd_path = Path(args.jd)
    if not jd_path.exists():
        print(f"Error: JD file not found at: {jd_path}")
        return

    company = args.company or "DirectCompany"
    title = args.title or "Software Engineer"
    apply_url = args.url or "MANUAL — no URL provided"

    print(f"Loading direct JD from: {jd_path}")
    raw_text = JDParser.extract_from_file(jd_path)
    if not raw_text:
        print("Error: Could not extract text from JD file.")
        return

    job_id = generate_job_id(company, title, f"direct-{Path(jd_path).stem}")
    job = JobListing(
        id=job_id,
        ats_source="direct",
        company=company,
        company_slug=slugify(company),
        title=title,
        location="Unspecified",
        description_html=f"<pre>{raw_text}</pre>",
        description_text=raw_text,
        application_url=apply_url,
        api_posting_id=f"direct-{Path(jd_path).stem}",
    )

    resume = ResumeParser().parse()
    tailor_selected_jobs([job], resume, cover_letter=getattr(args, "cover_letter", False))


def run_list(args):
    """List tracked applications."""
    tracker = ApplicationTracker()
    apps = tracker.list_applications(status=args.status)

    if not apps:
        msg = "ℹ️  No tracked applications found"
        if args.status:
            msg += f" with status '{args.status}'"
        print(msg)
        return

    print("=" * 85)
    print(f"📋 Tracked Applications ({len(apps)} total)")
    print("=" * 85)
    print(f"  {'#':<3} | {'Company':<16} | {'Role':<26} | {'Match':<5} | {'Status':<18} | {'Application URL'}")
    print(f"  {'-'*3}-+-{'-'*16}-+-{'-'*26}-+-{'-'*5}-+-{'-'*18}-+-{'-'*25}")

    for idx, app in enumerate(apps, start=1):
        cov = f"{int(app.get('coverage_score', 0) * 100)}%"
        url = app.get("application_url", "")
        url_snippet = (url[:25] + "...") if len(url) > 25 else url
        status = app.get("status", "unknown")
        status_display = "✅ Ready" if status == "ready_for_review" else ("⚠️  Needs Review" if status == "validation_failed" else status)
        print(f"  {idx:<3} | {app.get('company', ''):<16} | {app.get('title', '')[:26]:<26} | {cov:<5} | {status_display:<18} | {url_snippet}")
    print("=" * 85 + "\n")


def run_apply(args):
    """Open application URL for given job in browser."""
    tracker = ApplicationTracker()
    app = tracker.get_application(args.job_id)

    url = None
    if app:
        url = app.get("application_url")
    else:
        # Check if direct output directory exists
        candidate_dir = settings.output_dir / args.job_id
        url_file = candidate_dir / "application_url.txt"
        if url_file.exists():
            url = url_file.read_text(encoding="utf-8").strip()

    if not url or url.startswith("MANUAL"):
        print(f"No direct application URL found for: {args.job_id}")
        return

    print(f"Opening application URL: {url}")
    webbrowser.open(url)


def run_validate_cli(args):
    """Re-validate an existing output job."""
    out_dir = settings.output_dir / args.job_id
    if not out_dir.exists():
        print(f"Output directory not found: {out_dir}")
        return

    pdf_file = out_dir / "resume.pdf"
    html_file = out_dir / "resume.html"
    analysis_file = out_dir / "job_analysis.json"
    tailored_file = out_dir / "tailored_resume.json"

    if not pdf_file.exists() or not html_file.exists() or not analysis_file.exists():
        print("Missing required output files (resume.pdf, resume.html, or job_analysis.json).")
        return

    from src.models.jd import JDAnalysis
    from src.models.tailored import TailoredResume

    jd_analysis = JDAnalysis.model_validate_json(analysis_file.read_text(encoding="utf-8"))
    tailored = (
        TailoredResume.model_validate_json(tailored_file.read_text(encoding="utf-8"))
        if tailored_file.exists()
        else None
    )
    resume = ResumeParser().parse()

    validator = ATSValidator()
    report = validator.validate(
        pdf_path=pdf_file,
        html_path=html_file,
        tailored_resume=tailored or TailoredResume(
            job_id=args.job_id,
            application_url="",
            contact=resume.contact,
            summary=resume.summary,
            skills=resume.skills,
            experience=resume.experience,
            projects=resume.projects,
            education=resume.education,
        ),
        master_resume=resume,
        jd_analysis=jd_analysis,
        output_dir=out_dir,
    )

    print(f"\nValidation Result for {args.job_id}:")
    print(f"Passed: {'✅ YES' if report.passed else '❌ NO'}")
    for c in report.checks:
        status = "✅" if c.passed else "❌"
        print(f"  {status} {c.check:<26}: {c.detail or ''}")


def run_add_company(args):
    """Add a company to ats_companies.json."""
    config_file = settings.ats_companies_path
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    ats = args.ats.lower()
    if ats not in data:
        data[ats] = {"enabled": True, "rate_limit_delay_seconds": 1.0, "companies": []}

    companies = data[ats].get("companies", [])
    if any(c["slug"] == args.slug for c in companies):
        print(f"Company '{args.slug}' already exists under {ats}.")
        return

    companies.append({"slug": args.slug, "name": args.name or args.slug.capitalize()})
    data[ats]["companies"] = companies

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Added {args.name or args.slug} ({args.slug}) to {ats} configuration.")


def run_remove_company(args):
    """Remove a company from ats_companies.json."""
    config_file = settings.ats_companies_path
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    ats = args.ats.lower()
    if ats not in data:
        print(f"ATS '{ats}' not found in configuration.")
        return

    companies = data[ats].get("companies", [])
    initial_count = len(companies)
    companies = [c for c in companies if c["slug"] != args.slug]

    if len(companies) == initial_count:
        print(f"Company '{args.slug}' not found under {ats}.")
        return

    data[ats]["companies"] = companies
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Removed {args.slug} from {ats} configuration.")


def run_add_link(args):
    """Add an ATS job board link to ats_companies.json."""
    config_file = settings.ats_companies_path
    parsed = parse_ats_url(args.url, custom_name=args.name)
    if not parsed:
        print(f"❌ Could not recognize ATS platform for URL: {args.url}")
        print("   Supported platforms:")
        print("   - Lever:      https://jobs.lever.co/<company-slug>")
        print("   - Greenhouse: https://boards.greenhouse.io/<company-slug> or https://job-boards.greenhouse.io/<company-slug>")
        print("   - Ashby:      https://jobs.ashbyhq.com/<company-slug>")
        return 1

    ats_platform, slug, company_name = parsed

    if not config_file.exists():
        data = {"links": [args.url]}
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Created {config_file.name} with link: {args.url} ({company_name} on {ats_platform})")
        return 0

    with open(config_file, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = {"links": []}

    # Case 1: List of links/items
    if isinstance(data, list):
        if args.url in data or any(isinstance(x, dict) and (x.get("url") == args.url or x.get("slug") == slug) for x in data):
            print(f"⚠️  Link or company already configured in {config_file.name}: {slug}")
            return 0
        data.append(args.url)
    elif isinstance(data, dict):
        if "links" in data and isinstance(data["links"], list):
            if args.url in data["links"]:
                print(f"⚠️  Link already exists in {config_file.name}: {args.url}")
                return 0
            data["links"].append(args.url)
        elif "ats_links" in data and isinstance(data["ats_links"], list):
            if args.url in data["ats_links"]:
                print(f"⚠️  Link already exists in {config_file.name}: {args.url}")
                return 0
            data["ats_links"].append(args.url)
        else:
            # Categorized structure: {"lever": {...}, ...}
            if ats_platform not in data:
                data[ats_platform] = {"enabled": True, "rate_limit_delay_seconds": 1.0, "companies": []}
            companies = data[ats_platform].setdefault("companies", [])
            if any(c.get("slug") == slug for c in companies):
                print(f"⚠️  Company '{slug}' already exists under {ats_platform} in {config_file.name}.")
                return 0
            companies.append({"slug": slug, "name": company_name, "url": args.url})

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Added {company_name} ({slug}) on {ats_platform.capitalize()} to {config_file.name}.")
    return 0


def run_submit(args):
    """Mark an application as submitted and set follow-up reminders."""
    tracker = ApplicationTracker()
    app = tracker.get_application(args.job_id)
    if not app:
        print(f"Application not found: {args.job_id}")
        return

    if tracker.mark_submitted(args.job_id):
        app = tracker.get_application(args.job_id)
        print(f"✅ Marked as submitted: {app['company']} — {app['title']}")
        print(f"   Submitted at: {app.get('submitted_at', 'now')}")
        print("   Follow-up reminders set:")
        for fu in app.get("followup_dates", []):
            print(f"     📅 {fu['date']} ({fu['days_after']} days after submission)")
    else:
        print(f"Failed to update: {args.job_id}")


def run_stage(args):
    """Log an interview stage."""
    tracker = ApplicationTracker()
    if tracker.add_interview_stage(args.job_id, args.stage, date=args.date, notes=args.notes):
        app = tracker.get_application(args.job_id)
        print(f"✅ Logged stage '{args.stage}' for {app['company']} — {app['title']}")
        print(f"   Interview stages:")
        for s in app.get("interview_stages", []):
            print(f"     • {s['date']} — {s['stage']}{': ' + s['notes'] if s.get('notes') else ''}")
    else:
        print(f"Application not found: {args.job_id}")


def run_note(args):
    """Add a note to an application."""
    tracker = ApplicationTracker()
    if tracker.add_note(args.job_id, args.text):
        print(f"✅ Note added to {args.job_id}")
    else:
        print(f"Application not found: {args.job_id}")


def run_followups(args):
    """Show pending follow-up reminders."""
    tracker = ApplicationTracker()
    pending = tracker.get_pending_followups()

    if not pending:
        print("No pending follow-ups. You're all caught up!")
        return

    print("=" * 70)
    print(f"📬 Pending Follow-ups ({len(pending)})")
    print("=" * 70)
    for fu in pending:
        print(f"  📅 {fu['followup_date']} — {fu['company']} — {fu['title']}")
        print(f"     {fu['days_after']} days since submission")
        print(f"     Apply: {fu['application_url']}")
        print()
    print("💡 Mark a follow-up as done: python main.py submit <job_id> (sets new reminders)")


def run_pipeline(args):
    """Show application funnel summary."""
    tracker = ApplicationTracker()
    counts = tracker.get_pipeline_summary()

    if not counts:
        print("No tracked applications yet.")
        return

    total = sum(counts.values())
    print("=" * 50)
    print(f"📊 Application Pipeline ({total} total)")
    print("=" * 50)

    stage_order = [
        ("ready_for_review", "📝 Ready for Review"),
        ("approved", "✅ Approved"),
        ("submitted", "📤 Submitted"),
        ("applied", "📨 Applied"),
        ("recruiter_screen", "📞 Recruiter Screen"),
        ("phone_interview", "📱 Phone Interview"),
        ("technical_interview", "💻 Technical Interview"),
        ("onsite_interview", "🏢 Onsite Interview"),
        ("final_round", "🎯 Final Round"),
        ("offer", "🎉 Offer"),
        ("accepted", "✅ Accepted"),
        ("rejected", "❌ Rejected"),
        ("withdrawn", "🚫 Withdrawn"),
        ("no_response", "😶 No Response"),
        ("validation_failed", "⚠️  Validation Failed"),
    ]

    for key, label in stage_order:
        count = counts.get(key, 0)
        if count > 0:
            bar = "█" * count
            print(f"  {label:<28} {bar} {count}")

    print("=" * 50)


def run_cron(args):
    """Generate cron command for daily scheduled scanning."""
    cron_line = generate_cron_command()
    print("Add this line to your crontab (run `crontab -e`):\n")
    print(f"  {cron_line}")
    print("\nThis runs `scan --auto-tailor-top 3` daily at 8:00 AM.")
    print("Desktop notifications will alert you about high-match jobs.")
    print(f"Logs saved to: {settings.data_dir / 'cron.log'}")


def run_serve(args):
    """Start the HireReady Web API & UI server."""
    import uvicorn
    host = getattr(args, "host", "0.0.0.0")
    port = getattr(args, "port", 8000)
    reload = getattr(args, "reload", False)
    print("=" * 80)
    print("🚀 HireReady — Web Dashboard & API Server")
    print("=" * 80)
    print(f"\n  • Local URL : http://localhost:{port}")
    print(f"  • API Docs  : http://localhost:{port}/docs\n")
    print("Press Ctrl+C to stop the server.\n")
    uvicorn.run("src.api.app:app", host=host, port=port, reload=reload)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="HireReady — AI-Powered Resume Tailoring Pipeline")
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # serve
    p_serve = subparsers.add_parser("serve", help="Start the HireReady Web UI & API server")
    p_serve.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")
    p_serve.set_defaults(func=run_serve)

    # setup
    p_setup = subparsers.add_parser("setup", help="Validate setup, resume, preferences, and ATS configuration")
    p_setup.set_defaults(func=run_setup)

    # scan
    p_scan = subparsers.add_parser("scan", help="Scan ATS platforms, rank jobs, and tailor matches")
    p_scan.add_argument("--auto-tailor-top", type=int, help="Automatically tailor top N matching jobs")
    p_scan.add_argument("--cover-letter", action="store_true", help="Generate cover letters during tailoring (extra Gemini call)")
    p_scan.set_defaults(func=run_scan)

    # tailor
    p_tailor = subparsers.add_parser("tailor", help="Tailor resume for jobs from scan or direct JD file")
    p_tailor.add_argument("targets", nargs="?", help="Target rank numbers (e.g. 1,2,5)")
    p_tailor.add_argument("--top", type=int, help="Tailor top N jobs from previous scan")
    p_tailor.add_argument("--jd", help="Path to direct JD file (.pdf, .txt, .html)")
    p_tailor.add_argument("--company", help="Company name for direct JD mode")
    p_tailor.add_argument("--title", help="Job title for direct JD mode")
    p_tailor.add_argument("--url", help="Direct application URL for direct JD mode")
    p_tailor.add_argument("--cover-letter", action="store_true", help="Generate a tailored cover letter (extra Gemini call)")
    p_tailor.set_defaults(func=run_tailor_cli)

    # list
    p_list = subparsers.add_parser("list", help="List tracked applications")
    p_list.add_argument("--status", help="Filter by application status")
    p_list.set_defaults(func=run_list)

    # apply
    p_apply = subparsers.add_parser("apply", help="Open application URL in default browser")
    p_apply.add_argument("job_id", help="Job ID or output directory name")
    p_apply.set_defaults(func=run_apply)

    # validate
    p_val = subparsers.add_parser("validate", help="Re-validate an existing output job")
    p_val.add_argument("job_id", help="Job ID or folder name")
    p_val.set_defaults(func=run_validate_cli)

    # add-link
    p_add_link = subparsers.add_parser("add-link", help="Add an ATS job board link (auto-detects platform)")
    p_add_link.add_argument("url", help="Job board URL (e.g., https://boards.greenhouse.io/airbnb)")
    p_add_link.add_argument("--name", help="Optional company display name")
    p_add_link.set_defaults(func=run_add_link)

    # add-company
    p_add = subparsers.add_parser("add-company", help="Add a company to ATS scan list")
    p_add.add_argument("slug", help="Company ATS slug")
    p_add.add_argument("--ats", required=True, help="ATS platform name (must match a key in config/ats_platforms.json)")
    p_add.add_argument("--name", help="Company display name")
    p_add.set_defaults(func=run_add_company)

    # remove-company
    p_rem = subparsers.add_parser("remove-company", help="Remove a company from ATS scan list")
    p_rem.add_argument("slug", help="Company ATS slug")
    p_rem.add_argument("--ats", required=True, help="ATS platform name (must match a key in config/ats_platforms.json)")
    p_rem.set_defaults(func=run_remove_company)

    # submit — mark as submitted + set follow-up reminders
    p_submit = subparsers.add_parser("submit", help="Mark application as submitted and schedule follow-up reminders")
    p_submit.add_argument("job_id", help="Job ID")
    p_submit.set_defaults(func=run_submit)

    # stage — log an interview stage
    p_stage = subparsers.add_parser("stage", help="Log an interview stage for a tracked application")
    p_stage.add_argument("job_id", help="Job ID")
    p_stage.add_argument("stage", help="Stage name (e.g., recruiter_screen, phone_interview, technical_interview, onsite_interview, offer, rejected)")
    p_stage.add_argument("--date", help="Date of interview (YYYY-MM-DD, defaults to today)")
    p_stage.add_argument("--notes", default="", help="Notes about this stage")
    p_stage.set_defaults(func=run_stage)

    # note — add a note to an application
    p_note = subparsers.add_parser("note", help="Add a note to a tracked application")
    p_note.add_argument("job_id", help="Job ID")
    p_note.add_argument("text", help="Note text")
    p_note.set_defaults(func=run_note)

    # followups — view pending follow-ups
    p_followups = subparsers.add_parser("followups", help="View pending follow-up reminders")
    p_followups.set_defaults(func=run_followups)

    # pipeline — show application funnel
    p_pipeline = subparsers.add_parser("pipeline", help="Show application funnel summary")
    p_pipeline.set_defaults(func=run_pipeline)

    # cron — generate cron command for daily scanning
    p_cron = subparsers.add_parser("cron", help="Generate cron command for daily scheduled scanning")
    p_cron.set_defaults(func=run_cron)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
