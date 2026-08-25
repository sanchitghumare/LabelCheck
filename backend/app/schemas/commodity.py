from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PackagedCommodity(BaseModel):
    """Normalized details extracted from a packaged-commodity label."""

    model_config = ConfigDict(str_strip_whitespace=True)

    mrp: Optional[float] = Field(default=None, ge=0)
    net_quantity_value: Optional[float] = Field(default=None, gt=0)
    net_quantity_unit: Optional[str] = None
    mfg_date: Optional[str] = None
    manufacturer_name: Optional[str] = None
    manufacturer_address: Optional[str] = None
    consumer_care_contact: Optional[str] = None