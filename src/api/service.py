import html
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator

from bs4 import BeautifulSoup

import yaml

from config.settings import settings
from src.ats.aggregator import ATSAggregator
from src.ats.base import parse_ats_url
from src.ats.generic_client import load_platform_configs
from src.ats_validator import ATSValidator
from src.company_research import CompanyResearcher
from src.cover_letter_generator import CoverLetterGenerator
from src.html_generator import HTMLGenerator
from src.models.job_listing import DeepScore, JobListing
from src.models.preferences import SearchPreferences
from src.models.resume import ResumeData
from src.pdf_generator import PDFGenerator
from src.red_flag_detector import RedFlagDetector
from src.resume_matcher import ResumeMatcher
from src.resume_parser import ResumeParser, load_preferences
from src.resume_tailor import ResumeTailor
from src.role_suggester import RoleSuggester
from src.salary_extractor import SalaryExtractor
from src.scorer import Scorer
from src.tracker import ApplicationTracker

logger = logging.getLogger("hireready.api.service")


class APIService:
    def __init__(self):
        self.aggregator = ATSAggregator()
        self.tracker = ApplicationTracker()

    def get_resume(self) -> ResumeData:
        return ResumeParser().parse()

    def get_preferences(self) -> dict[str, Any]:
        prefs_path = settings.input_dir / "preferences.yaml"
        if not prefs_path.exists():
            return {}
        try:
            with open(prefs_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error("Error loading preferences: %s", e)
            return {}

    def update_preferences(self, data: dict[str, Any]) -> dict[str, Any]:
        prefs_path = settings.input_dir / "preferences.yaml"
        with open(prefs_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)
        return self.get_preferences()

    def get_ats_companies(self) -> dict[str, Any]:
        path = settings.ats_companies_path
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Error reading ats_companies.json: %s", e)
            return {}

    def add_ats_link(self, url: str | None = None, platform: str | None = None, company_slug: str | None = None, name: str | None = None) -> dict[str, Any]:
        if url:
            parsed = parse_ats_url(url)
            if not parsed:
                raise ValueError("Could not detect supported ATS platform from URL.")
            platform, company_slug, detected_name = parsed
            if not name:
                name = detected_name

        if not platform or not company_slug:
            raise ValueError("Platform and company_slug are required.")

        config = self.get_ats_companies()
        if platform not in config:
            config[platform] = {"enabled": True, "rate_limit_delay_seconds": 1.0, "companies": []}

        # Normalize config entry format
        entry = config[platform]
        if isinstance(entry, list):
            config[platform] = {"enabled": True, "rate_limit_delay_seconds": 1.0, "companies": entry}
        companies_list = config[platform].setdefault("companies", [])

        # Check for duplicates
        if not any(
            (isinstance(c, dict) and c.get("slug") == company_slug) or
            (isinstance(c, str) and c == company_slug)
            for c in companies_list
        ):
            companies_list.append({"slug": company_slug, "name": name or company_slug.replace("-", " ").title()})
            settings.ats_companies_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

        return config

    def delete_ats_company(self, platform: str, company_slug: str) -> dict[str, Any]:
        config = self.get_ats_companies()
        if platform in config:
            entry = config[platform]
            if isinstance(entry, dict):
                companies = entry.get("companies", [])
            else:
                companies = entry

            config[platform]["companies"] = [
                c for c in companies
                if not (
                    (isinstance(c, dict) and c.get("slug") == company_slug) or
                    (isinstance(c, str) and c == company_slug)
                )
            ]
            settings.ats_companies_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return config

    def get_jobs(self) -> dict[str, Any]:
        last_scan_path = settings.data_dir / "last_scan.json"
        if not last_scan_path.exists():
            return {"jobs": [], "total": 0, "suggestions": []}

        try:
            data = json.loads(last_scan_path.read_text(encoding="utf-8"))
            raw_jobs = data.get("jobs", [])
            deep_scores = data.get("deep_scores", {})
        except Exception as e:
            logger.error("Error loading last_scan.json: %s", e)
            return {"jobs": [], "total": 0, "suggestions": []}

        tracker_data = self.get_tracker()
        tracker_map = {app["job_id"]: app for app in tracker_data.get("applications", [])}

        enriched_jobs = []
        for j in raw_jobs:
            job_id = j.get("id")
            ds = deep_scores.get(job_id, {})
            
            # Clean and unescape HTML/text
            desc_html = j.get("description_html") or ""
            if "&lt;" in desc_html:
                desc_html = html.unescape(desc_html)
                if "&lt;" in desc_html:
                    desc_html = html.unescape(desc_html)
            
            desc_text = j.get("description_text") or ""
            if "<div" in desc_text or "<p" in desc_text or "&lt;" in desc_text:
                desc_text = BeautifulSoup(desc_html or desc_text, "html.parser").get_text("\n", strip=True)

            j["description_html"] = desc_html
            j["description_text"] = desc_text

            desc = desc_text or desc_html
            salary = SalaryExtractor.extract(desc, j.get("metadata", {}))
            red_flags = RedFlagDetector.scan(desc, j.get("title", ""))
            flag_summary = RedFlagDetector.summarize(red_flags)

            output_dir = settings.output_dir / job_id
            has_tailored = (output_dir / "resume.pdf").exists()

            enriched_jobs.append({
                **j,
                "score": ds.get("semantic_match", 0.5),
                "role_fit": ds.get("role_fit", ""),
                "key_gaps": ds.get("key_gaps", []),
                "recommendation": ds.get("recommendation", "weak_match"),
                "salary": salary.display,
                "salary_range": {"min": salary.min_salary, "max": salary.max_salary, "currency": salary.currency},
                "red_flags": [f.to_dict() for f in red_flags],
                "red_flag_count": flag_summary.get("total", 0),
                "red_flag_verdict": flag_summary.get("verdict", "clean"),
                "has_tailored_resume": has_tailored,
                "tracker_status": tracker_map.get(job_id, {}).get("status"),
            })

        # Generate role suggestions
        suggestions = {}
        try:
            prefs = load_preferences()
            seen_titles = [j.get("title", "") for j in raw_jobs]
            suggestions = RoleSuggester.suggest(prefs.target_roles, seen_titles)
        except Exception as e:
            logger.debug("Failed to generate role suggestions: %s", e)

        return {
            "jobs": enriched_jobs,
            "total": len(enriched_jobs),
            "suggestions": suggestions,
        }

    def get_tracker(self) -> dict[str, Any]:
        return self.tracker._load_data()

    def update_tracker(self, job_id: str, status: str, notes: str | None = None) -> dict[str, Any]:
        # Find if job exists in last_scan to get metadata
        jobs_data = self.get_jobs()
        job = next((j for j in jobs_data["jobs"] if j["id"] == job_id), None)

        data = self.tracker._load_data()
        apps = data.get("applications", [])
        app = next((a for a in apps if a.get("job_id") == job_id), None)

        if app:
            app["status"] = status
            app["updated_at"] = datetime.now().isoformat()
            if notes:
                app.setdefault("notes", []).append({
                    "text": notes,
                    "created_at": datetime.now().isoformat(),
                })
            if status == "submitted":
                app["submitted_at"] = datetime.now().isoformat()
            self.tracker._save_data(data)
        elif job:
            self.tracker.record_application(
                job_id=job_id,
                company=job.get("company", ""),
                title=job.get("title", ""),
                application_url=job.get("application_url", ""),
                output_dir=str(settings.output_dir / job_id),
                status=status,
            )
        return self.get_tracker()

    def delete_tracker(self, job_id: str) -> dict[str, Any]:
        data = self.tracker._load_data()
        apps = data.get("applications", [])
        data["applications"] = [a for a in apps if a.get("job_id") != job_id]
        self.tracker._save_data(data)
        return self.get_tracker()

    def get_job_output(self, job_id: str) -> dict[str, Any]:
        output_folder = settings.output_dir / job_id
        if not output_folder.exists():
            return {"exists": False}

        result: dict[str, Any] = {"exists": True, "job_id": job_id}

        pdf_path = output_folder / "resume.pdf"
        html_path = output_folder / "resume.html"
        cl_txt_path = output_folder / "cover_letter.txt"
        cl_html_path = output_folder / "cover_letter.html"
        analysis_path = output_folder / "job_analysis.json"
        match_path = output_folder / "match_report.json"
        val_path = output_folder / "validation_report.json"
        summary_path = output_folder / "change_summary.md"
        red_flags_path = output_folder / "red_flags.json"
        company_path = output_folder / "company_brief.json"
        salary_path = output_folder / "salary_info.json"
        url_path = output_folder / "application_url.txt"

        result["has_pdf"] = pdf_path.exists()
        result["has_html"] = html_path.exists()
        result["has_cover_letter"] = cl_txt_path.exists()

        if cl_txt_path.exists():
            result["cover_letter_txt"] = cl_txt_path.read_text(encoding="utf-8")
        if cl_html_path.exists():
            result["cover_letter_html"] = cl_html_path.read_text(encoding="utf-8")
        if analysis_path.exists():
            result["job_analysis"] = json.loads(analysis_path.read_text(encoding="utf-8"))
        if match_path.exists():
            result["match_report"] = json.loads(match_path.read_text(encoding="utf-8"))
        if val_path.exists():
            result["validation_report"] = json.loads(val_path.read_text(encoding="utf-8"))
        if summary_path.exists():
            result["change_summary"] = summary_path.read_text(encoding="utf-8")
        if red_flags_path.exists():
            result["red_flags"] = json.loads(red_flags_path.read_text(encoding="utf-8"))
        if company_path.exists():
            result["company_brief"] = json.loads(company_path.read_text(encoding="utf-8"))
        if salary_path.exists():
            result["salary_info"] = json.loads(salary_path.read_text(encoding="utf-8"))
        if url_path.exists():
            result["application_urls"] = url_path.read_text(encoding="utf-8")

        return result

    def tailor_job(self, job_id: str, generate_cover_letter: bool = False) -> dict[str, Any]:
        jobs_data = self.get_jobs()
        job_dict = next((j for j in jobs_data["jobs"] if j["id"] == job_id), None)
        if not job_dict:
            raise ValueError(f"Job {job_id} not found in recent scan results.")

        resume = self.get_resume()
        job = JobListing.model_validate(job_dict)

        output_folder = settings.output_dir / job.id
        output_folder.mkdir(parents=True, exist_ok=True)

        tailor = ResumeTailor()
        html_gen = HTMLGenerator()
        pdf_gen = PDFGenerator()
        matcher = ResumeMatcher()
        validator = ATSValidator(pdf_generator=pdf_gen)

        # Step 1: Combined JD Analysis + Resume Tailoring (single Gemini call)
        jd_analysis, tailored = tailor.analyze_and_tailor(
            resume=resume,
            job_description=job.description_text or job.description_html,
            job_id=job.id,
            company=job.company,
            job_title=job.title,
            application_url=job.application_url,
            output_dir=output_folder,
        )

        # Step 2: Match report (deterministic)
        match_report = matcher.match(jd_analysis, resume, output_dir=output_folder)

        # Step 3: HTML
        html_file = output_folder / "resume.html"
        html_gen.generate(tailored, target_role=job.title, output_path=html_file)

        # Step 4: PDF
        pdf_file = output_folder / "resume.pdf"
        pdf_gen.generate_pdf(html_path=html_file, pdf_path=pdf_file)

        # Step 5: Validate
        val_report = validator.validate(
            pdf_path=pdf_file,
            html_path=html_file,
            tailored_resume=tailored,
            master_resume=resume,
            jd_analysis=jd_analysis,
            output_dir=output_folder,
        )

        # Step 6: Red flags (deterministic)
        red_flags = RedFlagDetector.scan(job.description_text, job.title)
        flag_summary = RedFlagDetector.summarize(red_flags)
        (output_folder / "red_flags.json").write_text(json.dumps(flag_summary, indent=2), encoding="utf-8")

        # Step 7: Company research (Gemini, cached per company)
        company_researcher = CompanyResearcher()
        company_researcher.research(job.company, job.title, job.description_text, output_dir=output_folder)

        # Step 8: Cover letter (Gemini, opt-in)
        if generate_cover_letter:
            cover_letter_gen = CoverLetterGenerator()
            cover_letter_gen.generate(
                resume=resume,
                jd_analysis=jd_analysis,
                match_report=match_report,
                output_dir=output_folder,
            )

        # Step 9: Salary + LinkedIn
        from src.linkedin_detector import LinkedInDetector
        salary = SalaryExtractor.extract(job.description_text, job.metadata)
        linkedin_info = LinkedInDetector.get_linkedin_info(job.company, job.title, job.description_text)

        (output_folder / "salary_info.json").write_text(json.dumps(salary.to_dict(), indent=2), encoding="utf-8")

        url_lines = [
            f"ATS Apply: {job.application_url.strip()}",
            f"LinkedIn Easy Apply: {linkedin_info['linkedin_easy_apply_search']}",
            f"LinkedIn Search: {linkedin_info['linkedin_job_search']}",
        ]
        if linkedin_info.get("linkedin_direct_url"):
            url_lines.append(f"LinkedIn Direct: {linkedin_info['linkedin_direct_url']}")
        (output_folder / "application_url.txt").write_text("\n".join(url_lines) + "\n", encoding="utf-8")

        # Step 10: Record in tracker
        self.tracker.record_application(
            job_id=job.id,
            company=job.company,
            title=job.title,
            application_url=job.application_url,
            output_dir=str(output_folder),
            coverage_score=match_report.coverage_score,
            validation_passed=val_report.passed,
            needs_review_count=len(tailored.needs_review),
            status="ready_for_review" if val_report.passed else "validation_failed",
            salary=salary.display,
            linkedin_url=linkedin_info["linkedin_easy_apply_search"],
        )

        return self.get_job_output(job.id)

    async def scan_stream(self) -> AsyncGenerator[str, None]:
        """Stream scan execution progress via Server-Sent Events."""
        try:
            resume = self.get_resume()
            prefs = load_preferences()
        except Exception as e:
            yield json.dumps({"type": "error", "message": f"Setup error: {e}"})
            return

        yield json.dumps({"type": "status", "message": "Starting ATS scanner..."})

        platform_configs = load_platform_configs()
        platform_names = list(platform_configs.keys())
        yield json.dumps({
            "type": "platforms",
            "platforms": platform_names,
            "message": f"Scanning {len(platform_names)} configured ATS platforms...",
        })

        new_jobs, stats = await self.aggregator.fetch_all(prefs)

        for p_name in platform_names:
            count = stats.get(p_name, 0)
            if count > 0:
                yield json.dumps({
                    "type": "platform_result",
                    "platform": p_name,
                    "count": count,
                })

        total_fetched = stats.get("total_fetched", 0)
        after_filters = stats.get("after_filters", 0)
        yield json.dumps({
            "type": "summary",
            "total_fetched": total_fetched,
            "after_filters": after_filters,
            "new_count": len(new_jobs),
        })

        jobs_to_process = new_jobs if new_jobs else stats.get("matching_jobs", [])
        if not jobs_to_process:
            yield json.dumps({"type": "complete", "message": "No jobs found matching criteria."})
            return

        # Quick Scoring
        yield json.dumps({"type": "status", "message": f"Quick scoring {len(jobs_to_process)} listings..."})
        scorer = Scorer()
        scored_pairs = scorer.rank_quick(jobs_to_process, resume, prefs)
        quick_score_map = {job.id: qscore for job, qscore in scored_pairs}

        candidates = [job for job, qscore in scored_pairs if qscore.pass_to_deep_scoring][:settings.max_deep_score_candidates]
        if not candidates:
            candidates = [job for job, _ in scored_pairs[:settings.max_deep_score_candidates]]

        # Deep Scoring
        yield json.dumps({"type": "status", "message": f"Deep scoring {len(candidates)} candidates with Gemini..."})
        deep_scores = scorer.deep_score_batch(candidates, resume)

        deep_score_map: dict[str, DeepScore] = {}
        for ds in deep_scores:
            if ds.semantic_match == 0.5 and ds.key_gaps and "Gemini API unavailable" in ds.key_gaps[0]:
                qs = quick_score_map.get(ds.job_id)
                if qs:
                    ds.semantic_match = qs.composite_score
                    ds.role_fit = f"Scored by keyword matching (Gemini unavailable). Title: {qs.title_match:.0%}, overlap: {qs.keyword_overlap:.0%}"
            deep_score_map[ds.job_id] = ds

        ranked_jobs = sorted(
            candidates,
            key=lambda j: deep_score_map.get(j.id, DeepScore(job_id=j.id, semantic_match=0.0, role_fit="", key_gaps=[], recommendation="skip")).semantic_match,
            reverse=True,
        )

        # Cache last scan
        last_scan_cache = {
            "jobs": [j.model_dump(mode="json") for j in ranked_jobs],
            "deep_scores": {k: v.model_dump(mode="json") for k, v in deep_score_map.items()},
        }
        (settings.data_dir / "last_scan.json").write_text(json.dumps(last_scan_cache, indent=2, default=str), encoding="utf-8")

        yield json.dumps({
            "type": "complete",
            "message": f"Scan finished successfully! {len(ranked_jobs)} top jobs ranked.",
            "top_count": len(ranked_jobs),
        })
