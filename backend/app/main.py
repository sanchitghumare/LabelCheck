from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router
from app.core.database import close_mongo_connection, connect_to_mongo
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.extraction.orchestrator import ExtractionOrchestrator
from app.services.vision.Service import VisionServiceImpl

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # --- Required services: always constructed so /api/v1/scan never 503s. ---
    app.state.vision_service = VisionServiceImpl()
    app.state.extraction_orchestrator = ExtractionOrchestrator()
    app.state.compliance_engine = ComplianceEngine()

    # --- Mongo is optional: missing/unreachable Mongo must never stop the
    # API from serving scans in mock/local/offline mode. ---
    app.state.mongo_connected = False
    try:
        await connect_to_mongo()
        app.state.mongo_connected = True
        logger.info("MongoDB connected.")
    except Exception as exc:  # noqa: BLE001 - intentionally broad: any Mongo
        # failure (missing MONGODB_URI, unreachable host, auth error, etc.)
        # must degrade gracefully rather than crash the app.
        logger.warning(
            "MongoDB unavailable, continuing without persistence: %s", exc
        )

    try:
        yield
    finally:
        if app.state.mongo_connected:
            await close_mongo_connection()


app = FastAPI(
    title="Legal Metrology Compliance Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)