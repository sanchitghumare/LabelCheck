from __future__ import annotations

from typing import Any, Protocol

from app.schemas.commodity import PackagedCommodity
from app.schemas.response import ComplianceVerdict
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.extraction.orchestrator import ExtractionOrchestrator


class VisionService(Protocol):
    async def analyze(
        self,
        image_bytes: bytes,
        content_type: str | None,
    ) -> Any:
        ...


class ScanService:
    """
    Application service responsible for the complete scan pipeline.

    Coordinates vision, extraction, and compliance evaluation.

    Persistence and authentication are intentionally handled by the
    Next.js application layer.
    """

    def __init__(
        self,
        vision_service: VisionService,
        extraction_orchestrator: ExtractionOrchestrator,
        compliance_engine: ComplianceEngine,
    ) -> None:
        self.vision_service = vision_service
        self.extraction_orchestrator = extraction_orchestrator
        self.compliance_engine = compliance_engine

    async def scan(
        self,
        image_bytes: bytes,
        content_type: str | None,
        scan_id: str,
    ) -> ComplianceVerdict:
        """
        Run the complete packaged-commodity scan pipeline.

        Pipeline:
            1. Vision
            2. Extraction
            3. Compliance evaluation

        The scan_id is accepted so the existing service interface remains
        compatible with the API layer. Persistence is handled separately
        by Next.js.
        """

        # ---------------------------------------------------------
        # 1. Vision
        # ---------------------------------------------------------

        vision_result = await self.vision_service.analyze(
            image_bytes=image_bytes,
            content_type=content_type,
        )

        # ---------------------------------------------------------
        # 2. Extraction
        # ---------------------------------------------------------

        ocr_results = [
            dict(token)
            for token in vision_result.ocr_results
        ]

        extraction_result = self.extraction_orchestrator.process(
            ocr_results
        )

        commodity: PackagedCommodity = extraction_result.commodity

        # ---------------------------------------------------------
        # 3. Compliance
        # ---------------------------------------------------------

        verdict = self.compliance_engine.evaluate(
            commodity=commodity,
            px_per_mm=vision_result.px_per_mm,
            net_quantity_font_height_px=(
                vision_result.net_quantity_font_height_px
            ),
        )

        return verdict