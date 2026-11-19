"""Growatt Switch definitions for the SPF Offgrid device type."""
from __future__ import annotations

from .switch_entity_description import GrowattSwitchEntityDescription
from ..API.device_type.base import ATTR_AC_CHARGE_CURRENT

OFFGRID_SWITCH_TYPES: tuple[GrowattSwitchEntityDescription, ...] = (
    GrowattSwitchEntityDescription(
        key=ATTR_AC_CHARGE_CURRENT,
        name="AC Charge Enable",
        icon="mdi:battery-charging",
        # Use a custom approach: 0 = off, any positive value = on
        # The actual on/off logic will be handled by a custom entity class
        state_on=1,   # placeholder - actual value managed by entity
        state_off=0,  # 0 disables AC charging
        mask=0,       # no mask, we'll handle logic in entity
    ),
)