from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.extraction.orchestrator import ExtractionOrchestrator
from app.services.vision.Service import VisionServiceImpl
from app.api.endpoints import router
from app.core.database import close_mongo_connection, connect_to_mongo
from app.modules.scans.service import ScanService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # --- Application services ---
    app.state.scan_service = ScanService(
        vision_service=VisionServiceImpl(),
        extraction_orchestrator=ExtractionOrchestrator(),
        compliance_engine=ComplianceEngine(),
    )

    # --- MongoDB is optional ---
    # The API continues serving scans when MongoDB is unavailable.
    app.state.mongo_connected = False

    try:
        await connect_to_mongo()
        app.state.mongo_connected = True
        logger.info("MongoDB connected.")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "MongoDB unavailable, continuing without persistence: %s",
            exc,
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