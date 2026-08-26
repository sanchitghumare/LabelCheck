"""Evidence generation for extracted packaged-commodity fields."""

from __future__ import annotations

from typing import Any


def _clean(text: str) -> str:
    return " ".join(text.split())


def find_mrp_evidence(
    raw_text: str,
    *,
    mrp: float | None = None,
    confidence: float = 0.0,
    source_type: str | None = None,
) -> dict[str, Any]:
    """Find the most relevant text fragment supporting the extracted MRP."""

    if not raw_text or mrp is None:
        return {
            "field": "mrp",
            "value": mrp,
            "confidence": confidence,
            "source_text": None,
            "source_type": source_type or "none",
        }

    text = _clean(raw_text)
    lower_text = text.lower()

    # Prefer the strongest declarations first.
    keywords = (
        "incl. of all taxes",
        "inclusive of all taxes",
        "maximum retail price",
        "mrp",
        "rs.",
        "rs ",
        "inr",
    )

    for keyword in keywords:
        index = lower_text.find(keyword)

        if index != -1:
            start = max(0, index - 20)
            end = min(len(text), index + len(keyword) + 60)

            return {
                "field": "mrp",
                "value": mrp,
                "confidence": confidence,
                "source_text": text[start:end].strip(),
                "source_type": source_type or "text_match",
            }

    return {
        "field": "mrp",
        "value": mrp,
        "confidence": confidence,
        "source_text": None,
        "source_type": source_type or "numeric_match",
    }


def build_evidence(
    extracted: dict[str, Any],
    raw_text: str,
    confidence: dict[str, float] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build evidence records for currently supported fields."""

    confidence = confidence or {}

    evidence: dict[str, dict[str, Any]] = {}

    if "mrp" in extracted:
        mrp_meta = extracted.get("_mrp_meta") or {}

        evidence["mrp"] = find_mrp_evidence(
            raw_text,
            mrp=extracted["mrp"],
            confidence=confidence.get("mrp", 0.0),
            source_type=mrp_meta.get("source"),
        )

    if "net_quantity_value" in extracted:
        evidence["net_quantity"] = {
            "field": "net_quantity",
            "value": extracted["net_quantity_value"],
            "unit": extracted.get("net_quantity_unit"),
            "confidence": confidence.get("net_quantity", 0.0),
            "source_text": None,
            "source_type": "text_match",
        }

    if "mfg_date" in extracted:
        evidence["mfg_date"] = {
            "field": "mfg_date",
            "value": extracted["mfg_date"],
            "confidence": confidence.get("mfg_date", 0.0),
            "source_text": None,
            "source_type": "text_match",
        }

    if "manufacturer_address" in extracted:
        evidence["manufacturer_address"] = {
            "field": "manufacturer_address",
            "value": extracted["manufacturer_address"],
            "confidence": confidence.get("manufacturer_address", 0.0),
            "source_text": None,
            "source_type": "text_match",
        }

    return evidence