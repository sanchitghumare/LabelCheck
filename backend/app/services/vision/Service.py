"""
app/services/vision/service.py

Concrete vision service that composes the three pure vision modules
(preprocessor, calibrator, ocr) into the single object the API layer
expects at ``request.app.state.vision_service``.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
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
    Finds the pixel height of the token(s) corresponding to the net-quantity
    declaration (e.g. '100 g', '100g', '1.5 L').
    """
    # Group first: `100` and `g` are commonly emitted as separate words.
    # A token without line metadata is treated as a single-word line.
    lines: dict[Any, list[OcrToken]] = defaultdict(list)
    for index, token in enumerate(tokens):
        line_id = token.get("line_id")
        key = tuple(line_id) if isinstance(line_id, (tuple, list)) else ("token", index)
        lines[key].append(token)

    for line_tokens in lines.values():
        ordered_tokens = sorted(
            line_tokens,
            key=lambda token: int(token.get("box", [0, 0, 0, 0])[0]),
        )
        text_parts: list[str] = []
        spans: list[tuple[int, int, OcrToken]] = []
        cursor = 0
        for token in ordered_tokens:
            text = token.get("text", "").strip()
            if not text:
                continue
            if text_parts:
                cursor += 1  # account for the joining space
            start = cursor
            cursor += len(text)
            text_parts.append(text)
            spans.append((start, cursor, token))

        match = NET_QUANTITY_PATTERN.search(" ".join(text_parts))
        if not match:
            continue
        value_start, value_end = match.span("value")
        for start, end, token in spans:
            if start < value_end and end > value_start:
                box = token.get("box", [])
                if len(box) == 4:
                    return float(box[3])

    return None


FALLBACK_PX_PER_MM: float = 11.8  # ~300 DPI equivalent


class VisionServiceImpl:
    """
    Default vision service: preprocess -> barcode calibration -> OCR.
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
