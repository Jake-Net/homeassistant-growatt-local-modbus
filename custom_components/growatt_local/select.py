"""Growatt Select platform."""
import logging
from typing import Optional
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import CONF_FIRMWARE, CONF_SERIAL_NUMBER, CONF_INVERTER_POWER_CONTROL, DOMAIN
from homeassistant.const import CONF_MODEL, CONF_NAME
from .API.const import DeviceTypes
from .sensor_types.offgrid_select import OFFGRID_SELECT_TYPES
from .sensor_types.select_entity_description import GrowattSelectEntityDescription

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][config_entry.data[CONF_SERIAL_NUMBER]]
    entities = []
    sensor_descriptions = []

    power_control = (
        config_entry.options.get(CONF_INVERTER_POWER_CONTROL, False)
        or config_entry.data.get(CONF_INVERTER_POWER_CONTROL, False)
    )

    if not power_control:
        return

    device_type_str = config_entry.data.get("type", "")

    try:
        device_type = DeviceTypes(device_type_str)
    except ValueError:
        return


    if device_type == DeviceTypes.OFFGRID_SPF:
        supported_key_names = coordinator.growatt_api.get_register_names()
        for sensor in OFFGRID_SELECT_TYPES:
            if sensor.key not in supported_key_names:
                continue
            sensor_descriptions.append(sensor)


    if not sensor_descriptions:
        return

    coordinator.get_keys_by_name({sensor.key for sensor in sensor_descriptions}, True)

    entities.extend([
        GrowattSelectEntity(coordinator, description=description, entry=config_entry)
        for description in sensor_descriptions
    ])

    async_add_entities(entities, True)


class GrowattSelectEntity(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, description, entry):
        super().__init__(coordinator, context=description.key)
        self.entity_description = description
        self._config_entry = entry
        self._attr_options = description.options
        self._attr_current_option = None
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
    def unique_id(self):
        return f"{DOMAIN}_{self._config_entry.data[CONF_SERIAL_NUMBER]}_{self.entity_description.key}"

    async def async_select_option(self, option: str) -> None:
        value = self.entity_description.option_to_value.get(option)
        if value is None:
            _LOGGER.error("Unknown option %s", option)
            return
        await self.coordinator.write_register(self.entity_description.key, value)
        self._attr_current_option = option
        self.async_write_ha_state()
        await self.coordinator.force_refresh()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update_from_coordinator()

    def _update_from_coordinator(self) -> None:
        if not self.coordinator.data:
            return
        state = self.coordinator.data.get(self.entity_description.key)
        if state is None:
            return
        option = self.entity_description.value_to_option.get(int(state))
        if option is None:
            return
        self._attr_current_option = option
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_from_coordinator()
