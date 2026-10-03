"""Switch entities for EWPE Smart auxiliary features."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PARAM_AIR,
    PARAM_BLO,
    PARAM_HEALTH,
    PARAM_LIG,
    PARAM_QUIET,
    PARAM_SLEEP,
    PARAM_SLEEP_MODE,
    PARAM_SVST,
    PARAM_TUR,
    POWER_OFF,
    POWER_ON,
    QUIET_MODE_ON,
)
from .coordinator import EwpeConfigEntry, EwpeCoordinator
from .entity import EwpeEntity
from .params_catalog import SWITCH_DESCRIPTIONS as CATALOG_SWITCH_DESCRIPTIONS
from .params_catalog import param_disabled_by_default


@dataclass(frozen=True, kw_only=True)
class EwpeSwitchDescription:
    """Maps a switch entity to a Gree protocol parameter."""

    param: str
    unique_id_suffix: str
    translation_key: str
    # Params written alongside ``param``, but never read back.
    also_writes: tuple[str, ...] = ()
    on_value: int = POWER_ON


SWITCH_DESCRIPTIONS: tuple[EwpeSwitchDescription, ...] = (
    EwpeSwitchDescription(
        param=PARAM_SLEEP,
        unique_id_suffix="sleep",
        translation_key="sleep",
        also_writes=(PARAM_SLEEP_MODE,),
    ),
    EwpeSwitchDescription(
        param=PARAM_TUR, unique_id_suffix="turbo", translation_key="turbo"
    ),
    EwpeSwitchDescription(
        param=PARAM_QUIET,
        unique_id_suffix="quiet",
        translation_key="quiet",
        on_value=QUIET_MODE_ON,
    ),
    EwpeSwitchDescription(
        param=PARAM_BLO, unique_id_suffix="xfan", translation_key="xfan"
    ),
    EwpeSwitchDescription(
        param=PARAM_HEALTH, unique_id_suffix="health", translation_key="health"
    ),
    EwpeSwitchDescription(
        param=PARAM_LIG,
        unique_id_suffix="display_light",
        translation_key="display_light",
    ),
    EwpeSwitchDescription(
        param=PARAM_SVST,
        unique_id_suffix="energy_save",
        translation_key="energy_save",
    ),
    EwpeSwitchDescription(
        param=PARAM_AIR, unique_id_suffix="fresh_air", translation_key="fresh_air"
    ),
)


# Wire keys without a hand-written description above get a switch from the
# parameter catalog.
CATALOG_SWITCHES: tuple[EwpeSwitchDescription, ...] = tuple(
    EwpeSwitchDescription(
        param=d.param,
        unique_id_suffix=d.unique_id_suffix,
        translation_key=d.translation_key,
    )
    for d in CATALOG_SWITCH_DESCRIPTIONS
)


def supported_switch_descriptions(
    data: Mapping[str, int],
) -> tuple[EwpeSwitchDescription, ...]:
    """Return switch descriptions whose param appeared in a status reply."""
    return tuple(
        desc for desc in SWITCH_DESCRIPTIONS + CATALOG_SWITCHES if desc.param in data
    )


# Quiet and turbo moved to the climate fan modes. The switches stay for one
# release and are then removed.
DEPRECATED_SWITCH_PARAMS = frozenset({PARAM_QUIET, PARAM_TUR})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EwpeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register switch entities supported by this device."""
    coordinator = entry.runtime_data
    descriptions = supported_switch_descriptions(coordinator.data or {})
    async_add_entities(
        EwpeSwitchEntity(coordinator, description) for description in descriptions
    )
    issue_id = f"quiet_turbo_switches_{entry.entry_id}"
    if any(d.param in DEPRECATED_SWITCH_PARAMS for d in descriptions):
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="quiet_turbo_switches",
            translation_placeholders={"name": entry.title},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, issue_id)


class EwpeSwitchEntity(EwpeEntity, SwitchEntity):
    """Binary switch backed by a single Gree protocol parameter."""

    def __init__(
        self,
        coordinator: EwpeCoordinator,
        description: EwpeSwitchDescription,
    ) -> None:
        super().__init__(coordinator, description.unique_id_suffix)
        self._description = description
        self._attr_translation_key = description.translation_key
        if param_disabled_by_default(description.param):
            self._attr_entity_registry_enabled_default = False

    @property
    def is_on(self) -> bool | None:
        value = (self.coordinator.data or {}).get(self._description.param)
        if value is None:
            return None
        return bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send(self._description.on_value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send(POWER_OFF)

    async def _send(self, value: int) -> None:
        params = {self._description.param: value}
        params.update(dict.fromkeys(self._description.also_writes, value))
        await self.coordinator.device.set_state(params)
        await self.coordinator.async_request_refresh()
