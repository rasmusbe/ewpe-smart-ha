"""Binary sensor entities for EWPE Smart."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import EwpeCoordinator
from .params_catalog import (
    BINARY_SENSOR_DESCRIPTIONS,
    BinarySensorDescriptionRef,
    param_disabled_by_default,
)

_DEVICE_CLASS = {
    "problem": BinarySensorDeviceClass.PROBLEM,
    "motion": BinarySensorDeviceClass.MOTION,
    "running": BinarySensorDeviceClass.RUNNING,
}


def supported_binary_sensor_descriptions(
    data: dict[str, int],
) -> tuple[BinarySensorDescriptionRef, ...]:
    """Return binary sensor descriptions whose param appeared in a status reply."""
    return tuple(desc for desc in BINARY_SENSOR_DESCRIPTIONS if desc.param in data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EwpeCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    async_add_entities(
        EwpeBinarySensor(coordinator, entry, description)
        for description in supported_binary_sensor_descriptions(data)
    )


class EwpeBinarySensor(CoordinatorEntity[EwpeCoordinator], BinarySensorEntity):
    """Binary sensor backed by a Gree protocol parameter."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EwpeCoordinator,
        entry: ConfigEntry,
        description: BinarySensorDescriptionRef,
    ) -> None:
        super().__init__(coordinator)
        self._description = description
        device = coordinator.device
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = f"{device.mac}_{description.unique_id_suffix}"
        if description.device_class:
            self._attr_device_class = _DEVICE_CLASS.get(description.device_class)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.mac or entry.entry_id)},
            name=device.name or entry.title,
            manufacturer=MANUFACTURER,
            model=device.info.get("model") if device.info else None,
            sw_version=device.info.get("ver") if device.info else None,
        )
        if param_disabled_by_default(description.param):
            self._attr_disabled_by_default = True

    @property
    def is_on(self) -> bool | None:
        value = (self.coordinator.data or {}).get(self._description.param)
        if value is None:
            return None
        return bool(value)
