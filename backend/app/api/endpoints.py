from __future__ import annotations

import logging
from typing import Any, Protocol

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.core.database import save_audit
from app.schemas.commodity import PackagedCommodity
from app.schemas.response import ComplianceVerdict
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.extraction.orchestrator import ExtractionOrchestrator
from app.services.vision.Service import VisionAnalysisError, VisionServiceImpl

logger = logging.getLogger(__name__)


class VisionAnalysis(Protocol):
    """Contract implemented by the separate vision service."""

    ocr_results: list[dict[str, Any]]
    px_per_mm: float
    net_quantity_font_height_px: float | None


class VisionService(Protocol):
    async def analyze(self, image_bytes: bytes, content_type: str | None) -> Any:
        """Run image calibration and OCR in the separately owned vision service."""
        ...


router = APIRouter(prefix="/api/v1", tags=["audits"])

# Process-wide fallback singletons. These are used only if `lifespan` in
# main.py hasn't populated `app.state` for some reason (e.g. the app was
# constructed without running its lifespan, as can happen in certain test
# setups) -- this keeps the route itself from ever needing to 503 just
# because of *how* the app was booted.
_fallback_vision_service = VisionServiceImpl()
_fallback_extraction_orchestrator = ExtractionOrchestrator()
_fallback_compliance_engine = ComplianceEngine()


def _get_vision_service(request: Request) -> VisionService:
    service = getattr(request.app.state, "vision_service", None)
    if service is None:
        logger.warning(
            "vision_service missing from app.state; falling back to a "
            "default instance. Check that the app's lifespan ran."
        )
        service = _fallback_vision_service
        request.app.state.vision_service = service
    return service


def _get_extraction_orchestrator(request: Request) -> ExtractionOrchestrator:
    orchestrator = getattr(request.app.state, "extraction_orchestrator", None)
    if orchestrator is None:
        orchestrator = _fallback_extraction_orchestrator
        request.app.state.extraction_orchestrator = orchestrator
    return orchestrator


def _get_compliance_engine(request: Request) -> ComplianceEngine:
    engine = getattr(request.app.state, "compliance_engine", None)
    if engine is None:
        engine = _fallback_compliance_engine
        request.app.state.compliance_engine = engine
    return engine


@router.post(
    "/scan",
    response_model=ComplianceVerdict,
    status_code=status.HTTP_201_CREATED,
)
async def scan_packaged_commodity(
    request: Request,
    file: UploadFile = File(...),
) -> ComplianceVerdict:
    """Audit one packaged-commodity image."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only image uploads are supported.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded image is empty.",
        )

    vision_service = _get_vision_service(request)
    extraction_orchestrator = _get_extraction_orchestrator(request)
    compliance_engine = _get_compliance_engine(request)

    try:
        # Stage 1-3: Preprocess -> barcode scale calibration -> OCR
        # (all owned by the vision service).
        vision_result = await vision_service.analyze(
            image_bytes=image_bytes,
            content_type=file.content_type,
        )

        # Stage 4: NLP regex/LLM field extraction.
        commodity: PackagedCommodity = extraction_orchestrator.process(
            vision_result.ocr_results
        )

        # Stage 5: Compliance engine evaluation -> JSON response.
        verdict = compliance_engine.evaluate(
            commodity=commodity,
            px_per_mm=vision_result.px_per_mm,
            net_quantity_font_height_px=vision_result.net_quantity_font_height_px,
        )

        if getattr(request.app.state, "mongo_connected", False):
            try:
                await save_audit(verdict)
            except Exception:  # noqa: BLE001
                # Persistence is best-effort; never fail a scan over it.
                logger.exception("Failed to persist audit result to MongoDB.")

        return verdict

    except VisionAnalysisError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unhandled error while auditing commodity image.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete the commodity audit.",
        ) from exc
    finally:
        await file.close()