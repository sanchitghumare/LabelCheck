from __future__ import annotations

from typing import Optional

from app.schemas.commodity import PackagedCommodity
from app.schemas.response import ComplianceVerdict, RuleCheck


class ComplianceEngine:
    """Deterministic LMPC compliance checks. No AI is used here."""

    @staticmethod
    def _is_missing(value: object) -> bool:
        return value is None or (isinstance(value, str) and not value.strip())

    @staticmethod
    def _quantity_in_grams_or_ml(commodity: PackagedCommodity) -> Optional[float]:
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

    @staticmethod
    def _required_font_height_mm(quantity: float) -> float:
        """
        Rule 9, Table I — normal printed declaration:
        <= 200 g/ml: 1 mm
        > 200 to <= 500 g/ml: 2 mm
        > 500 g/ml: 4 mm
        """
        if quantity <= 200:
            return 1.0
        if quantity <= 500:
            return 2.0
        return 4.0

    def evaluate(
        self,
        commodity: PackagedCommodity,
        px_per_mm: float,
        net_quantity_font_height_px: Optional[float] = None,
        *,
        declaration_is_embossed: bool = False,
    ) -> ComplianceVerdict:
        """
        Evaluate mandatory declarations and net-quantity font height.

        `net_quantity_font_height_px` must be measured by the separate vision
        service. Passing no measurement produces a deterministic Rule 9 failure,
        because compliance cannot be established from calibration alone.
        """
        if px_per_mm <= 0:
            raise ValueError("px_per_mm must be greater than zero")

        rule_checks: list[RuleCheck] = []

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
            if self._is_missing(value)
        ]

        if missing_fields:
            rule_checks.append(
                RuleCheck(
                    rule_name="Rule 6 — Mandatory declarations",
                    status="FAIL",
                    details=f"Missing mandatory declarations: {', '.join(missing_fields)}.",
                )
            )
        else:
            rule_checks.append(
                RuleCheck(
                    rule_name="Rule 6 — Mandatory declarations",
                    status="PASS",
                    details="All configured mandatory declarations are present.",
                )
            )

        normalized_quantity = self._quantity_in_grams_or_ml(commodity)

        if normalized_quantity is None:
            rule_checks.append(
                RuleCheck(
                    rule_name="Rule 9 — Net quantity font height",
                    status="FAIL",
                    details=(
                        "Cannot determine the Rule 9 threshold because net quantity "
                        "is missing or uses an unsupported unit."
                    ),
                )
            )
        else:
            required_mm = self._required_font_height_mm(normalized_quantity)
            if declaration_is_embossed:
                required_mm *= 2

            if net_quantity_font_height_px is None:
                rule_checks.append(
                    RuleCheck(
                        rule_name="Rule 9 — Net quantity font height",
                        status="FAIL",
                        details=(
                            f"Minimum required height is {required_mm:.1f} mm, but no "
                            "pixel-height measurement was supplied by the vision service."
                        ),
                    )
                )
            else:
                measured_mm = net_quantity_font_height_px / px_per_mm
                status = "PASS" if measured_mm >= required_mm else "FAIL"

                rule_checks.append(
                    RuleCheck(
                        rule_name="Rule 9 — Net quantity font height",
                        status=status,
                        details=(
                            f"Required: {required_mm:.1f} mm; "
                            f"measured: {measured_mm:.2f} mm "
                            f"({net_quantity_font_height_px:.2f} px at "
                            f"{px_per_mm:.2f} px/mm)."
                        ),
                    )
                )

        verdict = (
            "COMPLIANT"
            if all(check.status == "PASS" for check in rule_checks)
            else "NON_COMPLIANT"
        )

        return ComplianceVerdict(
            verdict=verdict,
            px_per_mm=px_per_mm,
            rule_checks=rule_checks,
            extracted_fields=commodity,
        )