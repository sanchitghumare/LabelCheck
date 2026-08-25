from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RuleCheck(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    rule_name: str
    status: Literal["PASS", "FAIL"]
    details: str


class ComplianceVerdict(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    verdict: Literal["COMPLIANT", "NON_COMPLIANT"]
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    px_per_mm: float = Field(gt=0)
    rule_checks: list[RuleCheck]