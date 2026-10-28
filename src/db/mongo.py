"""MongoDB connection manager, index initializer, and repository for HireReady NoSQL job store."""

from datetime import datetime, timezone
import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
import pymongo
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database

from config.settings import settings

logger = logging.getLogger(__name__)

# Singletons for connection caching
_sync_client: MongoClient | None = None
_async_client: AsyncIOMotorClient | None = None


def is_mongo_configured() -> bool:
    """Return True if a non-empty MongoDB URI is configured."""
    return bool(settings.mongodb_uri and settings.mongodb_uri.strip())


def get_sync_client() -> MongoClient:
    """Return singleton synchronous MongoClient."""
    global _sync_client
    if _sync_client is None:
        if not is_mongo_configured():
            raise ValueError("MONGODB_URI is not configured in settings or environment.")
        _sync_client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            appname="HireReadySync",
        )
    return _sync_client


def get_async_client() -> AsyncIOMotorClient:
    """Return singleton asynchronous AsyncIOMotorClient."""
    global _async_client
    if _async_client is None:
        if not is_mongo_configured():
            raise ValueError("MONGODB_URI is not configured in settings or environment.")
        _async_client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            appname="HireReadyAsync",
        )
    return _async_client


def get_sync_collection(collection_name: str | None = None) -> Collection:
    """Return synchronous Collection object."""
    client = get_sync_client()
    db: Database = client[settings.mongodb_db_name]
    return db[collection_name or settings.mongodb_collection]


def get_async_collection(collection_name: str | None = None) -> AsyncIOMotorCollection:
    """Return asynchronous AsyncIOMotorCollection object."""
    client = get_async_client()
    db: AsyncIOMotorDatabase = client[settings.mongodb_db_name]
    return db[collection_name or settings.mongodb_collection]


def init_indexes(collection: Collection | None = None) -> list[str]:
    """Create indexes on the job collection for fast queries and deduplication."""
    coll = collection or get_sync_collection()
    created_indexes = []

    try:
        # 1. Chronological & Platform
        i1 = coll.create_index(
            [("posted_date", pymongo.DESCENDING), ("ats_source", pymongo.ASCENDING)],
            name="idx_posted_ats",
            background=True,
        )
        created_indexes.append(i1)

        # 2. Remote filter
        i2 = coll.create_index([("remote", pymongo.ASCENDING)], name="idx_remote", background=True)
        created_indexes.append(i2)

        # 3. Company slug filter
        i3 = coll.create_index([("company_slug", pymongo.ASCENDING)], name="idx_company_slug", background=True)
        created_indexes.append(i3)

        # 4. Numerical salary filter
        i4 = coll.create_index([("salary.min", pymongo.ASCENDING)], name="idx_salary_min", background=True)
        created_indexes.append(i4)

        # 5. Skills array search
        i5 = coll.create_index([("skills_extracted", pymongo.ASCENDING)], name="idx_skills", background=True)
        created_indexes.append(i5)

        # 6. Text search index on title and description
        i6 = coll.create_index(
            [("title", pymongo.TEXT), ("description_text", pymongo.TEXT)],
            name="idx_text_search",
            weights={"title": 10, "description_text": 1},
            background=True,
        )
        created_indexes.append(i6)

        logger.info("Successfully created/verified %d MongoDB indexes on %s", len(created_indexes), coll.name)
    except Exception as e:
        logger.warning("Index creation notice: %s", e)

    return created_indexes


def upsert_jobs_bulk(jobs: list[dict[str, Any]], collection: Collection | None = None) -> tuple[int, int]:
    """Bulk upsert jobs into MongoDB using deterministic _id deduplication.

    Only newly seen jobs are inserted. For existing jobs, only 'last_scanned_at' is updated.
    Returns (inserted_count, updated_count).
    """
    if not jobs:
        return 0, 0

    coll = collection or get_sync_collection()
    now_utc = datetime.now(timezone.utc).isoformat()

    operations = []
    for job in jobs:
        job_id = job.get("_id") or job.get("id")
        if not job_id:
            continue

        doc = dict(job)
        doc["_id"] = job_id
        if "id" in doc:
            del doc["id"]

        operations.append(
            UpdateOne(
                {"_id": job_id},
                {
                    "$setOnInsert": {**doc, "first_seen_at": now_utc},
                    "$set": {"last_scanned_at": now_utc},
                },
                upsert=True,
            )
        )

    if not operations:
        return 0, 0

    try:
        result = coll.bulk_write(operations, ordered=False)
        inserted = result.upserted_count
        updated = result.matched_count
        return inserted, updated
    except Exception as e:
        logger.error("Error bulk upserting jobs to MongoDB: %s", e)
        raise


def build_mongo_query(
    search: str | None = None,
    platform: str | None = None,
    company: str | None = None,
    remote_only: bool = False,
    min_salary: int = 0,
    skills: list[str] | None = None,
) -> dict[str, Any]:
    """Build a standard MongoDB filter dictionary from user query parameters."""
    query: dict[str, Any] = {}

    if remote_only:
        query["remote"] = True

    if platform and platform.lower() != "all":
        query["ats_source"] = platform.lower()

    if company and company.lower() != "all":
        query["company_slug"] = company.lower()

    if min_salary and min_salary > 0:
        query["salary.min"] = {"$gte": min_salary}

    if skills:
        query["skills_extracted"] = {"$in": skills}

    if search and search.strip():
        s = search.strip()
        # Use regex pattern across title and company for substring matching
        query["$or"] = [
            {"title": {"$regex": s, "$options": "i"}},
            {"company": {"$regex": s, "$options": "i"}},
            {"location": {"$regex": s, "$options": "i"}},
            {"skills_extracted": {"$regex": s, "$options": "i"}},
        ]

    return query


async def fetch_paginated_jobs_async(
    query: dict[str, Any],
    page: int = 1,
    page_size: int = 15,
    sort_by: str = "posted_date",
    sort_desc: bool = True,
    collection: AsyncIOMotorCollection | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch paginated job documents asynchronously via Motor."""
    coll = collection or get_async_collection()

    sort_order = pymongo.DESCENDING if sort_desc else pymongo.ASCENDING
    sort_spec = [(sort_by, sort_order)]

    # Skip & limit
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    skip = (page - 1) * page_size

    total_count = await coll.count_documents(query)
    cursor = coll.find(query).sort(sort_spec).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    # Standardize output IDs for frontend compatibility
    for d in docs:
        if "_id" in d and "id" not in d:
            d["id"] = d["_id"]

    return docs, total_count


def fetch_paginated_jobs_sync(
    query: dict[str, Any],
    page: int = 1,
    page_size: int = 15,
    sort_by: str = "posted_date",
    sort_desc: bool = True,
    collection: Collection | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch paginated job documents synchronously via pymongo."""
    coll = collection or get_sync_collection()

    sort_order = pymongo.DESCENDING if sort_desc else pymongo.ASCENDING
    sort_spec = [(sort_by, sort_order)]

    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    skip = (page - 1) * page_size

    total_count = coll.count_documents(query)
    cursor = coll.find(query).sort(sort_spec).skip(skip).limit(page_size)
    docs = list(cursor)

    for d in docs:
        if "_id" in d and "id" not in d:
            d["id"] = d["_id"]

    return docs, total_count

