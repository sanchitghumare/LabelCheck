from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from app.schemas.commodity import PackagedCommodity


@dataclass(frozen=True)
class RuleResult:
    """Result produced by an individual compliance rule."""

    rule_name: str
    status: str
    details: str


RuleFunction = Callable[
    [PackagedCommodity, float, Optional[float]],
    RuleResult,
]


def _is_missing(value: object) -> bool:
    return value is None or (
        isinstance(value, str) and not value.strip()
    )


def _quantity_in_grams_or_ml(
    commodity: PackagedCommodity,
) -> Optional[float]:
    if (
        commodity.net_quantity_value is None
        or commodity.net_quantity_unit is None
    ):
        return None

    unit = commodity.net_quantity_unit.lower().strip()
    value = commodity.net_quantity_value

    conversions = {
        "g": 1.0,
        "kg": 1000.0,
        "ml": 1.0,
        "l": 1000.0,
    }

    multiplier = conversions.get(unit)

    return value * multiplier if multiplier is not None else None


def _required_font_height_mm(quantity: float) -> float:
    """
    Rule 9, Table I — normal printed declaration.

    <= 200 g/ml       -> 1 mm
    > 200 to <= 500   -> 2 mm
    > 500             -> 4 mm
    """

    if quantity <= 200:
        return 1.0

    if quantity <= 500:
        return 2.0

    return 4.0


def check_mandatory_declarations(
    commodity: PackagedCommodity,
    px_per_mm: float,
    net_quantity_font_height_px: Optional[float],
) -> RuleResult:
    """Rule 6 — Mandatory declarations."""

    mandatory_fields = {
        "MRP": commodity.mrp,
        "Net quantity value": commodity.net_quantity_value,
        "Net quantity unit": commodity.net_quantity_unit,
        "Manufacturing date": commodity.mfg_date,
        "Manufacturer address": commodity.manufacturer_address,
        "Consumer care contact": commodity.consumer_care_contact,
    }

    missing_fields = [
        field_name
        for field_name, value in mandatory_fields.items()
        if _is_missing(value)
    ]

    if missing_fields:
        return RuleResult(
            rule_name="Rule 6 — Mandatory declarations",
            status="FAIL",
            details=(
                "Missing mandatory declarations: "
                f"{', '.join(missing_fields)}."
            ),
        )

    return RuleResult(
        rule_name="Rule 6 — Mandatory declarations",
        status="PASS",
        details="All configured mandatory declarations are present.",
    )


def check_net_quantity_font_height(
    commodity: PackagedCommodity,
    px_per_mm: float,
    net_quantity_font_height_px: Optional[float],
    *,
    declaration_is_embossed: bool = False,
) -> RuleResult:
    """Rule 9 — Net quantity font height."""

    normalized_quantity = _quantity_in_grams_or_ml(commodity)

    if normalized_quantity is None:
        return RuleResult(
            rule_name="Rule 9 — Net quantity font height",
            status="FAIL",
            details=(
                "Cannot determine the Rule 9 threshold because net quantity "
                "is missing or uses an unsupported unit."
            ),
        )

    required_mm = _required_font_height_mm(normalized_quantity)

    if declaration_is_embossed:
        required_mm *= 2

    if net_quantity_font_height_px is None:
        return RuleResult(
            rule_name="Rule 9 — Net quantity font height",
            status="FAIL",
            details=(
                f"Minimum required height is {required_mm:.1f} mm, but no "
                "pixel-height measurement was supplied by the vision service."
            ),
        )

    measured_mm = net_quantity_font_height_px / px_per_mm

    status = "PASS" if measured_mm >= required_mm else "FAIL"

    return RuleResult(
        rule_name="Rule 9 — Net quantity font height",
        status=status,
        details=(
            f"Required: {required_mm:.1f} mm; "
            f"measured: {measured_mm:.2f} mm "
            f"({net_quantity_font_height_px:.2f} px at "
            f"{px_per_mm:.2f} px/mm)."
        ),
    )


RULES: tuple[RuleFunction, ...] = (
    check_mandatory_declarations,
    check_net_quantity_font_height,
)