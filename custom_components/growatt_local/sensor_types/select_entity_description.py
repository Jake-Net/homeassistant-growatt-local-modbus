"""Growatt Select Entity Description."""
from __future__ import annotations
from dataclasses import dataclass, field
from homeassistant.components.select import SelectEntityDescription


@dataclass
class GrowattSelectEntityDescription(SelectEntityDescription):
    """Describes a Growatt select entity."""

    key: str = ""
    name: str = ""
    options: list[str] = field(default_factory=list)
    # Maps option label -> register value
    option_to_value: dict[str, int] = field(default_factory=dict)
    # Maps register value -> option label
    value_to_option: dict[int, str] = field(default_factory=dict)
