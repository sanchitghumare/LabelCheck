from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.modules.scans.service import ScanService
from app.schemas.response import ComplianceVerdict
from app.schemas.scan import ScanResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["audits"])


def _get_scan_service(request: Request) -> ScanService:
    service = getattr(request.app.state, "scan_service", None)

    if service is None:
        logger.warning(
            "scan_service missing from app.state; creating fallback instance."
        )
        service = ScanService(
            vision_service=request.app.state.vision_service,
            extraction_orchestrator=request.app.state.extraction_orchestrator,
            compliance_engine=request.app.state.compliance_engine,
        )
        request.app.state.scan_service = service

    return service


@router.post(
    "/scan",
    response_model=ScanResult,
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

    scan_service = _get_scan_service(request)
    scan_id = str(uuid4())

    try:
        return await scan_service.scan(
            image_bytes=image_bytes,
            content_type=file.content_type,
            scan_id=scan_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Unhandled error while auditing scan %s.",
            scan_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete the commodity audit.",
        ) from exc

    finally:
        await file.close()