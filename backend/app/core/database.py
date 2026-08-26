from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.results import InsertOneResult

from app.schemas.response import ComplianceVerdict
from app.schemas.audit import AuditRecord

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "legal_metrology")

_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> None:
    """Create and validate the MongoDB Atlas connection."""
    global _client, _database

    if _database is not None:
        return

    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI environment variable is not configured.")

    _client = AsyncIOMotorClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=5_000,
        tz_aware=True,
    )
    await _client.admin.command("ping")
    _database = _client[MONGODB_DATABASE]


async def close_mongo_connection() -> None:
    """Close the MongoDB connection during FastAPI shutdown."""
    global _client, _database

    if _client is not None:
        _client.close()

    _client = None
    _database = None


def get_database() -> AsyncIOMotorDatabase:
    if _database is None:
        raise RuntimeError("MongoDB is not connected.")
    return _database


async def save_audit(audit: AuditRecord) -> str:
    """Persist a final audit result and return the inserted document ID."""
    database = get_database()

    document = audit.model_dump(mode="json")

    result: InsertOneResult = await database["audits"].insert_one(document)
    return str(result.inserted_id)