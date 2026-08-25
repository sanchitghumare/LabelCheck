"""Raw Tesseract extraction with physical-line metadata."""

from __future__ import annotations

import logging
from typing import Optional, TypedDict

import numpy as np
import pytesseract
from pytesseract import Output

logger = logging.getLogger(__name__)

# Dot-matrix characters regularly receive low confidence despite being useful
# once neighbouring words have been reconstructed into a full line.
DEFAULT_MIN_CONFIDENCE: float = 10.0
# PSM 6 preserves line structure much better than sparse-word mode (PSM 11).
DEFAULT_TESSERACT_CONFIG = "--oem 3 --psm 6"


class OcrToken(TypedDict):
    text: str
    box: list[int]
    line_id: tuple[int, int, int]
    confidence: float


def extract_text_boxes(
    processed_image: np.ndarray,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    tesseract_config: str = DEFAULT_TESSERACT_CONFIG,
    lang: str = "eng",
) -> list[OcrToken]:
    """Return OCR words, boxes, confidence, and Tesseract physical line IDs."""
    if processed_image is None or processed_image.size == 0:
        logger.warning("extract_text_boxes received an empty image array.")
        return []

    raw_data = pytesseract.image_to_data(
        processed_image, lang=lang, config=tesseract_config, output_type=Output.DICT
    )
    tokens: list[OcrToken] = []
    for index, raw_text in enumerate(raw_data.get("text", [])):
        text = str(raw_text).strip()
        if not text:
            continue
        confidence = _safe_float(raw_data["conf"][index])
        if confidence is None or confidence < min_confidence:
            continue

        tokens.append(
            {
                "text": text,
                "box": [
                    int(raw_data["left"][index]), int(raw_data["top"][index]),
                    int(raw_data["width"][index]), int(raw_data["height"][index]),
                ],
                "line_id": (
                    int(raw_data["block_num"][index]),
                    int(raw_data["par_num"][index]),
                    int(raw_data["line_num"][index]),
                ),
                "confidence": confidence,
            }
        )

    logger.info("OCR extracted %d word tokens (min confidence %.1f)", len(tokens), min_confidence)
    return tokens


def _safe_float(value: object) -> Optional[float]:
    if not isinstance(value, (str, int, float)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
