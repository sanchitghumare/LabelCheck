"""Deterministic extraction for common Legal Metrology declarations."""

from __future__ import annotations

import re
from typing import Any


_NUMBER = r"\d{1,6}(?:,\d{3})*(?:\.\d{1,2})?"

_UNIT = (
    r"kgs?|kilograms?|g|gms?|grams?|mls?|millilit(?:re|er)s?|"
    r"l|ltrs?|lit(?:re|er)s?"
)


# ---------------------------------------------------------------------------
# MRP patterns
# ---------------------------------------------------------------------------

MRP_PATTERN = re.compile(
    rf"""
    \b(?:m\s*\.?\s*r\s*\.?\s*p\s*\.?|maximum\s+retail(?:\s+price)?)
    (?:\s*[:=\-]?\s*)
    (?:₹|rs\.?|inr)?
    \s*
    (?P<value>{_NUMBER})
    """,
    re.IGNORECASE | re.VERBOSE,
)


MRP_TAX_PATTERN = re.compile(
    rf"""
    (?:incl\.?\s*of\s*all\s*tax(?:es)?)
    [^0-9]{{0,20}}
    (?P<value>{_NUMBER})
    """,
    re.IGNORECASE | re.VERBOSE,
)


# Currency immediately followed by a number.
# The OCR may turn ₹ into symbols such as ~, =, E, F, etc.
MRP_CURRENCY_PATTERN = re.compile(
    rf"""
    (?<![A-Za-z0-9])
    (?:₹|rs\.?|inr|[~?EF=])
    \s*
    (?P<value>{_NUMBER})
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Quantity
# ---------------------------------------------------------------------------

NET_QUANTITY_PATTERN = re.compile(
    rf"""
    \b
    (?P<value>\d+(?:\.\d+)?)
    \s*
    (?P<unit>{_UNIT})
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


NET_QUANTITY_LABEL_PATTERN = re.compile(
    rf"""
    \bnet\s*(?:weight|wt|qty|quantity)?\b
    (?:\s|[:=;.,-]){{0,18}}
    (?P<value>\d+(?:\.\d+)?)
    \s*
    (?P<unit>{_UNIT})
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Manufacturing / packing date
# ---------------------------------------------------------------------------

MFG_DATE_PATTERN = re.compile(
    r"""
    \b(?:pkd|pkg|packed|packing|mfg|mfd|manufactured|manufacturing)\.?
    (?:\s*(?:date|dt|on))?
    (?:\s|[:=;.,-]){0,12}
    (?P<date>
        \d{1,2}\s*[-/.]\s*
        (?:\d{1,2}|jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|
        apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|
        sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|
        dec(?:ember)?)
        \s*[-/.]\s*\d{2,4}

        |

        \d{1,2}\s*[-/.]\s*\d{2,4}

        |

        (?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|
        may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t)?(?:ember)?|
        oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)
        \s*[-/.]\s*\d{2,4}
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Manufacturer address
# ---------------------------------------------------------------------------

MFG_ADDRESS_PATTERN = re.compile(
    r"""
    (?:
        \b(?:manuf(?:actured)?|mfd|mkd|marketed|packed|repacked)
        \.?\s+(?:by|for)\b
        |
        \bregd\.?\s+off(?:ice)?\b
        |
        \baddress\b
    )
    (?:\s|[:=;,-]){0,10}
    (?P<address>
        (?:[A-Za-z0-9.,&\-()/|]+\s*){3,40}?
        \b\d{6}\b
    )
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_number(value: str) -> float:
    return float(value.replace(",", ""))


def _clean_mrp_candidate(value: str) -> str | None:
    """
    Conservative cleanup for OCR'd MRP values.

    Only small, well-understood OCR substitutions are corrected.
    We deliberately avoid aggressive digit replacement because MRP is
    legally important and a wrong value is worse than a missing value.
    """
    value = value.strip().replace(",", "")

    # Common OCR confusion: O/o -> 0 when surrounded by digits.
    value = re.sub(r"(?<=\d)[Oo](?=\d|$)", "0", value)

    # Remove accidental spaces around decimal points.
    value = re.sub(r"\s*\.\s*", ".", value)

    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", value):
        return None

    return value


def _mrp_candidate_score(
    *,
    source: str,
    value: float,
    text: str,
    start: int,
    end: int,
) -> int:
    """
    Score an MRP candidate.

    This is intentionally heuristic. It is not the final confidence
    system; confidence.py will later combine OCR confidence, spatial
    evidence and extraction signals.
    """
    score = 0

    # Strongest evidence: explicit MRP label.
    if source == "mrp_label":
        score += 100

    # Very strong evidence: "incl. of all taxes".
    elif source == "tax_label":
        score += 85

    # Currency-only evidence is weaker.
    elif source == "currency":
        score += 45

    # Prefer realistic positive retail prices.
    if value > 0:
        score += 5

    # Suspiciously tiny values are more likely OCR noise.
    if value < 5:
        score -= 15
    elif value < 10:
        score -= 5

    # MRP generally has a monetary-looking decimal value.
    if "." in text[start:end]:
        score += 5

    # Avoid candidates that are immediately surrounded by letters.
    before = text[max(0, start - 1):start]
    after = text[end:end + 1]

    if before.isalpha():
        score -= 20

    if after.isalpha():
        score -= 20

    return score


def _extract_mrp_candidates(full_text: str) -> list[dict[str, Any]]:
    """
    Find every plausible MRP candidate instead of accepting the first match.

    Returns candidates containing:
        value
        source
        score
        raw_value
        start
        end
    """
    candidates: list[dict[str, Any]] = []

    patterns = (
        ("mrp_label", MRP_PATTERN),
        ("tax_label", MRP_TAX_PATTERN),
        ("currency", MRP_CURRENCY_PATTERN),
    )

    for source, pattern in patterns:
        for match in pattern.finditer(full_text):
            raw_value = match.group("value")
            cleaned = _clean_mrp_candidate(raw_value)

            if cleaned is None:
                continue

            value = _normalise_number(cleaned)

            score = _mrp_candidate_score(
                source=source,
                value=value,
                text=full_text,
                start=match.start("value"),
                end=match.end("value"),
            )

            candidates.append(
                {
                    "value": value,
                    "source": source,
                    "score": score,
                    "raw_value": raw_value,
                    "start": match.start("value"),
                    "end": match.end("value"),
                }
            )

    # Highest score first.
    candidates.sort(
        key=lambda candidate: candidate["score"],
        reverse=True,
    )

    return candidates


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_regex_fields(raw_ocr_strings: list[str]) -> dict[str, Any]:
    """
    Extract common Legal Metrology fields from OCR text.

    The parser remains deterministic. It does not use an LLM and does not
    decide legal compliance.

    MRP extraction is candidate-based so that the first numeric match is not
    automatically trusted.
    """
    lines = [
        line.strip()
        for line in raw_ocr_strings
        if isinstance(line, str) and line.strip()
    ]

    if not lines:
        return {}

    full_text = "\n".join(lines)

    print("\n--- RAW OCR TEXT FOR THIS IMAGE ---")
    print(full_text)
    print("-----------------------------------\n")

    extracted: dict[str, Any] = {}

    # -----------------------------------------------------------------------
    # MRP
    # -----------------------------------------------------------------------

    mrp_candidates = _extract_mrp_candidates(full_text)

    if mrp_candidates:
        best_mrp = mrp_candidates[0]

        extracted["mrp"] = best_mrp["value"]

        # Temporary metadata for the upcoming confidence/evidence layer.
        # Existing consumers can continue using extracted["mrp"].
        extracted["_mrp_meta"] = {
            "source": best_mrp["source"],
            "score": best_mrp["score"],
            "raw_value": best_mrp["raw_value"],
            "start": best_mrp["start"],
            "end": best_mrp["end"],
            "candidate_count": len(mrp_candidates),
        }

    # -----------------------------------------------------------------------
    # Net quantity
    # -----------------------------------------------------------------------

    quantity_match = NET_QUANTITY_LABEL_PATTERN.search(full_text)

    if quantity_match is None:
        quantity_match = NET_QUANTITY_PATTERN.search(full_text)

    if quantity_match:
        extracted["net_quantity_value"] = float(
            quantity_match.group("value")
        )

        extracted["net_quantity_unit"] = UNIT_NORMALIZATION[
            quantity_match.group("unit").lower()
        ]

    # -----------------------------------------------------------------------
    # Manufacturing / packing date
    # -----------------------------------------------------------------------

    date_match = MFG_DATE_PATTERN.search(full_text)

    if date_match:
        extracted["mfg_date"] = re.sub(
            r"\s+",
            "",
            date_match.group("date"),
        )

    # -----------------------------------------------------------------------
    # Manufacturer address
    # -----------------------------------------------------------------------

    address_match = MFG_ADDRESS_PATTERN.search(full_text)

    if address_match:
        raw_address = address_match.group("address")

        extracted["manufacturer_address"] = re.sub(
            r"\s+",
            " ",
            raw_address,
        ).strip()

    return extracted