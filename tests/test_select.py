"""Tests for select entity state mapping and command emission."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ewpe_smart.const import (
    PARAM_FAN_SPEED,
    PARAM_QUIET,
    PARAM_SWING_HORIZONTAL,
    PARAM_SWING_VERTICAL,
    PARAM_TUR,
    SWING_HORIZONTAL_DEVICE_TO_OPTION,
    SWING_VERTICAL_DEVICE_TO_OPTION,
)
from custom_components.ewpe_smart.select import (
    EwpeSwingSelectEntity,
    EwpeWindSpeedSelect,
    supported_select_descriptions,
    supported_wind_speed_options,
    wind_speed_params_for_option,
)
from custom_components.ewpe_smart.switch import supported_switch_descriptions


def _make_swing_select(
    status: dict[str, int], param: str = PARAM_SWING_HORIZONTAL
) -> tuple[EwpeSwingSelectEntity, MagicMock]:
    descriptions = supported_select_descriptions(status)
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

    entity = EwpeSwingSelectEntity(coordinator, entry, description)
    return entity, device


def _make_wind_select(
    status: dict[str, int],
) -> tuple[EwpeWindSpeedSelect, MagicMock]:
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

    entity = EwpeWindSpeedSelect(
        coordinator, entry, supported_wind_speed_options(status)
    )
    return entity, device


def test_supported_select_descriptions_filters_by_status_keys() -> None:
    data = {"Pow": 1, "SwingLfRig": 1, "SwUpDn": 6}
    descriptions = supported_select_descriptions(data)
    params = {d.param for d in descriptions}
    assert params == {"SwingLfRig", "SwUpDn"}


def test_swing_current_option_maps_device_value() -> None:
    entity, _ = _make_swing_select({"SwingLfRig": 1})
    assert entity.current_option == "full_swing"
    assert set(SWING_HORIZONTAL_DEVICE_TO_OPTION.values()) == {
        "full_swing",
        "left",
        "left_center",
        "center",
        "right_center",
        "right",
    }

    entity_vertical, _ = _make_swing_select({"SwUpDn": 6}, param=PARAM_SWING_VERTICAL)
    assert entity_vertical.current_option == "fixed_lower"
    assert set(SWING_VERTICAL_DEVICE_TO_OPTION.values()) == {
        "full_swing",
        "fixed_upper",
        "fixed_upper_middle",
        "fixed_middle",
        "fixed_lower_middle",
        "fixed_lower",
    }


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ({"WdSpd": 0, "Quiet": 0, "Tur": 0}, "auto"),
        ({"WdSpd": 2, "Quiet": 0, "Tur": 0}, "medium_low"),
        ({"WdSpd": 0, "Quiet": 2, "Tur": 0}, "quiet"),
        ({"WdSpd": 0, "Quiet": 1, "Tur": 0}, "quiet"),
        ({"WdSpd": 3, "Quiet": 0, "Tur": 1}, "turbo"),
        ({"WdSpd": 5, "Quiet": 0, "Tur": 1}, "turbo"),
    ],
)
def test_wind_speed_current_option(status: dict[str, int], expected: str) -> None:
    entity, _ = _make_wind_select(status)
    assert entity.current_option == expected


def test_quiet_and_turbo_switches_are_not_exposed() -> None:
    status = {"Pow": 1, "Quiet": 0, "Tur": 0, "Lig": 1}
    switch_params = {d.param for d in supported_switch_descriptions(status)}
    assert "Quiet" not in switch_params
    assert "Tur" not in switch_params


@pytest.mark.asyncio
async def test_swing_select_option_sends_device_value() -> None:
    entity, device = _make_swing_select({"SwingLfRig": 0})
    await entity.async_select_option("full_swing")
    device.set_state.assert_awaited_once_with({"SwingLfRig": 1})


@pytest.mark.asyncio
async def test_wind_speed_select_clears_other_modes() -> None:
    entity, device = _make_wind_select({"WdSpd": 0, "Quiet": 1, "Tur": 0})
    await entity.async_select_option("high")
    device.set_state.assert_awaited_once_with(
        {"WdSpd": 5, "Quiet": 0, "Tur": 0}
    )


@pytest.mark.asyncio
async def test_wind_speed_turbo_sets_tur_only() -> None:
    entity, device = _make_wind_select({"WdSpd": 3, "Quiet": 0, "Tur": 0})
    await entity.async_select_option("turbo")
    device.set_state.assert_awaited_once_with(
        wind_speed_params_for_option("turbo")
    )
    assert "WdSpd" not in device.set_state.await_args.args[0]


@pytest.mark.asyncio
async def test_wind_speed_quiet_sets_quiet_only() -> None:
    entity, device = _make_wind_select({"WdSpd": 1, "Quiet": 0, "Tur": 0})
    await entity.async_select_option("quiet")
    device.set_state.assert_awaited_once_with(
        wind_speed_params_for_option("quiet")
    )
    assert device.set_state.await_args.args[0]["Quiet"] == 2
    assert "WdSpd" not in device.set_state.await_args.args[0]
