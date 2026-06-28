"""Constants for Ventilation Assistant."""

from __future__ import annotations

from enum import Enum

DOMAIN = "ventilation_assistant"

PLATFORMS = ["sensor", "binary_sensor", "number", "select"]

DATA_GLOBAL_OPTIONS = "global_options"

CONF_KIND = "kind"
CONF_GLOBAL = "global"
CONF_DEVICE = "device"

CONF_INDOOR_TEMP_ENTITIES = "indoor_temp_entities"
CONF_INDOOR_HUMIDITY_ENTITIES = "indoor_humidity_entities"
CONF_OUTDOOR_TEMP_ENTITIES = "outdoor_temp_entities"
CONF_OUTDOOR_HUMIDITY_ENTITIES = "outdoor_humidity_entities"
CONF_DOOR_WINDOW_ENTITIES = "door_window_entities"

CONF_COMFORT_TEMP_MIN = "comfort_temp_min"
CONF_COMFORT_TEMP_MAX = "comfort_temp_max"
CONF_COMFORT_RH_MIN = "comfort_rh_min"
CONF_COMFORT_RH_MAX = "comfort_rh_max"
CONF_PRIORITY = "priority"

DEFAULT_COMFORT_TEMP_MIN = 19.0
DEFAULT_COMFORT_TEMP_MAX = 24.0
DEFAULT_COMFORT_RH_MIN = 40.0
DEFAULT_COMFORT_RH_MAX = 60.0


class Priority(str, Enum):
    """Ventilation advice priority."""

    TEMPERATURE = "TEMPERATURE"
    HUMIDITY = "HUMIDITY"


class Advice(str, Enum):
    """Ventilation advice."""

    KEEP_CLOSED = "KEEP_CLOSED"
    OPEN = "OPEN"
    KEEP_OPEN = "KEEP_OPEN"
    CLOSE = "CLOSE"
