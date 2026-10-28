"""HireReady Database package."""

from src.db.mongo import (
    is_mongo_configured,
    get_sync_client,
    get_async_client,
    get_sync_collection,
    get_async_collection,
    init_indexes,
    upsert_jobs_bulk,
    build_mongo_query,
    fetch_paginated_jobs_async,
    fetch_paginated_jobs_sync,
)
from src.db.normalizer import normalize_job_for_db

__all__ = [
    "is_mongo_configured",
    "get_sync_client",
    "get_async_client",
    "get_sync_collection",
    "get_async_collection",
    "init_indexes",
    "upsert_jobs_bulk",
    "build_mongo_query",
    "fetch_paginated_jobs_async",
    "fetch_paginated_jobs_sync",
    "normalize_job_for_db",
]
