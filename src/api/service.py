import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator

import yaml

from config.settings import settings
from src.ats.aggregator import ATSAggregator
from src.ats.base import parse_ats_url
from src.ats.generic_client import load_platform_configs
from src.company_research import CompanyResearcher
from src.cover_letter_generator import CoverLetterGenerator
from src.html_generator import HTMLGenerator
from src.jd_analyzer import JDAnalyzer
from src.models.job_listing import DeepScore, JobListing
from src.models.preferences import SearchPreferences
from src.models.resume import ResumeData
from src.pdf_generator import PDFGenerator
from src.red_flag_detector import RedFlagDetector
from src.resume_matcher import ResumeMatcher
from src.resume_parser import ResumeParser
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

    def add_ats_link(self, url: str | None = None, platform: str | None = None, company_slug: str | None = None) -> dict[str, Any]:
        if url:
            parsed_platform, parsed_slug = parse_ats_url(url)
            if not parsed_platform or not parsed_slug:
                raise ValueError("Could not detect supported ATS platform from URL.")
            platform = parsed_platform
            company_slug = parsed_slug

        if not platform or not company_slug:
            raise ValueError("Platform and company_slug are required.")

        config = self.get_ats_companies()
        if platform not in config:
            config[platform] = {"companies": []}

        # Normalize config entry format
        entry = config[platform]
        if isinstance(entry, list):
            companies_list = entry
            config[platform] = {"companies": companies_list}
        else:
            companies_list = entry.setdefault("companies", [])

        if company_slug not in companies_list:
            companies_list.append(company_slug)
            settings.ats_companies_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

        return config

    def delete_ats_company(self, platform: str, company_slug: str) -> dict[str, Any]:
        config = self.get_ats_companies()
        if platform in config:
            entry = config[platform]
            companies = entry if isinstance(entry, list) else entry.get("companies", [])
            if company_slug in companies:
                companies.remove(company_slug)
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
            desc = j.get("description_text") or j.get("description_html") or ""
            salary = SalaryExtractor.extract(desc, j.get("metadata", {}))
            red_flags = RedFlagDetector.scan(desc, j.get("title", ""))

            output_dir = settings.output_dir / job_id
            has_tailored = (output_dir / "resume.pdf").exists()

            enriched_jobs.append({
                **j,
                "score": ds.get("semantic_match", 0.5),
                "role_fit": ds.get("role_fit", ""),
                "key_gaps": ds.get("key_gaps", []),
                "recommendation": ds.get("recommendation", "consider"),
                "salary": salary.display,
                "salary_range": {"min": salary.min_salary, "max": salary.max_salary, "currency": salary.currency},
                "red_flags": [f.get("issue") if isinstance(f, dict) else str(f) for f in red_flags],
                "red_flag_count": len(red_flags),
                "has_tailored_resume": has_tailored,
                "tracker_status": tracker_map.get(job_id, {}).get("status"),
            })

        # Generate role suggestions
        prefs = SearchPreferences(**self.get_preferences())
        seen_titles = [j.get("title", "") for j in raw_jobs]
        suggestions = RoleSuggester.suggest(prefs.target_roles, seen_titles)

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
        cl_path = output_folder / "cover_letter.md"
        analysis_path = output_folder / "job_analysis.json"
        match_path = output_folder / "match_report.json"
        val_path = output_folder / "validation_report.json"
        summary_path = output_folder / "change_summary.md"

        result["has_pdf"] = pdf_path.exists()
        result["has_html"] = html_path.exists()
        result["has_cover_letter"] = cl_path.exists()
        if cl_path.exists():
            result["cover_letter"] = cl_path.read_text(encoding="utf-8")
        if analysis_path.exists():
            result["job_analysis"] = json.loads(analysis_path.read_text(encoding="utf-8"))
        if match_path.exists():
            result["match_report"] = json.loads(match_path.read_text(encoding="utf-8"))
        if val_path.exists():
            result["validation_report"] = json.loads(val_path.read_text(encoding="utf-8"))
        if summary_path.exists():
            result["change_summary"] = summary_path.read_text(encoding="utf-8")

        return result

    def tailor_job(self, job_id: str, generate_cover_letter: bool = True) -> dict[str, Any]:
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
        cover_letter_gen = CoverLetterGenerator()
        company_researcher = CompanyResearcher()

        # Step 1: Analyze & Tailor
        jd_analysis, tailored = tailor.analyze_and_tailor(
            resume=resume,
            job_description=job.description_text or job.description_html,
            job_id=job.id,
            company=job.company,
            job_title=job.title,
            application_url=job.application_url,
            output_dir=output_folder,
        )

        # Step 2: Match
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
            target_role=job.title,
            output_dir=output_folder,
        )

        # Step 6: Cover Letter & Company Research
        if generate_cover_letter:
            research = company_researcher.research(job.company, job.description_text or job.description_html)
            cover_letter_gen.generate(
                resume=resume,
                tailored_resume=tailored,
                jd_analysis=jd_analysis,
                company=job.company,
                job_title=job.title,
                output_dir=output_folder,
                company_research=research,
            )

        # Step 7: Record in tracker
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
        )

        return self.get_job_output(job.id)

    async def scan_stream(self) -> AsyncGenerator[str, None]:
        """Stream scan execution progress via Server-Sent Events."""
        try:
            resume = self.get_resume()
            prefs = SearchPreferences(**self.get_preferences())
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
        yield json.dumps({"type": "status", "message": f"Deep scoring {len(candidates)} candidates..."})
        deep_scores = scorer.deep_score_batch(candidates, resume)

        deep_score_map: dict[str, DeepScore] = {}
        for ds in deep_scores:
            if ds.semantic_match == 0.5 and "Gemini API unavailable" in (ds.key_gaps[0] if ds.key_gaps else ""):
                qs = quick_score_map.get(getattr(ds, "job_id", None))
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
