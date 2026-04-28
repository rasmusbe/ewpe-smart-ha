"""Indoor temperature sensor entity for EWPE Smart."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, PARAM_TEMP_SENSOR
from .coordinator import EwpeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EwpeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EwpeIndoorTempSensor(coordinator, entry)])


class EwpeIndoorTempSensor(CoordinatorEntity[EwpeCoordinator], SensorEntity):
    """Reports the indoor temperature reading from the unit's TemSen sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "indoor_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: EwpeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        device = coordinator.device
        self._attr_unique_id = f"{device.mac}_indoor_temperature"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.mac or entry.entry_id)},
            name=device.name or entry.title,
            manufacturer=MANUFACTURER,
            model=device.info.get("model") if device.info else None,
            sw_version=device.info.get("ver") if device.info else None,
        )

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        value = data.get(PARAM_TEMP_SENSOR)
        if value is None or not -10 <= value <= 60:
            return None
        return float(value)
