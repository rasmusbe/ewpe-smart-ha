"""Number entities for EWPE Smart timers and sleep curve."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import EwpeCoordinator
from .params_catalog import NUMBER_DESCRIPTIONS, NumberDescriptionRef

_MODE = {
    "auto": NumberMode.AUTO,
    "box": NumberMode.BOX,
    "slider": NumberMode.SLIDER,
}

_UNIT = {
    "min": UnitOfTime.MINUTES,
    "°C": UnitOfTemperature.CELSIUS,
}


def supported_number_descriptions(
    data: dict[str, int],
) -> tuple[NumberDescriptionRef, ...]:
    """Return number descriptions whose param appeared in a status reply."""
    return tuple(desc for desc in NUMBER_DESCRIPTIONS if desc.param in data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EwpeCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    async_add_entities(
        EwpeNumberEntity(coordinator, entry, description)
        for description in supported_number_descriptions(data)
    )


class EwpeNumberEntity(CoordinatorEntity[EwpeCoordinator], NumberEntity):
    """Numeric parameter backed by a Gree protocol key."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EwpeCoordinator,
        entry: ConfigEntry,
        description: NumberDescriptionRef,
    ) -> None:
        super().__init__(coordinator)
        self._description = description
        device = coordinator.device
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = f"{device.mac}_{description.unique_id_suffix}"
        self._attr_native_min_value = description.native_min_value
        self._attr_native_max_value = description.native_max_value
        self._attr_native_step = description.native_step
        self._attr_mode = _MODE.get(description.mode, NumberMode.AUTO)
        if description.native_unit_of_measurement:
            unit = description.native_unit_of_measurement
            self._attr_native_unit_of_measurement = _UNIT.get(unit, unit)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.mac or entry.entry_id)},
            name=device.name or entry.title,
            manufacturer=MANUFACTURER,
            model=device.info.get("model") if device.info else None,
            sw_version=device.info.get("ver") if device.info else None,
        )

    @property
    def native_value(self) -> float | None:
        value = (self.coordinator.data or {}).get(self._description.param)
        if value is None:
            return None
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.device.set_state(
            {self._description.param: int(round(value))}
        )
        await self.coordinator.async_request_refresh()
