from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.commodity import PackagedCommodity


RuleStatus = Literal["PASS", "FAIL"]


class RuleCheck(BaseModel):
    """Result of evaluating one compliance rule."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    rule_name: str = Field(min_length=1)
    status: RuleStatus
    details: str = Field(min_length=1)


class ComplianceVerdict(BaseModel):
    """
    Public API response for a completed commodity scan.

    This is intentionally smaller than AuditRecord. Internal
    extraction confidence, evidence, ruleset metadata, and
    persistence-specific fields belong to the audit model.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    verdict: Literal["COMPLIANT", "NON_COMPLIANT"]

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    px_per_mm: float = Field(gt=0)

    extracted_fields: PackagedCommodity

    rule_checks: list[RuleCheck] = Field(
        default_factory=list
    )