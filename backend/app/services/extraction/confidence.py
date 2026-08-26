"""Confidence scoring for extracted packaged-commodity fields."""

from __future__ import annotations

from typing import Any


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def score_mrp(
    mrp: Any,
    *,
    meta: dict[str, Any] | None = None,
    ocr_confidence: float | None = None,
) -> float:
    """
    Estimate confidence that the extracted MRP is correct.

    This is a heuristic score, not a probability.
    """
    if mrp is None:
        return 0.0

    try:
        value = float(mrp)
    except (TypeError, ValueError):
        return 0.0

    if value <= 0:
        return 0.0

    meta = meta or {}

    # Start with a neutral score.
    score = 0.50

    source = meta.get("source")

    # Strong textual evidence.
    if source == "mrp_label":
        score += 0.30
    elif source == "tax_label":
        score += 0.30
    elif source == "currency":
        score += 0.15
    elif source == "numeric":
        score += 0.00

    # Suspiciously small prices are more likely to be OCR errors.
    if value < 5:
        score -= 0.20
    elif value < 10:
        score -= 0.05

    # OCR confidence is supplementary evidence, not the primary signal.
    if ocr_confidence is not None:
        ocr_confidence = clamp(float(ocr_confidence))
        score += (ocr_confidence - 0.5) * 0.20

    return round(clamp(score), 3)


def score_field(
    value: Any,
    *,
    ocr_confidence: float | None = None,
    evidence_strength: float = 0.5,
) -> float:
    """
    Generic confidence score for extracted fields.

    Used for fields where we don't yet have field-specific scoring logic.
    """
    if value is None:
        return 0.0

    if isinstance(value, str) and not value.strip():
        return 0.0

    score = 0.40 + (clamp(evidence_strength) * 0.40)

    if ocr_confidence is not None:
        score += (clamp(float(ocr_confidence)) - 0.5) * 0.40

    return round(clamp(score), 3)


def build_confidence(
    extracted: dict[str, Any],
    *,
    ocr_confidence: float | None = None,
) -> dict[str, float]:
    """
    Build confidence scores for all currently supported extracted fields.
    """
    confidence: dict[str, float] = {}

    if "mrp" in extracted:
        confidence["mrp"] = score_mrp(
            extracted["mrp"],
            meta=extracted.get("_mrp_meta"),
            ocr_confidence=ocr_confidence,
        )

    if "net_quantity_value" in extracted:
        confidence["net_quantity"] = score_field(
            extracted["net_quantity_value"],
            ocr_confidence=ocr_confidence,
            evidence_strength=0.7,
        )

    if "mfg_date" in extracted:
        confidence["mfg_date"] = score_field(
            extracted["mfg_date"],
            ocr_confidence=ocr_confidence,
            evidence_strength=0.7,
        )

    if "manufacturer_address" in extracted:
        confidence["manufacturer_address"] = score_field(
            extracted["manufacturer_address"],
            ocr_confidence=ocr_confidence,
            evidence_strength=0.6,
        )

    return confidence