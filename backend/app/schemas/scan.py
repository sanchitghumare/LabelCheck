from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.commodity import PackagedCommodity
from app.schemas.extraction import FieldEvidence
from app.schemas.response import RuleCheck


class ScanResult(BaseModel):
    """
    Complete internal result produced by the Python scan engine.

    This is used by the application layer to persist an audit.
    It is intentionally separate from the public ComplianceVerdict.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    verdict: str
    timestamp: datetime

    px_per_mm: float = Field(gt=0)

    extracted_fields: PackagedCommodity

    rule_checks: list[RuleCheck] = Field(
        default_factory=list
    )

    extraction_confidence: dict[str, float] = Field(
        default_factory=dict
    )

    extraction_evidence: dict[str, FieldEvidence] = Field(
        default_factory=dict
    )

    ruleset_version: str = Field(min_length=1)

    calibration_fallback: bool = False

    barcode_data: str | None = None