"""Select entities for EWPE Smart."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    FAN_SPEED_AUTO,
    FAN_SPEED_HIGH,
    FAN_SPEED_LOW,
    FAN_SPEED_MEDIUM,
    FAN_SPEED_MEDIUM_HIGH,
    FAN_SPEED_MEDIUM_LOW,
    MANUFACTURER,
    PARAM_FAN_SPEED,
    PARAM_QUIET,
    PARAM_SUB_ZONE_SWING_LEFT,
    PARAM_SUB_ZONE_SWING_RIGHT,
    PARAM_SUB_ZONE_SWING_UD,
    PARAM_SWING_HORIZONTAL,
    PARAM_SWING_VERTICAL,
    PARAM_TUR,
    POWER_OFF,
    POWER_ON,
    QUIET_MODE_ON,
    SWING_HORIZONTAL_DEVICE_TO_OPTION,
    SWING_VERTICAL_DEVICE_TO_OPTION,
    WIND_SPEED_FAN_TO_OPTION,
)
from .coordinator import EwpeCoordinator
from .params_catalog import param_disabled_by_default

WIND_SPEED_BASE_OPTIONS: tuple[str, ...] = (
    "auto",
    "low",
    "medium_low",
    "medium",
    "medium_high",
    "high",
)


def supported_wind_speed_options(data: Mapping[str, int]) -> tuple[str, ...]:
    """Return wind speed options supported by this device."""
    options = list(WIND_SPEED_BASE_OPTIONS)
    if PARAM_QUIET in data:
        options.append("quiet")
    if PARAM_TUR in data:
        options.append("turbo")
    return tuple(options)


def wind_speed_option_from_status(data: Mapping[str, int]) -> str | None:
    """Derive the active wind speed option from coordinator data."""
    if data.get(PARAM_TUR) == POWER_ON:
        return "turbo"
    quiet = data.get(PARAM_QUIET)
    if quiet not in (None, POWER_OFF):
        return "quiet"
    speed = data.get(PARAM_FAN_SPEED)
    if speed is None:
        return None
    return WIND_SPEED_FAN_TO_OPTION.get(int(speed))


def wind_speed_params_for_option(option: str) -> dict[str, int]:
    """Build a cmd packet that selects exactly one wind speed mode."""
    if option == "turbo":
        # Do not set WdSpd — the unit keeps the last fan step while turbo is active.
        return {PARAM_TUR: POWER_ON, PARAM_QUIET: POWER_OFF}
    if option == "quiet":
        # Do not set WdSpd — the unit keeps the last fan step while quiet is active.
        return {PARAM_QUIET: QUIET_MODE_ON, PARAM_TUR: POWER_OFF}
    fan_speeds: dict[str, int] = {
        "auto": FAN_SPEED_AUTO,
        "low": FAN_SPEED_LOW,
        "medium_low": FAN_SPEED_MEDIUM_LOW,
        "medium": FAN_SPEED_MEDIUM,
        "medium_high": FAN_SPEED_MEDIUM_HIGH,
        "high": FAN_SPEED_HIGH,
    }
    if option not in fan_speeds:
        raise ValueError(f"Unsupported wind speed option: {option}")
    return {
        PARAM_FAN_SPEED: fan_speeds[option],
        PARAM_QUIET: POWER_OFF,
        PARAM_TUR: POWER_OFF,
    }


@dataclass(frozen=True, kw_only=True)
class EwpeSelectDescription:
    """Maps a select entity to a Gree protocol parameter."""

    param: str
    unique_id_suffix: str
    translation_key: str
    device_to_option: dict[int, str]


_SUB_ZONE_SWING_PARAMS = frozenset(
    {
        PARAM_SUB_ZONE_SWING_UD,
        PARAM_SUB_ZONE_SWING_RIGHT,
        PARAM_SUB_ZONE_SWING_LEFT,
    }
)


def _select_param_supported(
    description: EwpeSelectDescription, data: Mapping[str, int]
) -> bool:
    """Whether a swing select should be created for this status snapshot."""
    if description.param not in data:
        return False
    if description.param not in _SUB_ZONE_SWING_PARAMS:
        return True
    value = data[description.param]
    if value is None:
        return False
    return int(value) in description.device_to_option


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
    EwpeSelectDescription(
        param=PARAM_SUB_ZONE_SWING_UD,
        unique_id_suffix="sub_zone_swing_ud",
        translation_key="sub_zone_swing_ud",
        device_to_option=SWING_VERTICAL_DEVICE_TO_OPTION,
    ),
    EwpeSelectDescription(
        param=PARAM_SUB_ZONE_SWING_RIGHT,
        unique_id_suffix="sub_zone_swing_right_lr",
        translation_key="sub_zone_swing_right_lr",
        device_to_option=SWING_HORIZONTAL_DEVICE_TO_OPTION,
    ),
    EwpeSelectDescription(
        param=PARAM_SUB_ZONE_SWING_LEFT,
        unique_id_suffix="sub_zone_swing_left_lr",
        translation_key="sub_zone_swing_left_lr",
        device_to_option=SWING_HORIZONTAL_DEVICE_TO_OPTION,
    ),
)


def supported_select_descriptions(
    data: Mapping[str, int],
) -> tuple[EwpeSelectDescription, ...]:
    """Return swing selects supported by this device snapshot."""
    return tuple(
        desc for desc in SELECT_DESCRIPTIONS if _select_param_supported(desc, data)
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register select entities supported by this device."""
    coordinator: EwpeCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    entities: list[SelectEntity] = []
    if PARAM_FAN_SPEED in data:
        entities.append(
            EwpeWindSpeedSelect(
                coordinator, entry, supported_wind_speed_options(data)
            )
        )
    entities.extend(
        EwpeSwingSelectEntity(coordinator, entry, description)
        for description in supported_select_descriptions(data)
    )
    async_add_entities(entities)


class _EwpeSelectBase(CoordinatorEntity[EwpeCoordinator], SelectEntity):
    """Shared device info for EWPE Smart select entities."""

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


class EwpeWindSpeedSelect(_EwpeSelectBase):
    """Wind speed select — fan level, auto, quiet, and turbo are mutually exclusive."""

    _attr_translation_key = "wind_speed"

    def __init__(
        self,
        coordinator: EwpeCoordinator,
        entry: ConfigEntry,
        options: tuple[str, ...],
    ) -> None:
        super().__init__(coordinator, entry)
        device = coordinator.device
        self._attr_options = list(options)
        self._attr_unique_id = f"{device.mac}_wind_speed"

    @property
    def current_option(self) -> str | None:
        option = wind_speed_option_from_status(self.coordinator.data or {})
        if option is None or option not in self._attr_options:
            return None
        return option

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.device.set_state(wind_speed_params_for_option(option))
        await self.coordinator.async_request_refresh()


class EwpeSwingSelectEntity(_EwpeSelectBase):
    """Swing mode select backed by a single Gree protocol parameter."""

    def __init__(
        self,
        coordinator: EwpeCoordinator,
        entry: ConfigEntry,
        description: EwpeSelectDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self._description = description
        device = coordinator.device
        self._option_to_device = {
            label: value for value, label in description.device_to_option.items()
        }
        self._attr_translation_key = description.translation_key
        self._attr_options = list(description.device_to_option.values())
        self._attr_unique_id = f"{device.mac}_{description.unique_id_suffix}"
        if param_disabled_by_default(description.param):
            self._attr_disabled_by_default = True

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
