"""
app/services/vision/ocr.py

Raw OCR extraction for the Legal Metrology compliance vision pipeline.

Objective: given a preprocessed image, return the detected text tokens
and their pixel-space bounding boxes. This module performs NO semantic
parsing (e.g. identifying MRP, net quantity, manufacturer name) -- it
strictly emits raw (text, box) pairs for a downstream NLP/rules layer
to consume.

Scope (strict): OCR extraction only. No NLP parsing, no database, no
API routing code.
"""

from __future__ import annotations

import logging
from typing import Optional, TypedDict

import numpy as np
import pytesseract
from pytesseract import Output

logger = logging.getLogger(__name__)

# Tesseract confidence values below this threshold are discarded as noise
# (pytesseract reports -1 for non-text image regions, and low single-digit
# confidences are typically speckle/artifact false positives).
DEFAULT_MIN_CONFIDENCE: float = 30.0

# Default Tesseract config:
#   --oem 3  -> use the default LSTM OCR engine
#   --psm 11 -> "sparse text": find as much text as possible in no
#               particular order, well suited to product labels where
#               text is scattered across the package (not laid out as
#               uniform paragraphs).
DEFAULT_TESSERACT_CONFIG: str = "--oem 3 --psm 11"


class OcrToken(TypedDict):
    """A single OCR detection: raw text plus its pixel bounding box."""

    text: str
    box: list[int]  # [x, y, w, h] in pixel space, relative to input image


def extract_text_boxes(
    processed_image: np.ndarray,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    tesseract_config: str = DEFAULT_TESSERACT_CONFIG,
    lang: str = "eng",
) -> list[OcrToken]:
    """
    Run Tesseract OCR on a preprocessed image and return raw text tokens
    with their bounding boxes.

    Args:
        processed_image: Preprocessed (grayscale, CLAHE-applied) image
            array, as produced by preprocessor.preprocess_image.
        min_confidence: Minimum Tesseract confidence (0-100) required to
            keep a detected token. Tokens below this are dropped as
            noise. Pass 0 or a negative number to disable filtering.
        tesseract_config: Raw Tesseract CLI config string passed through
            to pytesseract (page segmentation mode, OCR engine mode, etc).
        lang: Tesseract language pack to use (must be installed
            alongside the tesseract-ocr binary, e.g. "eng").

    Returns:
        A list of dicts, each strictly of the form:
            {"text": "Extracted String", "box": [x, y, w, h]}
        Empty/whitespace-only tokens and tokens below min_confidence are
        excluded. Order follows Tesseract's internal detection order.

    Raises:
        pytesseract.TesseractNotFoundError: If the tesseract binary is
            not installed / not on PATH.
    """
    if processed_image is None or processed_image.size == 0:
        logger.warning("extract_text_boxes received an empty image array.")
        return []

    raw_data = pytesseract.image_to_data(
        processed_image,
        lang=lang,
        config=tesseract_config,
        output_type=Output.DICT,
    )

    tokens: list[OcrToken] = []
    num_detections = len(raw_data.get("text", []))

    for i in range(num_detections):
        text = raw_data["text"][i].strip()
        if not text:
            continue

        confidence = _safe_float(raw_data["conf"][i])
        if confidence is not None and confidence < min_confidence:
            continue

        x = int(raw_data["left"][i])
        y = int(raw_data["top"][i])
        w = int(raw_data["width"][i])
        h = int(raw_data["height"][i])

        tokens.append({"text": text, "box": [x, y, w, h]})

    logger.info(
        "OCR extracted %d text tokens (of %d raw detections, "
        "min_confidence=%.1f)",
        len(tokens),
        num_detections,
        min_confidence,
    )
    return tokens


def _safe_float(value: object) -> Optional[float]:
    """
    Safely coerce a Tesseract confidence value to float.

    Tesseract/pytesseract reports confidence as -1 (int or str) for
    entries that don't correspond to recognized text; these should not
    be dropped by strict filtering logic before an explicit numeric
    comparison, so this returns None on non-numeric/unparseable input
    rather than raising.

    Args:
        value: The raw confidence value from pytesseract's output dict.

    Returns:
        The parsed float, or None if it could not be parsed.
    """
    if isinstance(value, (int, float, str, bytes, bytearray)):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None