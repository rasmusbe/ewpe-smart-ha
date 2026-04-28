"""Constants for the EWPE Smart integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "ewpe_smart"
MANUFACTURER = "Gree (EWPE Smart)"

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR]

# Network
DEFAULT_PORT = 7000
DEFAULT_TIMEOUT = 5.0
DEFAULT_BROADCAST = "255.255.255.255"
DEFAULT_SCAN_TIMEOUT = 3.0

# Encryption
GENERIC_KEY = b"a3K8Bx%2r8Y7#xDh"

# Polling
DEFAULT_UPDATE_INTERVAL = 30
MIN_UPDATE_INTERVAL = 10
MAX_UPDATE_INTERVAL = 300

# Indoor temperature sensor offset
TEMP_SENSOR_OFFSET = -40

# Config entry keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_MAC = "mac"
CONF_KEY = "key"
CONF_NAME = "name"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_BROADCAST = "broadcast"

# ── Device parameter keys ──────────────────────────────────────────────────
PARAM_POWER = "Pow"
PARAM_MODE = "Mod"
PARAM_SET_TEMP = "SetTem"
PARAM_TEMP_UNIT = "TemUn"
PARAM_FAN_SPEED = "WdSpd"
PARAM_TEMP_SENSOR = "TemSen"

PHASE1_PARAMS: list[str] = [
    PARAM_POWER,
    PARAM_MODE,
    PARAM_SET_TEMP,
    PARAM_TEMP_UNIT,
    PARAM_FAN_SPEED,
    PARAM_TEMP_SENSOR,
]

# ── Value mappings ─────────────────────────────────────────────────────────
POWER_OFF = 0
POWER_ON = 1

MODE_AUTO = 0
MODE_COOL = 1
MODE_DRY = 2
MODE_FAN = 3
MODE_HEAT = 4

FAN_SPEED_AUTO = 0
FAN_SPEED_LOW = 1
FAN_SPEED_MEDIUM = 3
FAN_SPEED_HIGH = 5

# Temperature limits
MIN_TEMP = 16
MAX_TEMP = 30
