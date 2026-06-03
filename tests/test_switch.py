"""Tests for switch entity state mapping and command emission."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ewpe_smart.const import (
    CONF_MAC,
    PARAM_BEEPER,
    PARAM_BEEPER_NEW,
    PARAM_LIG,
    PARAM_QUIET,
)
from custom_components.ewpe_smart.switch import (
    EwpeSwitchEntity,
    supported_switch_descriptions,
)


def _make_switch(
    status: dict[str, int], param: str = PARAM_LIG
) -> tuple[EwpeSwitchEntity, MagicMock]:
    descriptions = supported_switch_descriptions(status)
    description = next(d for d in descriptions if d.param == param)

    coordinator = MagicMock()
    coordinator.data = status
    coordinator.last_update_success = True
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)

    device = MagicMock()
    device.mac = "AA:BB:CC:DD:EE:FF"
    device.name = "Test"
    device.info = {}
    device.set_state = AsyncMock()
    coordinator.device = device

    entry = MagicMock()
    entry.entry_id = "abc"
    entry.title = "Test"
    entry.data = {CONF_MAC: "580d0df2deaf"}

    entity = EwpeSwitchEntity(coordinator, entry, description)
    return entity, device


def test_supported_switch_descriptions_filters_by_status_keys() -> None:
    data = {"Pow": 1, "Quiet": 0, "Lig": 1}
    descriptions = supported_switch_descriptions(data)
    params = {d.param for d in descriptions}
    assert params == {PARAM_LIG}


def test_sleep_exposes_all_wire_keys_when_present() -> None:
    data = {"SmartSlpMod": 1, "SlpMod": 0, "SwhSlp": 1}
    descriptions = supported_switch_descriptions(data)
    params = {d.param for d in descriptions}
    assert params == {"SmartSlpMod", "SlpMod", "SwhSlp"}


def test_buzzer_exposes_both_wire_keys_when_present() -> None:
    data = {"BuzzerCtrl": 0, "Buzzer_ON_OFF": 1}
    descriptions = supported_switch_descriptions(data)
    params = {d.param for d in descriptions}
    assert params == {PARAM_BEEPER_NEW, PARAM_BEEPER}


def test_buzzer_ctrl_switch_when_alone() -> None:
    data = {"Pow": 1, "BuzzerCtrl": 0}
    descriptions = supported_switch_descriptions(data)
    params = {d.param for d in descriptions}
    assert params == {PARAM_BEEPER_NEW}


def test_buzzer_on_off_when_ctrl_absent() -> None:
    data = {"Pow": 1, "Buzzer_ON_OFF": 1}
    descriptions = supported_switch_descriptions(data)
    params = {d.param for d in descriptions}
    assert params == {PARAM_BEEPER}


def test_quiet_is_not_exposed_as_switch() -> None:
    data = {"Pow": 1, "Quiet": 1, "Tur": 0}
    descriptions = supported_switch_descriptions(data)
    params = {d.param for d in descriptions}
    assert PARAM_QUIET not in params


def test_switch_unique_id_uses_config_mac() -> None:
    entity, _ = _make_switch({"Lig": 1})
    assert entity.unique_id == "580d0df2deaf_display_light"


def test_switch_uses_translation_key_not_wire_param_name() -> None:
    entity, _ = _make_switch({"Lig": 1})
    assert entity._attr_translation_key == "display_light"
    assert getattr(entity, "_attr_name", None) is None


def test_is_on_reflects_param_value() -> None:
    entity, _ = _make_switch({"Lig": 1})
    assert entity.is_on is True

    entity_off, _ = _make_switch({"Lig": 0})
    assert entity_off.is_on is False


@pytest.mark.asyncio
async def test_turn_on_sends_param_one() -> None:
    entity, device = _make_switch({"Lig": 0})
    await entity.async_turn_on()
    device.set_state.assert_awaited_once_with({PARAM_LIG: 1})


@pytest.mark.asyncio
async def test_turn_off_sends_param_zero() -> None:
    entity, device = _make_switch({"Lig": 1}, param=PARAM_LIG)
    await entity.async_turn_off()
    device.set_state.assert_awaited_once_with({PARAM_LIG: 0})
