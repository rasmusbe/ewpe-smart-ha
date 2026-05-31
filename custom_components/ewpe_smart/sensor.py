"""Sensor entities for EWPE Smart."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    PARAM_FAULT,
    PARAM_HUMIDITY,
    PARAM_OUTDOOR_TEMP,
    PARAM_TEMP_SENSOR,
)
from .coordinator import EwpeCoordinator


@dataclass(frozen=True, kw_only=True)
class EwpeSensorDescription:
    """Maps a sensor entity to a Gree protocol parameter."""

    param: str
    unique_id_suffix: str
    translation_key: str
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    entity_category: EntityCategory | None = None
    native_unit_of_measurement: str | None = None


EXTRA_SENSOR_DESCRIPTIONS: tuple[EwpeSensorDescription, ...] = (
    EwpeSensorDescription(
        param=PARAM_OUTDOOR_TEMP,
        unique_id_suffix="outdoor_temperature",
        translation_key="outdoor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    EwpeSensorDescription(
        param=PARAM_HUMIDITY,
        unique_id_suffix="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
    ),
    EwpeSensorDescription(
        param=PARAM_FAULT,
        unique_id_suffix="fault",
        translation_key="fault",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


def supported_extra_sensor_descriptions(
    data: Mapping[str, int],
) -> tuple[EwpeSensorDescription, ...]:
    """Return extra sensor descriptions whose param appeared in a status reply."""
    return tuple(desc for desc in EXTRA_SENSOR_DESCRIPTIONS if desc.param in data)


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
    """Additional sensors discovered via device status cols."""

    def __init__(
        self,
        coordinator: EwpeCoordinator,
        entry: ConfigEntry,
        description: EwpeSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self._description = description
        device = coordinator.device
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = f"{device.mac}_{description.unique_id_suffix}"
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_entity_category = description.entity_category
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement

    @property
    def native_value(self) -> float | int | None:
        value = (self.coordinator.data or {}).get(self._description.param)
        if value is None:
            return None
        if self._description.param == PARAM_OUTDOOR_TEMP:
            if not -40 <= value <= 60:
                return None
            return float(value)
        if self._description.param == PARAM_HUMIDITY:
            if not 0 <= value <= 100:
                return None
            return float(value)
        return int(value)
