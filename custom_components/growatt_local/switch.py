import logging
from datetime import timedelta
from typing import Any, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_MODEL,
    CONF_NAME,
    CONF_TYPE,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from .API.const import DeviceTypes
from .API.device_type.base import ATTR_AC_CHARGE_CURRENT
from .API.device_type.storage_120 import ChargeDischargePeriodValue
from .const import (
    CONF_FIRMWARE,
    CONF_SERIAL_NUMBER,
    CONF_INVERTER_POWER_CONTROL,
    DOMAIN,
)
from .sensor_types.inverter import INVERTER_POWER_SWITCH
from .sensor_types.storage import STORAGE_SWITCH_TYPES, STORAGE_CHARGE_DISCHARGE_SWITCH_TYPES
from .sensor_types.switch_entity_description import GrowattSwitchEntityDescription

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][config_entry.data[CONF_SERIAL_NUMBER]]
    entities = []
    sensor_descriptions: list[GrowattSwitchEntityDescription] = []
    supported_key_names = coordinator.growatt_api.get_register_names()

    device_type = DeviceTypes(config_entry.data[CONF_TYPE])

    if config_entry.options.get(CONF_INVERTER_POWER_CONTROL, False):
        sensor_descriptions.append(INVERTER_POWER_SWITCH) 

    if device_type in (DeviceTypes.HYBRID_120, DeviceTypes.HYBRID_120_TL_XH, DeviceTypes.STORAGE_120):
        for sensor in STORAGE_SWITCH_TYPES:
            if sensor.key not in supported_key_names:
                continue
            
            sensor_descriptions.append(sensor)

        for item in STORAGE_CHARGE_DISCHARGE_SWITCH_TYPES:
            if sensor.key not in supported_key_names:
                continue

            entities.append(
                GrowattChargeDischargeEntity(coordinator, description=item, entry=config_entry)
            )

    # jake-net: SPF off-grid AC-charge switch over holding register 38
    if device_type == DeviceTypes.OFFGRID_SPF:
        if ATTR_AC_CHARGE_CURRENT in supported_key_names:
            entities.append(
                GrowattOffgridACChargeSwitch(coordinator, entry=config_entry)
            )

    coordinator.get_keys_by_name({sensor.key for sensor in sensor_descriptions}, True)

    entities.extend(
        [
            GrowattSwitchEntity(
                coordinator, description=description, entry=config_entry
            )
            for description in sensor_descriptions
        ]
    )

    async_add_entities(entities, True)


class GrowattBaseSwitchEntity(CoordinatorEntity, RestoreEntity, SwitchEntity):
    """A base Growatt switch entity using CoordinatorEntity."""

    def __init__(self, coordinator, description, entry):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, description.key)
        self.entity_description: GrowattSwitchEntityDescription = description
        self._config_entry = entry

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_SERIAL_NUMBER])},
            manufacturer="Growatt",
            model=entry.data[CONF_MODEL],
            sw_version=entry.data[CONF_FIRMWARE],
            name=entry.options[CONF_NAME],
        )

    @property
    def name(self):
        return f"{self._config_entry.options[CONF_NAME]} {self.entity_description.name}"

    @property
    def unique_id(self) -> Optional[str]:
        return f"{DOMAIN}_{self._config_entry.data[CONF_SERIAL_NUMBER]}_{self.entity_description.key}"

    @callback
    def _handle_midnight_update(self) -> None:
        self._handle_coordinator_update()


class GrowattSwitchEntity(GrowattBaseSwitchEntity):
    """An entity using CoordinatorEntity."""

    def __init__(self, coordinator, description, entry):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, description, entry)
        self.masked_value = 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.masked_value != 0:
            await self.coordinator.write_register(
                self.entity_description.key,
                self.masked_value + self.entity_description.state_on
            )
        else:
            await self.coordinator.write_register(
                self.entity_description.key,
                self.entity_description.state_on
            )

        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.masked_value != 0:
            await self.coordinator.write_register(
                self.entity_description.key,
                self.masked_value + self.entity_description.state_off
            )
        else:
            await self.coordinator.write_register(
                self.entity_description.key,
                self.entity_description.state_off
            )

        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Call when entity is about to be added to Home Assistant."""
        await super().async_added_to_hass()
        if state := await self.async_get_last_state():
            self._attr_is_on = state.state == STATE_ON

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (state := self.coordinator.data.get(self.entity_description.key)) is None:
            _LOGGER.debug("Device type %s state %s", self._attr_unique_id, state)
            return

        _LOGGER.debug("Device type %s state %s", self._attr_unique_id, state)

        value = int(state)

        if self.entity_description.mask != 0:
            self._attr_is_on = value & self.entity_description.mask
            self.masked_value = value ^ self._attr_is_on

        else:    
            self._attr_is_on = value >= 1

        self.async_write_ha_state()

    @callback
    def _handle_midnight_update(self) -> None:
        self._handle_coordinator_update()


class GrowattChargeDischargeEntity(GrowattBaseSwitchEntity):
    """A specific Growatt charge discharge switch entity using CoordinatorEntity."""

    def __init__(self, coordinator, description, entry):
        """Pass coordinator to GrowattDeviceEntity."""
        super().__init__(coordinator, description, entry)
        self.charge_discharge_period_state = ChargeDischargePeriodValue()

    @property
    def unique_id(self) -> Optional[str]:
            return f"{DOMAIN}_{self._config_entry.data[CONF_SERIAL_NUMBER]}_{self.entity_description.key}_enable"

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.charge_discharge_period_state.enable = True
        _LOGGER.debug("Turn on Device type %s, full state %s", self._attr_unique_id, self.charge_discharge_period_state)
        await self.coordinator.write_charge_discharge_period_registers(
                self.entity_description.key,
                self.charge_discharge_period_state
            )

        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.charge_discharge_period_state.enable = False
        _LOGGER.debug("Turn off Device type %s, full state %s", self._attr_unique_id, self.charge_discharge_period_state)
        await self.coordinator.write_charge_discharge_period_registers(
                self.entity_description.key,
                self.charge_discharge_period_state
            )
        
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Call when entity is about to be added to Home Assistant."""
        await super().async_added_to_hass()
        if state := await self.async_get_last_state():
            self._attr_is_on = state.state == STATE_ON

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (state := self.coordinator.data.get(self.entity_description.key)) is None:
            _LOGGER.debug("Device type %s state %s", self._attr_unique_id, state)
            return

        _LOGGER.debug("Device type %s state %s", self._attr_unique_id, state)

        self.charge_discharge_period_state = state
        self._attr_is_on = state.enable

        self.async_write_ha_state()


class GrowattOffgridACChargeSwitch(CoordinatorEntity, RestoreEntity, SwitchEntity):
    """Enable/disable AC (grid) charging on a Growatt SPF off-grid inverter.

    Uses the AC Charge Current holding register (register 38):
    - ON: restore the last non-zero charge current (default 20 A)
    - OFF: set the charge current to 0 (disables AC charging)
    """

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, context=ATTR_AC_CHARGE_CURRENT)
        self._config_entry = entry
        self._stored_charge_current = 20  # Default charge current in Amps
        self._attr_name = f"{entry.options[CONF_NAME]} AC Charge Enable"
        self._attr_unique_id = f"{DOMAIN}_{entry.data[CONF_SERIAL_NUMBER]}_ac_charge_enable"
        self._attr_icon = "mdi:battery-charging"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_SERIAL_NUMBER])},
            manufacturer="Growatt",
            model=entry.data[CONF_MODEL],
            sw_version=entry.data[CONF_FIRMWARE],
            name=entry.options[CONF_NAME],
        )

    @property
    def is_on(self) -> bool:
        return self._attr_is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable AC charging by restoring the stored charge current value."""
        _LOGGER.info("Enabling AC charging with current: %dA", self._stored_charge_current)
        await self.coordinator.write_register(ATTR_AC_CHARGE_CURRENT, self._stored_charge_current)
        self._attr_is_on = True
        self.async_write_ha_state()
        await self.coordinator.force_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable AC charging by setting the charge current to 0."""
        current_value = self.coordinator.data.get(ATTR_AC_CHARGE_CURRENT)
        if current_value is not None and int(current_value) > 0:
            self._stored_charge_current = int(current_value)
            _LOGGER.info("Stored AC charge current: %dA", self._stored_charge_current)

        _LOGGER.info("Disabling AC charging (setting current to 0)")
        await self.coordinator.write_register(ATTR_AC_CHARGE_CURRENT, 0)
        self._attr_is_on = False
        self.async_write_ha_state()
        await self.coordinator.force_refresh()

    async def async_added_to_hass(self) -> None:
        """Call when entity is about to be added to Home Assistant."""
        await super().async_added_to_hass()
        if state := await self.async_get_last_state():
            self._attr_is_on = state.state == STATE_ON
            if state.attributes.get("stored_charge_current"):
                self._stored_charge_current = state.attributes["stored_charge_current"]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (state := self.coordinator.data.get(ATTR_AC_CHARGE_CURRENT)) is None:
            return

        value = int(state)
        # Switch is ON if charge current > 0
        self._attr_is_on = value > 0

        # If value > 0, update our stored value (user may have changed it via number entity)
        if value > 0:
            self._stored_charge_current = value

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "stored_charge_current": self._stored_charge_current,
            "current_charge_current": self.coordinator.data.get(ATTR_AC_CHARGE_CURRENT, 0),
        }