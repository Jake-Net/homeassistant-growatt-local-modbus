from typing import Optional
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.const import (
    CONF_MODEL,
    CONF_NAME,
    CONF_TYPE,
)

from .API.const import DeviceTypes
from .API.device_type.storage_120 import ChargeDischargeMode, ChargeDischargePeriodValue
from .sensor_types.inverter import INVERTER_SELECT_TYPES_W_METER
from .sensor_types.storage import STORAGE_CHARGE_DISCHARGE_SELECT_TYPES
from .sensor_types.select_entity_description import GrowattSelectEntityDescription
from .sensor_types.offgrid_select import (
    OFFGRID_SELECT_TYPES,
    GrowattOffgridSelectEntityDescription,
)
from . import GrowattLocalCoordinator
from .const import (
    CONF_FIRMWARE,
    CONF_INVERTER_POWER_CONTROL,
    CONF_METER_CONNECTED,
    CONF_SERIAL_NUMBER,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GrowattLocalCoordinator = hass.data[DOMAIN][config_entry.data[CONF_SERIAL_NUMBER]]
    entities = []
    sensor_descriptions: list[GrowattSelectEntityDescription] = []
    supported_key_names = coordinator.growatt_api.get_register_names()

    if config_entry.data.get(CONF_METER_CONNECTED, False):
        for sensor in INVERTER_SELECT_TYPES_W_METER:
            if sensor.key not in supported_key_names:
                continue
            
            sensor_descriptions.append(sensor)
    
    device_type = DeviceTypes(config_entry.data[CONF_TYPE])
    if device_type in (DeviceTypes.HYBRID_120, DeviceTypes.HYBRID_120_TL_XH, DeviceTypes.STORAGE_120):
        for item in STORAGE_CHARGE_DISCHARGE_SELECT_TYPES:
            if item.key not in supported_key_names:
                continue

            entities.append(
                GrowattChargeDischargeSelectEntity(coordinator, description=item, entry=config_entry)
            )

    # jake-net: SPF off-grid output source priority select
    offgrid_descriptions: list[GrowattOffgridSelectEntityDescription] = []
    power_control = (
        config_entry.options.get(CONF_INVERTER_POWER_CONTROL, False)
        or config_entry.data.get(CONF_INVERTER_POWER_CONTROL, False)
    )
    if power_control and device_type == DeviceTypes.OFFGRID_SPF:
        for item in OFFGRID_SELECT_TYPES:
            if item.key not in supported_key_names:
                continue
            offgrid_descriptions.append(item)

    coordinator.get_keys_by_name(
        {sensor.key for sensor in sensor_descriptions}
        | {item.key for item in offgrid_descriptions},
        True,
    )

    entities.extend(
        [
            GrowattSelectEntity(
                coordinator, description=description, entry=config_entry
            )
            for description in sensor_descriptions
        ]
    )

    entities.extend(
        [
            GrowattOffgridSelectEntity(
                coordinator, description=description, entry=config_entry
            )
            for description in offgrid_descriptions
        ]
    )

    async_add_entities(entities, True)

class GrowattBaseSelectEntity(CoordinatorEntity, RestoreEntity, SelectEntity):
    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator, description.key)
        self.entity_description: GrowattSelectEntityDescription = description
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

    async def async_added_to_hass(self) -> None:
        """Call when entity is about to be added to Home Assistant."""
        await super().async_added_to_hass()

        if (state := await self.async_get_last_state()) is None:
            return

        if state.state not in self.options:
            return

        self._attr_current_option = state.state

class GrowattSelectEntity(GrowattBaseSelectEntity):

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (state := self.coordinator.data.get(self.entity_description.key)) is None:
            return

        if state not in self.options:
            return

        self._attr_current_option = state
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        value = next((k for k, v in self.entity_description.value_to_state_dict.items() if v == option), None)
        if value is None:
            return
        await self.coordinator.write_register(self.entity_description.key, value)

        self._attr_current_option = option
        self.async_write_ha_state()

class GrowattChargeDischargeSelectEntity(GrowattBaseSelectEntity):
    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator, entry, description)
        self.charge_discharge_period_state = ChargeDischargePeriodValue()

    @property
    def unique_id(self) -> Optional[str]:
        return f"{DOMAIN}_{self._config_entry.data[CONF_SERIAL_NUMBER]}_{self.entity_description.key}_mode"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (state := self.coordinator.data.get(self.entity_description.key)) is None:
            return

        self.charge_discharge_period_state = state
        self._attr_current_option = state.mode.value
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        if option not in list(ChargeDischargeMode):
            return
        
        self.charge_discharge_period_state.mode = ChargeDischargeMode(option)
        await self.coordinator.write_charge_discharge_period_registers(
                self.entity_description.key,
                self.charge_discharge_period_state
            )
        
        self._attr_current_option = option
        self.async_write_ha_state()


class GrowattOffgridSelectEntity(GrowattBaseSelectEntity):
    """SPF off-grid select entity.

    The output-source-priority register decodes to a plain integer, so the
    option<->value maps on the description are used rather than the
    ``value_to_state_dict`` shape used by the upstream selects.
    """

    def __init__(self, coordinator, description, entry):
        super().__init__(coordinator, entry, description)
        self._attr_options = description.options
        self._attr_current_option = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (state := self.coordinator.data.get(self.entity_description.key)) is None:
            return

        option = self.entity_description.value_to_option.get(int(state))
        if option is None:
            return

        self._attr_current_option = option
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        value = self.entity_description.option_to_value.get(option)
        if value is None:
            _LOGGER.error("Unknown option %s", option)
            return

        await self.coordinator.write_register(self.entity_description.key, value)
        self._attr_current_option = option
        self.async_write_ha_state()
        await self.coordinator.force_refresh()
