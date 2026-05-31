"""Select entities for EWPE Smart swing controls."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    PARAM_SWING_HORIZONTAL,
    PARAM_SWING_VERTICAL,
    SWING_HORIZONTAL_DEVICE_TO_OPTION,
    SWING_VERTICAL_DEVICE_TO_OPTION,
)
from .coordinator import EwpeCoordinator


@dataclass(frozen=True, kw_only=True)
class EwpeSelectDescription:
    """Maps a select entity to a Gree protocol parameter."""

    param: str
    unique_id_suffix: str
    translation_key: str
    device_to_option: dict[int, str]


SELECT_DESCRIPTIONS: tuple[EwpeSelectDescription, ...] = (
    EwpeSelectDescription(
        param=PARAM_SWING_HORIZONTAL,
        unique_id_suffix="swing_horizontal",
        translation_key="swing_horizontal",
        device_to_option=SWING_HORIZONTAL_DEVICE_TO_OPTION,
    ),
    EwpeSelectDescription(
        param=PARAM_SWING_VERTICAL,
        unique_id_suffix="swing_vertical",
        translation_key="swing_vertical",
        device_to_option=SWING_VERTICAL_DEVICE_TO_OPTION,
    ),
)


def supported_select_descriptions(
    data: Mapping[str, int],
) -> tuple[EwpeSelectDescription, ...]:
    """Return select descriptions whose param appeared in a status reply."""
    return tuple(desc for desc in SELECT_DESCRIPTIONS if desc.param in data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register select entities supported by this device."""
    coordinator: EwpeCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    async_add_entities(
        EwpeSelectEntity(coordinator, entry, description)
        for description in supported_select_descriptions(data)
    )


class EwpeSelectEntity(CoordinatorEntity[EwpeCoordinator], SelectEntity):
    """Swing mode select backed by a single Gree protocol parameter."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EwpeCoordinator,
        entry: ConfigEntry,
        description: EwpeSelectDescription,
    ) -> None:
        super().__init__(coordinator)
        self._description = description
        device = coordinator.device
        self._option_to_device = {
            label: value for value, label in description.device_to_option.items()
        }
        self._attr_translation_key = description.translation_key
        self._attr_options = list(description.device_to_option.values())
        self._attr_unique_id = f"{device.mac}_{description.unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.mac or entry.entry_id)},
            name=device.name or entry.title,
            manufacturer=MANUFACTURER,
            model=device.info.get("model") if device.info else None,
            sw_version=device.info.get("ver") if device.info else None,
        )

    @property
    def current_option(self) -> str | None:
        value = (self.coordinator.data or {}).get(self._description.param)
        if value is None:
            return None
        return self._description.device_to_option.get(int(value))

    async def async_select_option(self, option: str) -> None:
        device_value = self._option_to_device.get(option)
        if device_value is None:
            raise ValueError(f"Unsupported option: {option}")
        await self.coordinator.device.set_state(
            {self._description.param: device_value}
        )
        await self.coordinator.async_request_refresh()
