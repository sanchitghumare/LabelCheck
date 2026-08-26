from __future__ import annotations

from typing import Literal, Optional, cast

from app.schemas.commodity import PackagedCommodity
from app.schemas.response import ComplianceVerdict, RuleCheck
from app.services.compliance.rules import (
    check_mandatory_declarations,
    check_net_quantity_font_height,
)


class ComplianceEngine:
    """Orchestrates deterministic LMPC compliance rules."""

    def evaluate(
        self,
        commodity: PackagedCommodity,
        px_per_mm: float,
        net_quantity_font_height_px: Optional[float] = None,
        *,
        declaration_is_embossed: bool = False,
    ) -> ComplianceVerdict:
        """Evaluate all configured compliance rules."""

        if px_per_mm <= 0:
            raise ValueError("px_per_mm must be greater than zero")

        rule_results = [
            check_mandatory_declarations(
                commodity,
                px_per_mm,
                net_quantity_font_height_px,
            ),
            check_net_quantity_font_height(
                commodity,
                px_per_mm,
                net_quantity_font_height_px,
                declaration_is_embossed=declaration_is_embossed,
            ),
        ]

        rule_checks = [
            RuleCheck(
                rule_name=result.rule_name,
                status=cast(Literal["PASS", "FAIL"], result.status),
                details=result.details,
            )
            for result in rule_results
        ]

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