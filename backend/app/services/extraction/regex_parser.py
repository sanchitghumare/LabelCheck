"""Deterministic extraction for common Legal Metrology declarations."""

from __future__ import annotations

import re
from typing import Any

_NUMBER = r"\d{1,6}(?:,\d{3})*(?:\.\d{1,2})?"
_UNIT = (
    r"kgs?|kilograms?|g|gms?|grams?|mls?|millilit(?:re|er)s?|"
    r"l|ltrs?|lit(?:re|er)s?"
)

# A recognisable MRP label anchors the price. The short non-digit section after
# it intentionally accepts the usual OCR substitutes for the rupee sign (E,
# F, ?, 2, =, and Rs) plus punctuation and whitespace.
# MRP label + value.
# Keep the value extraction conservative because MRP is a legally
# important numeric field and should not be guessed.
MRP_PATTERN = re.compile(
    rf"""
    \b(?:m\s*\.?\s*r\s*\.?\s*p\s*\.?|maximum\s+retail(?:\s+price)?)
    (?:\s*[:=\-]?\s*)
    (?:₹|rs\.?|inr)?
    \s*
    (?P<value>
        \d{{1,6}}(?:,\d{{3}})*(?:\.\d{{1,2}})?
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
MRP_TAX_PATTERN = re.compile(
    r"""
    (?:incl\.?\s*of\s*all\s*tax(?:es)?)
    [^0-9]{0,20}
    (?P<value>
        \d{1,6}(?:,\d{3})*(?:\.\d{1,2})?
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
# Kept public because the vision service uses it to locate the font-height
# source token. Whitespace includes newlines, so ``100`` and ``g`` may reside
# in separate OCR fragments after text is joined.
NET_QUANTITY_PATTERN = re.compile(
    rf"\b(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>{_UNIT})\b",
    re.IGNORECASE,
)
NET_QUANTITY_LABEL_PATTERN = re.compile(
    rf"""
    \bnet\s*(?:weight|wt|qty|quantity)?\b
    (?:\s|[:=;.,-]){{0,18}}
    (?P<value>\d+(?:\.\d+)?)\s*(?P<unit>{_UNIT})\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Supports PKD/PKG/MFG/MFD, numeric and month-name dates, and MM/YYYY forms.
# ``\s`` deliberately allows labels and date values split across reconstructed
# OCR lines/blocks.
MFG_DATE_PATTERN = re.compile(
    r"""
    \b(?:pkd|pkg|packed|packing|PKD|PKG|MFG|MFD|mfg|mfd|manuf(?:actured|acturing)?)\.?
    (?:\s*(?:date|dt|on))?
    (?:\s|[:=;.,-]){0,12}
    (?P<date>
        \d{1,2}\s*[-/.]\s*(?:\d{1,2}|jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s*[-/.]\s*\d{2,4}
        |\d{1,2}\s*[-/.]\s*\d{2,4}
        |(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s*[-/.]\s*\d{2,4}
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
MFG_ADDRESS_PATTERN = re.compile(
    r"""
    (?:
        \b(?:manuf(?:actured)?|mfd|mkd|marketed|packed|repacked)\.?\s+(?:by|for)\b
      | \bregd\.?\s+off(?:ice)?\b
      | \baddress\b
    )
    (?:\s|[:=;,-]){0,10}
    (?P<address>
        (?:[A-Za-z0-9.,&\-()/|]+\s*){3,40}?  # Captures words, punctuation, and spaces
        \b\d{6}\b                           # Anchors exactly at a 6-digit PIN code
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
UNIT_NORMALIZATION = {
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
    "ml": "ml", "mls": "ml", "millilitre": "ml", "millilitres": "ml",
    "milliliter": "ml", "milliliters": "ml", "l": "l", "ltr": "l",
    "ltrs": "l", "litre": "l", "litres": "l", "liter": "l", "liters": "l",
}


def _normalise_number(value: str) -> float:
    return float(value.replace(",", ""))

def _clean_mrp_candidate(value: str) -> str | None:
    """
    Conservative cleanup for OCR'd MRP values.
    """
    value = value.strip().replace(",", "")

    # Common OCR confusion: O -> 0 when surrounded by digits
    value = re.sub(r"(?<=\d)[Oo](?=\d|$)", "0", value)

    # Only accept a genuine numeric value
    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", value):
        return None

    return value
def parse_regex_fields(raw_ocr_strings: list[str]) -> dict[str, Any]:
    """Extract MRP, quantity and packed/manufacturing date from complete text.

    Joining all reconstructed physical lines before matching is essential: OCR
    may emit ``MRP :`` / ``₹58`` or ``100`` / ``g`` as distinct fragments.
    """
    lines = [line.strip() for line in raw_ocr_strings if isinstance(line, str) and line.strip()]
    if not lines:
        return {}
    full_text = "\n".join(lines)
    print("\n--- RAW OCR TEXT FOR THIS IMAGE ---")
    print(full_text)
    print("-----------------------------------\n")
    extracted: dict[str, Any] = {}

    mrp_match = MRP_PATTERN.search(full_text) 
    if mrp_match is None:
      mrp_match = MRP_TAX_PATTERN.search(full_text)
    if mrp_match:
     cleaned = _clean_mrp_candidate(mrp_match.group("value"))

    if cleaned is not None:
        extracted["mrp"] = _normalise_number(cleaned)

    quantity_match = NET_QUANTITY_LABEL_PATTERN.search(full_text)
    if quantity_match is None:
        quantity_match = NET_QUANTITY_PATTERN.search(full_text)
    if quantity_match:
        extracted["net_quantity_value"] = float(quantity_match.group("value"))
        extracted["net_quantity_unit"] = UNIT_NORMALIZATION[quantity_match.group("unit").lower()]

    date_match = MFG_DATE_PATTERN.search(full_text)
    if date_match:
        extracted["mfg_date"] = re.sub(r"\s+", "", date_match.group("date"))
    address_match = MFG_ADDRESS_PATTERN.search(full_text)
    if address_match:
        raw_address = address_match.group("address")
        # Collapse scattered OCR newlines/spaces into a single clean string
        extracted["manufacturer_address"] = re.sub(r"\s+", " ", raw_address).strip()    
    return extracted
