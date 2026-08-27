"""
Concrete vision service.

Coordinates image preprocessing, image-quality assessment,
scale calibration, and OCR into a single vision analysis result.
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
from app.services.vision.preprocessor import (
    ImageDecodeError,
    preprocess_image,
)
from app.services.vision.quality import assess_image_quality

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VisionAnalysisResult:
    """
    Result produced by the vision pipeline.

    Contains OCR data, calibrated scale information,
    and metadata required by the scan service.
    """

    ocr_results: list[OcrToken]

    px_per_mm: float

    net_quantity_font_height_px: Optional[float]

    barcode_data: Optional[str] = None

    is_calibration_fallback: bool = False


class VisionAnalysisError(ValueError):
    """Raised when an image cannot be analyzed successfully."""


FALLBACK_PX_PER_MM: float = 11.8


def _estimate_net_quantity_font_height_px(
    tokens: Sequence[OcrToken],
) -> Optional[float]:
    """
    Estimate the pixel height of the numeric portion of the
    net-quantity declaration.

    Examples:
        100 g
        100g
        1.5 L
    """

    # OCR engines frequently return "100" and "g" as separate
    # tokens. Group tokens belonging to the same OCR line.
    lines: dict[Any, list[OcrToken]] = defaultdict(list)

    for index, token in enumerate(tokens):
        line_id = token.get("line_id")

        if isinstance(line_id, (tuple, list)):
            key = tuple(line_id)
        else:
            key = ("token", index)

        lines[key].append(token)

    for line_tokens in lines.values():

        # Restore natural left-to-right ordering.
        ordered_tokens = sorted(
            line_tokens,
            key=lambda token: int(
                token.get("box", [0, 0, 0, 0])[0]
            ),
        )

        text_parts: list[str] = []
        spans: list[tuple[int, int, OcrToken]] = []

        cursor = 0

        for token in ordered_tokens:
            text = token.get("text", "").strip()

            if not text:
                continue

            if text_parts:
                cursor += 1

            start = cursor
            cursor += len(text)

            text_parts.append(text)
            spans.append((start, cursor, token))

        combined_text = " ".join(text_parts)

        match = NET_QUANTITY_PATTERN.search(combined_text)

        if not match:
            continue

        value_start, value_end = match.span("value")

        for start, end, token in spans:

            # Find the token containing the numeric value.
            if start < value_end and end > value_start:

                box = token.get("box", [])

                if len(box) == 4:
                    try:
                        return float(box[3])
                    except (TypeError, ValueError):
                        continue

    return None


class VisionServiceImpl:
    """
    Default concrete implementation of the vision pipeline.

    Pipeline:

        image bytes
            ↓
        preprocessing
            ↓
        quality assessment
            ↓
        scale calibration
            ↓
        OCR
            ↓
        VisionAnalysisResult
    """

    def __init__(
        self,
        fallback_px_per_mm: Optional[float] = FALLBACK_PX_PER_MM,
    ) -> None:
        self._fallback_px_per_mm = fallback_px_per_mm

    async def analyze(
        self,
        image_bytes: bytes,
        content_type: str | None,
    ) -> VisionAnalysisResult:
        """
        Analyze an uploaded image.

        The image is decoded and preprocessed before OCR.
        Scale is calibrated using the barcode when possible,
        with a configured fallback when necessary.
        """

        if not image_bytes:
            raise VisionAnalysisError(
                "Uploaded image is empty."
            )

        # ---------------------------------------------------------
        # 1. Preprocessing + image quality
        # ---------------------------------------------------------

        try:
            processed_image = await asyncio.to_thread(
                preprocess_image,
                image_bytes,
            )

            quality_result = await asyncio.to_thread(
                assess_image_quality,
                processed_image,
            )

            logger.info(
                "Image quality: acceptable=%s, size=%dx%d, "
                "blur=%.2f, brightness=%.2f, contrast=%.2f, "
                "issues=%s",
                quality_result.is_acceptable,
                quality_result.width_px,
                quality_result.height_px,
                quality_result.blur_score,
                quality_result.brightness,
                quality_result.contrast,
                quality_result.issues,
            )

        except ImageDecodeError as exc:
            raise VisionAnalysisError(
                str(exc)
            ) from exc

        # ---------------------------------------------------------
        # 2. Scale calibration
        # ---------------------------------------------------------

        calibration = await asyncio.to_thread(
            calibrate_scale,
            processed_image,
            self._fallback_px_per_mm,
        )

        if calibration.px_per_mm is None:
            raise VisionAnalysisError(
                "Could not calibrate scale: no barcode detected "
                "and no fallback px_per_mm configured."
            )

        # ---------------------------------------------------------
        # 3. OCR
        # ---------------------------------------------------------

        tokens = await asyncio.to_thread(
            extract_text_boxes,
            processed_image,
        )

        # ---------------------------------------------------------
        # 4. Net quantity font measurement
        # ---------------------------------------------------------

        font_height_px = (
            _estimate_net_quantity_font_height_px(tokens)
        )

        # ---------------------------------------------------------
        # 5. Logging
        # ---------------------------------------------------------

        logger.info(
            "Vision analysis complete: %d OCR tokens, "
            "px_per_mm=%.3f (fallback=%s), "
            "net_quantity_font_height_px=%s",
            len(tokens),
            calibration.px_per_mm,
            calibration.is_fallback,
            font_height_px,
        )

        # ---------------------------------------------------------
        # 6. Return complete vision result
        # ---------------------------------------------------------

        return VisionAnalysisResult(
            ocr_results=tokens,
            px_per_mm=calibration.px_per_mm,
            net_quantity_font_height_px=font_height_px,
            barcode_data=calibration.barcode_data,
            is_calibration_fallback=calibration.is_fallback,
        )