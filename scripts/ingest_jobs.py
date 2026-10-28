#!/usr/bin/env python3
"""Manual ATS Job Ingestion Script for HireReady.

Fetches job listings from configured ATS providers, normalizes them into our custom
document format, and bulk upserts them to MongoDB Atlas with deduplication.

Usage:
    python scripts/ingest_jobs.py
    python scripts/ingest_jobs.py --ats ashby,greenhouse --limit 15
    python scripts/ingest_jobs.py --remote-only
    python scripts/ingest_jobs.py --dry-run
"""

import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from src.ats.aggregator import ATSAggregator
from src.ats.generic_client import load_platform_configs
from src.db.mongo import (
    get_sync_client,
    init_indexes,
    is_mongo_configured,
    upsert_jobs_bulk,
)
from src.db.normalizer import normalize_job_for_db
from src.resume_parser import load_preferences


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    # Mute noisy raw HTTP request logging from httpx/httpcore unless in verbose mode
    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch ATS jobs and store them in MongoDB Atlas NoSQL with deduplication."
    )
    parser.add_argument(
        "--ats",
        type=str,
        default="all",
        help="Comma-separated list of ATS platforms to scan (e.g. 'ashby,greenhouse,lever') or 'all' (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max jobs to fetch per company/platform",
    )
    parser.add_argument(
        "--remote-only",
        action="store_true",
        help="Filter for remote jobs only during scanning",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and normalize jobs without inserting into MongoDB",
    )
    parser.add_argument(
        "--init-indexes",
        action="store_true",
        default=True,
        help="Initialize MongoDB indexes before ingesting (default: True)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debug logging",
    )
    return parser.parse_args()


async def run_ingestion(args):
    setup_logging(args.verbose)
    logger = logging.getLogger("ingest")

    print("=" * 65)
    print("🚀 HireReady — Manual ATS Job Ingestion to MongoDB Atlas")
    print("=" * 65)

    # 1. Check MongoDB configuration
    if not args.dry_run and not is_mongo_configured():
        print("\n❌ Error: MONGODB_URI is not configured in your .env file.")
        print("Please add your MongoDB Atlas connection string to .env:")
        print("  MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority")
        print("  MONGODB_DB_NAME=hireready")
        print("Or run with --dry-run to test fetching without saving.")
        sys.exit(1)

    if not args.dry_run:
        try:
            client = get_sync_client()
            client.admin.command("ping")
            print(f"✓ Connected to MongoDB Atlas: database '{settings.mongodb_db_name}'")
            if args.init_indexes:
                init_indexes()
                print("✓ Verified MongoDB indexes for fast search and filtering")
        except Exception as e:
            print(f"\n❌ Error connecting to MongoDB: {e}")
            sys.exit(1)

    # 2. Load preferences & ATS platforms
    prefs = load_preferences()
    if args.remote_only:
        prefs.remote_only = True

    platform_configs = load_platform_configs()
    selected_platforms = list(platform_configs.keys())
    if args.ats and args.ats.lower() != "all":
        requested = [p.strip().lower() for p in args.ats.split(",") if p.strip()]
        selected_platforms = [p for p in selected_platforms if p.lower() in requested]

    print(f"\nScanning ATS platforms: {', '.join(selected_platforms).upper()}")
    print("Fetching listings... (this may take a few seconds)")

    aggregator = ATSAggregator()
    jobs, stats = await aggregator.fetch_all(prefs)
    # Use all matching jobs from the ATS scan so MongoDB Atlas can store and deduplicate them
    all_jobs = stats.get("matching_jobs", []) or jobs

    # Filter by requested platforms if specified
    if args.ats and args.ats.lower() != "all":
        all_jobs = [j for j in all_jobs if j.ats_source.lower() in selected_platforms]

    print(f"\n✓ Fetched {len(all_jobs)} total matching jobs from ATS sources:")
    for p in selected_platforms:
        p_count = sum(1 for j in all_jobs if j.ats_source.lower() == p.lower())
        print(f"  • {p.upper():<12}: {p_count} listings")

    if not all_jobs:
        print("\nNo jobs were returned matching your criteria. Exiting.")
        return

    # 3. Normalize into Custom NoSQL Document Schema
    print(f"\nNormalizing {len(all_jobs)} listings into custom document format...")
    normalized_docs = [normalize_job_for_db(job) for job in all_jobs]

    # Show sample preview
    sample = normalized_docs[0]
    print(f"\n[Sample Custom Document Schema Preview]")
    print(f"  ID:          {sample['_id']}")
    print(f"  Company:     {sample['company']} ({sample['ats_source']})")
    print(f"  Title:       {sample['title']}")
    print(f"  Salary:      {sample['salary']['raw']} (Min: {sample['salary']['min']}, Max: {sample['salary']['max']})")
    print(f"  Skills:      {', '.join(sample['skills_extracted'][:6]) if sample['skills_extracted'] else 'None'}")
    print(f"  Verdict:     {sample['red_flag_verdict']}")
    print(f"  Workplace:   {sample['workplace_type']} | Remote: {sample['remote']}")

    # 4. Ingest or Dry Run
    if args.dry_run:
        print("\n[Dry Run] Skipping MongoDB write. Processed successfully.")
        return

    print("\nUpserting documents into MongoDB Atlas collection 'job_listings'...")
    inserted_count, updated_count = upsert_jobs_bulk(normalized_docs)

    print("\n" + "=" * 65)
    print("🎉 Ingestion Complete Summary:")
    print("=" * 65)
    print(f"  • Total Scanned:          {len(normalized_docs):>5}")
    print(f"  • NEW Jobs Stored:        {inserted_count:>5} (Freshly inserted)")
    print(f"  • Already Existing Jobs:  {updated_count:>5} (Timestamp refreshed, deduplicated)")
    print("=" * 65)
    print("The backend API and UI will now serve these latest jobs with zero LLM browsing overhead!\n")


def main():
    args = parse_args()
    asyncio.run(run_ingestion(args))


if __name__ == "__main__":
    main()

