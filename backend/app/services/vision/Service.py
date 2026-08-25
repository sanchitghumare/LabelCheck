"""
app/services/vision/service.py

Concrete vision service that composes the three pure vision modules
(preprocessor, calibrator, ocr) into the single object the API layer
expects at ``request.app.state.vision_service``.

This is the ONLY module in `services/vision` allowed to know about all
three sub-stages together; preprocessor.py, calibrator.py and ocr.py
each stay strictly single-purpose per their own docstrings.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Optional

from app.services.extraction.regex_parser import NET_QUANTITY_PATTERN
from app.services.vision.calibrator import calibrate_scale
from app.services.vision.ocr import OcrToken, extract_text_boxes
from app.services.vision.preprocessor import ImageDecodeError, preprocess_image

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VisionAnalysisResult:
    """Concrete result satisfying the `VisionAnalysis` protocol in endpoints.py."""

    ocr_results: list[OcrToken]
    px_per_mm: float
    net_quantity_font_height_px: Optional[float]
    barcode_data: Optional[str] = None
    is_calibration_fallback: bool = False


class VisionAnalysisError(ValueError):
    """Raised when an uploaded image cannot be analyzed end-to-end."""


def _estimate_net_quantity_font_height_px(
    tokens: Sequence[OcrToken],
) -> Optional[float]:
    """
    Best-effort heuristic: the pixel height of the first OCR token whose
    text alone matches a "<number> <unit>" net-quantity pattern (e.g.
    "200g", "1.5 L"). Tesseract sometimes splits the number and unit
    into separate tokens, in which case this returns None and Rule 9
    correctly falls back to a FAIL with an explicit "no measurement"
    reason rather than a guess.
    """
    for token in tokens:
        text = token.get("text", "")
        box = token.get("box")
        if not text or not box or len(box) != 4:
            continue
        if NET_QUANTITY_PATTERN.search(text):
            return float(box[3])
    return None


# Conservative fallback so a barcode-free photo (e.g. cropped tightly on
# the label) still produces a usable, clearly-flagged-as-low-confidence
# scale instead of hard-failing the whole scan at the calibration step.
FALLBACK_PX_PER_MM: float = 11.8  # ~300 DPI equivalent


class VisionServiceImpl:
    """
    Default vision service: preprocess -> barcode calibration -> OCR.

    Blocking CV/OCR calls are pushed onto a worker thread via
    `asyncio.to_thread` so the event loop stays responsive under
    concurrent uploads.
    """

    def __init__(self, fallback_px_per_mm: Optional[float] = FALLBACK_PX_PER_MM) -> None:
        self._fallback_px_per_mm = fallback_px_per_mm

    async def analyze(
        self, image_bytes: bytes, content_type: str | None
    ) -> VisionAnalysisResult:
        try:
            processed_image = await asyncio.to_thread(preprocess_image, image_bytes)
        except ImageDecodeError as exc:
            raise VisionAnalysisError(str(exc)) from exc

        calibration = await asyncio.to_thread(
            calibrate_scale, processed_image, self._fallback_px_per_mm
        )
        if calibration.px_per_mm is None:
            raise VisionAnalysisError(
                "Could not calibrate scale: no barcode detected and no "
                "fallback px_per_mm configured."
            )

        tokens = await asyncio.to_thread(extract_text_boxes, processed_image)

        font_height_px = _estimate_net_quantity_font_height_px(tokens)

        logger.info(
            "Vision analysis complete: %d OCR tokens, px_per_mm=%.3f "
            "(fallback=%s), font_height_px=%s",
            len(tokens),
            calibration.px_per_mm,
            calibration.is_fallback,
            font_height_px,
        )

        return VisionAnalysisResult(
            ocr_results=tokens,
            px_per_mm=calibration.px_per_mm,
            net_quantity_font_height_px=font_height_px,
            barcode_data=calibration.barcode_data,
            is_calibration_fallback=calibration.is_fallback,
        )