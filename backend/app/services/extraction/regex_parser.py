from __future__ import annotations

import re
from typing import Any, Iterable

# Prefer an explicit MRP label so that unrelated prices are not selected.
MRP_LABEL_PATTERN = re.compile(
    r"""
    \b(?:m\.?\s*r\.?\s*p\.?|maximum\s+retail\s+price)
    \s*(?:\([^)]{0,80}\))?
    \s*[:=\-]?\s*
    (?:₹|rs\.?|inr)?\s*
    (?P<value>\d{1,6}(?:,\d{3})*(?:\.\d{1,2})?)
    (?:\s*/\s*[-=])?
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Supports labels which only say "Rs. 50" or "₹ 45".
MRP_CURRENCY_PATTERN = re.compile(
    r"""
    (?<![A-Za-z0-9])
    (?:₹|rs\.?|inr)
    \s*
    (?P<value>\d{1,6}(?:,\d{3})*(?:\.\d{1,2})?)
    (?:\s*/\s*[-=])?
    """,
    re.IGNORECASE | re.VERBOSE,
)

NET_QUANTITY_PATTERN = re.compile(
    r"""
    \b
    (?P<value>\d+(?:\.\d+)?)
    \s*
    (?P<unit>
        kgs?|kilograms?|
        g|gms?|grams?|
        mls?|millilit(?:re|er)s?|
        l|ltrs?|lit(?:re|er)s?
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Manufacturing-labelled dates only, preventing accidental use of expiry dates.
MFG_DATE_PATTERN = re.compile(
    r"""
    \b
    (?:mfg|mfd|manuf(?:actured|acturing)?)
    \.?
    (?:\s*(?:date|dt|on))?
    \s*[:=\-]?\s*
    (?P<date>
        \d{1,2}/\d{1,2}/\d{2,4} |  # DD/MM/YYYY
        \d{1,2}/\d{2,4}            # MM/YY or MM/YYYY
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

UNIT_NORMALIZATION = {
    "g": "g",
    "gm": "g",
    "gms": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kgs": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "ml": "ml",
    "mls": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "l": "l",
    "ltr": "l",
    "ltrs": "l",
    "litre": "l",
    "litres": "l",
    "liter": "l",
    "liters": "l",
}


def _normalise_number(value: str) -> float:
    return float(value.replace(",", ""))


def _first_match(
    pattern: re.Pattern[str],
    lines: Iterable[str],
) -> re.Match[str] | None:
    for line in lines:
        match = pattern.search(line)
        if match:
            return match
    return None


def parse_regex_fields(raw_ocr_strings: list[str]) -> dict[str, Any]:
    """
    Extract deterministic commodity fields from OCR text.

    Returns only fields that were confidently found. This lets the caller
    distinguish unavailable values from a value that was extracted as null.
    """
    lines = [line.strip() for line in raw_ocr_strings if isinstance(line, str) and line.strip()]
    extracted: dict[str, Any] = {}

    mrp_match = _first_match(MRP_LABEL_PATTERN, lines)
    if mrp_match is None:
        mrp_match = _first_match(MRP_CURRENCY_PATTERN, lines)
    if mrp_match:
        extracted["mrp"] = _normalise_number(mrp_match.group("value"))

    quantity_match = _first_match(NET_QUANTITY_PATTERN, lines)
    if quantity_match:
        extracted["net_quantity_value"] = float(quantity_match.group("value"))
        raw_unit = quantity_match.group("unit").lower()
        extracted["net_quantity_unit"] = UNIT_NORMALIZATION[raw_unit]

    date_match = _first_match(MFG_DATE_PATTERN, lines)
    if date_match:
        extracted["mfg_date"] = date_match.group("date")

    return extracted