"""Switch entities for EWPE Smart auxiliary features."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, POWER_OFF, POWER_ON
from .coordinator import EwpeCoordinator
from .entity_identity import config_device_identifier, config_device_mac
from .params_catalog import SWITCH_DESCRIPTIONS


@dataclass(frozen=True, kw_only=True)
class ResolvedSwitchDescription:
    """A switch group resolved to the wire param present on this device."""

    param: str
    unique_id_suffix: str
    translation_key: str


def supported_switch_descriptions(
    data: Mapping[str, int],
) -> tuple[ResolvedSwitchDescription, ...]:
    """Return one switch per wire key present in a status reply."""
    return tuple(
        ResolvedSwitchDescription(
            param=description.param,
            unique_id_suffix=description.unique_id_suffix,
            translation_key=description.translation_key,
        )
        for description in SWITCH_DESCRIPTIONS
        if description.param in data
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register switch entities supported by this device."""
    coordinator: EwpeCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    async_add_entities(
        EwpeSwitchEntity(coordinator, entry, description)
        for description in supported_switch_descriptions(data)
    )


class EwpeSwitchEntity(CoordinatorEntity[EwpeCoordinator], SwitchEntity):
    """Binary switch backed by a single Gree protocol parameter."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EwpeCoordinator,
        entry: ConfigEntry,
        description: ResolvedSwitchDescription,
    ) -> None:
        super().__init__(coordinator)
        self._description = description
        device = coordinator.device
        device_mac = config_device_mac(entry, device)
        self._attr_translation_key = description.translation_key
        # Fallback when translations are missing — avoids duplicate switch.ac_* ids.
        self._attr_name = description.param
        self._attr_unique_id = f"{device_mac}_{description.unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_device_identifier(entry, device))},
            name=device.name or entry.title,
            manufacturer=MANUFACTURER,
            model=device.info.get("model") if device.info else None,
            sw_version=device.info.get("ver") if device.info else None,
        )

    @property
    def is_on(self) -> bool | None:
        value = (self.coordinator.data or {}).get(self._description.param)
        if value is None:
            return None
        return bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send(POWER_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send(POWER_OFF)

    async def _send(self, value: int) -> None:
        await self.coordinator.device.set_state({self._description.param: value})
        await self.coordinator.async_request_refresh()
