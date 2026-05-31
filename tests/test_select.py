"""Tests for select entity state mapping and command emission."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ewpe_smart.const import PARAM_SWING_HORIZONTAL, PARAM_SWING_VERTICAL
from custom_components.ewpe_smart.select import (
    EwpeSelectEntity,
    supported_select_descriptions,
)


def _make_select(
    status: dict[str, int], param: str = PARAM_SWING_HORIZONTAL
) -> tuple[EwpeSelectEntity, MagicMock]:
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

    entity = EwpeSelectEntity(coordinator, entry, description)
    return entity, device


def test_supported_select_descriptions_filters_by_status_keys() -> None:
    data = {"Pow": 1, "SwingLfRig": 1, "SwUpDn": 6}
    descriptions = supported_select_descriptions(data)
    params = {d.param for d in descriptions}
    assert params == {"SwingLfRig", "SwUpDn"}


def test_current_option_maps_device_value() -> None:
    entity, _ = _make_select({"SwingLfRig": 1})
    assert entity.current_option == "full_swing"

    entity_vertical, _ = _make_select({"SwUpDn": 6}, param=PARAM_SWING_VERTICAL)
    assert entity_vertical.current_option == "fixed_lower"


@pytest.mark.asyncio
async def test_select_option_sends_device_value() -> None:
    entity, device = _make_select({"SwingLfRig": 0})
    await entity.async_select_option("full_swing")
    device.set_state.assert_awaited_once_with({"SwingLfRig": 1})
