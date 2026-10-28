"""ATS scan coordination, scoring, and SSE progress streaming service."""

import json
import logging
from typing import AsyncGenerator

from config.settings import settings
from src.ats.aggregator import ATSAggregator
from src.ats.generic_client import load_platform_configs
from src.models.job_listing import DeepScore
from src.resume_parser import load_preferences
from src.models.resume import ResumeData
from src.scorer import Scorer

logger = logging.getLogger(__name__)


class ScanService:
    """Orchestrates job scanning across ATS providers, two-pass scoring, and SSE streaming."""

    def __init__(self, aggregator: ATSAggregator | None = None):
        self.aggregator = aggregator or ATSAggregator()

    async def stream_scan(self, resume: ResumeData) -> AsyncGenerator[str, None]:
        """Stream ATS scan progress and scoring steps via JSON SSE messages."""
        try:
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

        # Pass 1: Quick Scoring
        yield json.dumps({"type": "status", "message": f"Quick scoring {len(jobs_to_process)} listings..."})
        scorer = Scorer()
        scored_pairs = scorer.rank_quick(jobs_to_process, resume, prefs)
        quick_score_map = {job.id: qscore for job, qscore in scored_pairs}

        all_passing = [job for job, qscore in scored_pairs if qscore.pass_to_deep_scoring]
        if not all_passing:
            all_passing = [job for job, _ in scored_pairs]

        candidates = all_passing[:settings.max_deep_score_candidates]

        # Pass 2: Gemini Deep Scoring
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

        # Rank all passing jobs
        default_ds = DeepScore(job_id="", semantic_match=0.0, role_fit="", key_gaps=[], recommendation="skip")
        ranked_jobs = sorted(
            all_passing,
            key=lambda j: (-deep_score_map.get(j.id, default_ds).semantic_match, j.company.lower(), j.title.lower()),
        )

        last_scan_cache = {
            "jobs": [j.model_dump(mode="json") for j in ranked_jobs],
            "deep_scores": {k: v.model_dump(mode="json") for k, v in deep_score_map.items()},
        }
        (settings.data_dir / "last_scan.json").write_text(json.dumps(last_scan_cache, indent=2, default=str), encoding="utf-8")

        yield json.dumps({
            "type": "complete",
            "message": f"Scan finished successfully! {len(ranked_jobs)} jobs ranked ({len(candidates)} deep-scored with Gemini).",
            "top_count": len(ranked_jobs),
        })
