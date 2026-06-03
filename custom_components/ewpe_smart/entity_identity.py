"""Stable device identity for entity unique_id and registry."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import CONF_MAC
from .device import EwpeDevice

_INVALID_MAC = frozenset({"", "0", "00:00:00:00:00:00", "000000000000"})


def is_valid_status_mac(value: Any) -> bool:
    """True when a status-reported ``mac`` col is usable (not a placeholder)."""
    if value is None:
        return False
    return str(value).strip().casefold() not in _INVALID_MAC


def config_device_mac(entry: ConfigEntry, device: EwpeDevice) -> str:
    """MAC from config entry, falling back to bind scan then entry id."""
    raw = entry.data.get(CONF_MAC) or device.mac
    if raw is None:
        return entry.entry_id
    mac = str(raw).strip()
    if mac.casefold() in _INVALID_MAC:
        return entry.entry_id
    return mac


def config_device_identifier(entry: ConfigEntry, device: EwpeDevice) -> str:
    """Device registry identifier — same rules as :func:`config_device_mac`."""
    return config_device_mac(entry, device)
