from __future__ import annotations

from typing import Any, Protocol

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.core.database import save_audit
from app.schemas.commodity import PackagedCommodity
from app.schemas.response import ComplianceVerdict
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.extraction.orchestrator import ExtractionOrchestrator
from app.services.vision.ocr import 


class VisionAnalysis(Protocol):
    """Contract implemented by the separate vision service."""

    ocr_results: list[dict[str, Any]]
    px_per_mm: float
    net_quantity_font_height_px: float | None


class VisionService(Protocol):
    async def analyze(self, image_bytes: bytes, content_type: str | None) -> VisionAnalysis:
        """Run image calibration and OCR in the separately owned vision service."""
        ...


router = APIRouter(prefix="/api/v1", tags=["audits"])

_extraction_orchestrator = ExtractionOrchestrator()
_compliance_engine = ComplianceEngine()


def _get_vision_service(request: Request) -> VisionService:
    service = getattr(request.app.state, "vision_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vision service has not been configured.",
        )
    return service


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

    try:
        # Implemented by the separate OCR / calibration service.
        vision_result = await vision_service.analyze(
            image_bytes=image_bytes,
            content_type=file.content_type,
        )

        commodity: PackagedCommodity = _extraction_orchestrator.process(
            vision_result.ocr_results
        )

        verdict = _compliance_engine.evaluate(
            commodity=commodity,
            px_per_mm=vision_result.px_per_mm,
            net_quantity_font_height_px=vision_result.net_quantity_font_height_px,
        )

        # await save_audit(verdict)
        return verdict

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete the commodity audit.",
        ) from exc
    finally:
        await file.close()