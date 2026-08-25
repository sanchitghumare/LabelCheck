"""
app/services/vision/calibrator.py

Optical scale calibration for the Legal Metrology compliance vision
pipeline.

Objective: derive a pixels-per-millimeter (px_per_mm) scale factor from
a detected retail barcode of known physical width, so downstream (out
of scope, handled elsewhere) logic can check printed font heights
against LMPC Rule 9 minimums in real-world millimeters.

Scope (strict): barcode detection + scale math only. No text/NLP
parsing, no persistence, no API routing.
"""

from __future__ import annotations

import logging
from typing import Any, NamedTuple, Optional

import numpy as np
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol

logger = logging.getLogger(__name__)

# Standard physical width, in millimeters, of a nominal (100%-magnification)
# EAN-13 / UPC-A retail barcode symbol (quiet zones excluded, full symbol
# width including guard bars included). Used as the ground-truth reference
# length for scale calibration.
EAN13_PHYSICAL_WIDTH_MM: float = 37.29

# Fallback scale used when no barcode can be detected in the frame.
# This is a conservative approximation and should be treated as low
# confidence by any downstream consumer -- it is NOT a substitute for
# a real detected barcode. Set to None by default to force callers to
# handle the "no calibration available" case explicitly; a numeric
# fallback can be supplied via the `fallback_px_per_mm` argument.
DEFAULT_FALLBACK_PX_PER_MM: Optional[float] = None

# pyzbar symbol types considered valid retail barcodes for calibration.
_SUPPORTED_BARCODE_SYMBOLS = (ZBarSymbol.EAN13, ZBarSymbol.UPCA)


class CalibrationResult(NamedTuple):
    """Result of a barcode-based scale calibration attempt."""

    px_per_mm: Optional[float]
    barcode_data: Optional[str]
    barcode_type: Optional[str]
    box: Optional[list[int]]  # [x, y, w, h] in pixel space
    is_fallback: bool


def _select_best_barcode(barcodes: list[Any]) -> Optional[Any]:
    """
    From a list of pyzbar decoded objects, select the most reliable one
    to use for calibration. Preference: widest bounding box (larger
    detections are generally less noisy / less affected by perspective
    skew on a flat label).

    Args:
        barcodes: List of pyzbar Decoded objects.

    Returns:
        The selected Decoded object, or None if the input list is empty.
    """
    if not barcodes:
        return None
    return max(barcodes, key=lambda b: b.rect.width)


def calibrate_scale(
    processed_image: np.ndarray,
    fallback_px_per_mm: Optional[float] = DEFAULT_FALLBACK_PX_PER_MM,
) -> CalibrationResult:
    """
    Detect a standard retail barcode (EAN-13/UPC-A) in the preprocessed
    image and compute the pixels-per-millimeter scale factor from its
    pixel width, using the known physical width of an EAN-13 symbol as
    ground truth.

    Args:
        processed_image: Preprocessed (grayscale, CLAHE-applied) image
            array, as produced by preprocessor.preprocess_image.
        fallback_px_per_mm: Value to return (with is_fallback=True) when
            no barcode is detected. Defaults to None, meaning "no
            calibration available" -- pass a positive float to instead
            supply a low-confidence default scale.

    Returns:
        A CalibrationResult with:
            px_per_mm: calculated (or fallback) scale, or None if
                neither a barcode was found nor a fallback was supplied.
            barcode_data: decoded barcode payload string, if found.
            barcode_type: pyzbar symbol type name, if found.
            box: [x, y, w, h] pixel bounding box of the barcode, if found.
            is_fallback: True if px_per_mm came from fallback_px_per_mm
                rather than an actual detection.
    """
    if processed_image is None or processed_image.size == 0:
        logger.warning("calibrate_scale received an empty image array.")
        return CalibrationResult(
            px_per_mm=fallback_px_per_mm,
            barcode_data=None,
            barcode_type=None,
            box=None,
            is_fallback=fallback_px_per_mm is not None,
        )

    barcodes = pyzbar.decode(
        processed_image, symbols=_SUPPORTED_BARCODE_SYMBOLS
    )

    best_barcode = _select_best_barcode(barcodes)

    if best_barcode is None:
        logger.info(
            "No EAN-13/UPC-A barcode detected; returning fallback "
            "px_per_mm=%s",
            fallback_px_per_mm,
        )
        return CalibrationResult(
            px_per_mm=fallback_px_per_mm,
            barcode_data=None,
            barcode_type=None,
            box=None,
            is_fallback=fallback_px_per_mm is not None,
        )

    rect = best_barcode.rect  # pyzbar Rect(left, top, width, height)
    pixel_width = float(rect.width)

    if pixel_width <= 0:
        logger.warning(
            "Detected barcode has non-positive pixel width (%s); "
            "returning fallback.",
            pixel_width,
        )
        return CalibrationResult(
            px_per_mm=fallback_px_per_mm,
            barcode_data=best_barcode.data.decode("utf-8", errors="replace"),
            barcode_type=best_barcode.type,
            box=[rect.left, rect.top, rect.width, rect.height],
            is_fallback=fallback_px_per_mm is not None,
        )

    px_per_mm = pixel_width / EAN13_PHYSICAL_WIDTH_MM

    logger.info(
        "Calibrated scale from %s barcode: pixel_width=%.2f -> "
        "px_per_mm=%.4f",
        best_barcode.type,
        pixel_width,
        px_per_mm,
    )

    return CalibrationResult(
        px_per_mm=px_per_mm,
        barcode_data=best_barcode.data.decode("utf-8", errors="replace"),
        barcode_type=best_barcode.type,
        box=[rect.left, rect.top, rect.width, rect.height],
        is_fallback=False,
    )


def get_px_per_mm(
    processed_image: np.ndarray,
    fallback_px_per_mm: Optional[float] = DEFAULT_FALLBACK_PX_PER_MM,
) -> Optional[float]:
    """
    Convenience wrapper around calibrate_scale for callers that only
    need the scalar scale factor.

    Args:
        processed_image: Preprocessed image array.
        fallback_px_per_mm: Value to return if no barcode is detected.

    Returns:
        The float px_per_mm scale, the supplied fallback if no barcode
        was found, or None if no barcode was found and no fallback was
        supplied.
    """
    return calibrate_scale(
        processed_image, fallback_px_per_mm=fallback_px_per_mm
    ).px_per_mm