"""Growatt Select definitions for the SPF Offgrid device type."""
from __future__ import annotations

from .select_entity_description import GrowattSelectEntityDescription
from ..API.device_type.base import ATTR_OUTPUT_SOURCE_PRIORITY

OFFGRID_SELECT_TYPES: tuple[GrowattSelectEntityDescription, ...] = (
    GrowattSelectEntityDescription(
        key=ATTR_OUTPUT_SOURCE_PRIORITY,
        name="Output Source Priority",
        options=["SBU Priority", "Solar first (SOL)", "Utility first (UTI)", "Solar and Utility (SUB)"],
        option_to_value={
            "SBU Priority": 0,
            "Solar first (SOL)": 1,
            "Utility first (UTI)": 2,
            "Solar and Utility (SUB)": 3,
        },
        value_to_option={
            0: "SBU Priority",
            1: "Solar first (SOL)",
            2: "Utility first (UTI)",
            3: "Solar and Utility (SUB)",
        },
    ),
)
