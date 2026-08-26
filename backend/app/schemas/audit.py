from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.commodity import PackagedCommodity
from app.schemas.response import RuleCheck


class AuditRecord(BaseModel):
    """
    Persistent representation of a completed scan.

    AuditRecord contains everything required to reproduce and
    understand the result later. It is intentionally separate from
    the public ComplianceVerdict response.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    scan_id: str = Field(min_length=1)

    timestamp: datetime

    verdict: Literal["COMPLIANT", "NON_COMPLIANT"]

    px_per_mm: float = Field(gt=0)

    extracted_fields: PackagedCommodity

    rule_checks: list[RuleCheck] = Field(
        default_factory=list
    )

    extraction_confidence: dict[str, float] = Field(
        default_factory=dict
    )

    extraction_evidence: dict[str, object] = Field(
        default_factory=dict
    )

    ruleset_version: str = Field(min_length=1)

    calibration_fallback: bool = False

    barcode_data: str | None = None