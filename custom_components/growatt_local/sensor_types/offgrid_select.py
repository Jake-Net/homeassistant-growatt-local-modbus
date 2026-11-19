"""Growatt Select definitions for the SPF Offgrid device type.

jake-net fork: upstream manages ``GrowattSelectEntityDescription`` in
``select_entity_description.py`` with a ``value_to_state_dict`` shape. The
off-grid output-source-priority register decodes to a plain integer, so this
module keeps a small dedicated description with explicit option<->value maps.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from homeassistant.components.select import SelectEntityDescription

from ..API.device_type.base import ATTR_OUTPUT_SOURCE_PRIORITY


@dataclass
class GrowattOffgridSelectEntityDescription(SelectEntityDescription):
    """Describes an SPF off-grid select entity."""

    key: str = ""
    name: str = ""
    options: list[str] = field(default_factory=list)
    # Maps option label -> register value
    option_to_value: dict[str, int] = field(default_factory=dict)
    # Maps register value -> option label
    value_to_option: dict[int, str] = field(default_factory=dict)


OFFGRID_SELECT_TYPES: tuple[GrowattOffgridSelectEntityDescription, ...] = (
    GrowattOffgridSelectEntityDescription(
        key=ATTR_OUTPUT_SOURCE_PRIORITY,
        name="Output Source Priority",
        options=[
            "SBU Priority",
            "Solar first (SOL)",
            "Utility first (UTI)",
            "Solar and Utility (SUB)",
        ],
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
