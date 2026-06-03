"""Sensor entities for EWPE Smart."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfFrequency,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, PARAM_TEMP_SENSOR
from .coordinator import EwpeCoordinator
from .params_catalog import (
    EXTRA_SENSOR_DESCRIPTIONS,
    SensorDescriptionRef,
    TEMP_OFFSET_PARAMS,
    diagnostic_params,
)

_DEVICE_CLASS = {
    "temperature": SensorDeviceClass.TEMPERATURE,
    "humidity": SensorDeviceClass.HUMIDITY,
    "pm25": SensorDeviceClass.PM25,
}

_STATE_CLASS = {
    "measurement": SensorStateClass.MEASUREMENT,
}

_ENTITY_CATEGORY = {
    "diagnostic": EntityCategory.DIAGNOSTIC,
}

_UNIT = {
    "°C": UnitOfTemperature.CELSIUS,
    "%": PERCENTAGE,
    "µg/m³": "µg/m³",
    "Hz": UnitOfFrequency.HERTZ,
}


def supported_extra_sensor_descriptions(
    data: dict[str, Any],
) -> tuple[SensorDescriptionRef, ...]:
    """Return explicit sensor descriptions whose param appeared in a status reply."""
    return tuple(desc for desc in EXTRA_SENSOR_DESCRIPTIONS if desc.param in data)


def _slugify_param(param: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", param).strip("_").lower()
    return slug or "param"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EwpeCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    entities: list[SensorEntity] = [EwpeIndoorTempSensor(coordinator, entry)]
    entities.extend(
        EwpeExtraSensor(coordinator, entry, description)
        for description in supported_extra_sensor_descriptions(data)
    )
    entities.extend(
        EwpeDiagnosticSensor(coordinator, entry, param)
        for param in diagnostic_params(data)
    )
    async_add_entities(entities)


class _EwpeSensorBase(CoordinatorEntity[EwpeCoordinator], SensorEntity):
    """Shared device info for EWPE Smart sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EwpeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        device = coordinator.device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.mac or entry.entry_id)},
            name=device.name or entry.title,
            manufacturer=MANUFACTURER,
            model=device.info.get("model") if device.info else None,
            sw_version=device.info.get("ver") if device.info else None,
        )


class EwpeIndoorTempSensor(_EwpeSensorBase):
    """Reports the indoor temperature reading from the unit's TemSen sensor."""

    _attr_translation_key = "indoor_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: EwpeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        device = coordinator.device
        self._attr_unique_id = f"{device.mac}_indoor_temperature"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        value = data.get(PARAM_TEMP_SENSOR)
        if value is None or not -10 <= value <= 60:
            return None
        return float(value)


class EwpeExtraSensor(_EwpeSensorBase):
    """Named sensors mapped from the parameter catalog."""

    def __init__(
        self,
        coordinator: EwpeCoordinator,
        entry: ConfigEntry,
        description: SensorDescriptionRef,
    ) -> None:
        super().__init__(coordinator, entry)
        self._description = description
        device = coordinator.device
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = f"{device.mac}_{description.unique_id_suffix}"
        if description.device_class:
            self._attr_device_class = _DEVICE_CLASS.get(description.device_class)
        if description.value_kind == "text":
            self._attr_state_class = None
        elif description.state_class:
            self._attr_state_class = _STATE_CLASS.get(description.state_class)
        if description.entity_category:
            self._attr_entity_category = _ENTITY_CATEGORY.get(description.entity_category)
        if description.native_unit_of_measurement:
            unit = description.native_unit_of_measurement
            self._attr_native_unit_of_measurement = _UNIT.get(unit, unit)

    @property
    def native_value(self) -> float | int | str | None:
        value = (self.coordinator.data or {}).get(self._description.param)
        if value is None:
            return None
        if self._description.value_kind == "text":
            if isinstance(value, (list, dict)):
                return str(value)
            return str(value)
        if isinstance(value, (list, dict)):
            return str(value)
        param = self._description.param
        if param in TEMP_OFFSET_PARAMS and param != PARAM_TEMP_SENSOR:
            if not -40 <= value <= 60:
                return None
            return float(value)
        if self._description.percent_range:
            if not 0 <= value <= 100:
                return None
            return float(value)
        if self._description.device_class == "temperature":
            if not -40 <= value <= 60:
                return None
            return float(value)
        return int(value)


class EwpeDiagnosticSensor(_EwpeSensorBase):
    """Read-only fallback for wire params without an explicit entity mapping."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: EwpeCoordinator,
        entry: ConfigEntry,
        param: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._param = param
        device = coordinator.device
        slug = _slugify_param(param)
        self._attr_name = param
        self._attr_unique_id = f"{device.mac}_raw_{slug}"

    @property
    def native_value(self) -> int | None:
        value = (self.coordinator.data or {}).get(self._param)
        if value is None:
            return None
        return int(value)
