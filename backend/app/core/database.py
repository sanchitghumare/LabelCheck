from __future__ import annotations

import os
from typing import Optional

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
)
from pymongo import ASCENDING, DESCENDING
from pymongo.results import InsertOneResult

from app.schemas.audit import AuditRecord


MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv(
    "MONGODB_DATABASE",
    "legal_metrology",
)

_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> None:
    """Create and validate the MongoDB connection."""
    global _client, _database

    if _database is not None:
        return

    if not MONGODB_URI:
        raise RuntimeError(
            "MONGODB_URI environment variable is not configured."
        )

    _client = AsyncIOMotorClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=5_000,
        tz_aware=True,
    )

    await _client.admin.command("ping")

    _database = _client[MONGODB_DATABASE]

    # Indexes used by the audit-history/report APIs.
    await _database["audits"].create_index(
        [("scan_id", ASCENDING)],
        unique=True,
    )

    await _database["audits"].create_index(
        [("timestamp", DESCENDING)],
    )


async def close_mongo_connection() -> None:
    """Close the MongoDB connection during FastAPI shutdown."""
    global _client, _database

    if _client is not None:
        _client.close()

    _client = None
    _database = None


def get_database() -> AsyncIOMotorDatabase:
    """Return the active MongoDB database."""
    if _database is None:
        raise RuntimeError("MongoDB is not connected.")

    return _database


async def save_audit(audit: AuditRecord) -> str:
    """
    Persist a completed audit.

    The scan_id is unique, preventing accidental duplicate
    audit records for the same scan.
    """
    database = get_database()

    document = audit.model_dump(mode="json")

    result: InsertOneResult = await database["audits"].insert_one(
        document
    )

    return str(result.inserted_id)


async def get_audit(
    scan_id: str,
) -> AuditRecord | None:
    """Retrieve one audit by its scan ID."""
    database = get_database()

    document = await database["audits"].find_one(
        {"scan_id": scan_id},
        {"_id": 0},
    )

    if document is None:
        return None

    return AuditRecord.model_validate(document)


async def get_recent_audits(
    limit: int = 20,
) -> list[AuditRecord]:
    """Retrieve the most recent audit records."""
    database = get_database()

    if limit < 1:
        raise ValueError("limit must be greater than zero")

    limit = min(limit, 100)

    cursor = (
        database["audits"]
        .find({}, {"_id": 0})
        .sort("timestamp", DESCENDING)
        .limit(limit)
    )

    documents = await cursor.to_list(length=limit)

    return [
        AuditRecord.model_validate(document)
        for document in documents
    ]