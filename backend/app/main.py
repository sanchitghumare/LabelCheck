from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router
from app.services.vision.Service import VisionServiceImpl
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.extraction.orchestrator import ExtractionOrchestrator
from app.modules.scans.service import ScanService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Initialize application services for the Python scan engine.

    Authentication and persistence are owned by the Next.js application.
    The Python service is responsible only for image analysis,
    extraction, and deterministic compliance evaluation.
    """

    app.state.scan_service = ScanService(
        vision_service=VisionServiceImpl(),
        extraction_orchestrator=ExtractionOrchestrator(),
        compliance_engine=ComplianceEngine(),
    )

    yield


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