from __future__ import annotations

import logging
from typing import Any, Protocol, cast

from app.core.database import save_audit
from app.schemas.audit import AuditRecord
from app.schemas.commodity import PackagedCommodity
from app.schemas.response import ComplianceVerdict
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.compliance.rule_versions import RULESET_VERSION
from app.services.extraction.orchestrator import ExtractionOrchestrator

logger = logging.getLogger(__name__)


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

    Coordinates vision, extraction, compliance, and audit persistence.
    The API layer should only handle HTTP concerns.
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
        """Run the complete packaged-commodity audit pipeline."""

        # 1. Vision
        vision_result = await self.vision_service.analyze(
            image_bytes=image_bytes,
            content_type=content_type,
        )

        # 2. Extraction
        ocr_results = [
            dict(token)
            for token in vision_result.ocr_results
        ]

        extraction_result = self.extraction_orchestrator.process(
            ocr_results
        )

        commodity: PackagedCommodity = extraction_result.commodity

        # 3. Compliance
        verdict = self.compliance_engine.evaluate(
            commodity=commodity,
            px_per_mm=vision_result.px_per_mm,
            net_quantity_font_height_px=(
                vision_result.net_quantity_font_height_px
            ),
        )

        # 4. Build immutable audit record
        audit = AuditRecord(
            scan_id=scan_id,
            timestamp=verdict.timestamp,
            verdict=verdict.verdict,
            px_per_mm=vision_result.px_per_mm,
            extracted_fields=commodity,
            rule_checks=verdict.rule_checks,
            extraction_confidence=extraction_result.confidence,
            extraction_evidence=cast(
                dict[str, object],
                extraction_result.evidence,
            ),
            ruleset_version=RULESET_VERSION,
            calibration_fallback=vision_result.is_calibration_fallback,
            barcode_data=vision_result.barcode_data,
        )

        # 5. Persistence is best-effort
        try:
            await save_audit(audit)
        except Exception:
            logger.exception(
                "Failed to persist audit record for scan %s.",
                scan_id,
            )

        return verdict