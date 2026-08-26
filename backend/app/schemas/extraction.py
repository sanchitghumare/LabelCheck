from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.commodity import PackagedCommodity


class FieldEvidence(BaseModel):
    """Evidence supporting one extracted field."""

    model_config = ConfigDict(str_strip_whitespace=True)

    value: Any = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_text: Optional[str] = None
    source_type: Optional[str] = None


class ExtractionResult(BaseModel):
    """
    Complete extraction result.

    PackagedCommodity contains normalized values.
    This model additionally preserves confidence and evidence.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    commodity: PackagedCommodity
    confidence: dict[str, float] = Field(default_factory=dict)
    evidence: dict[str, FieldEvidence] = Field(default_factory=dict)