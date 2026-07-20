"""Constants for Ventilation Assistant."""

from __future__ import annotations

from enum import StrEnum

DOMAIN = "ventilation_assistant"

PLATFORMS = ["sensor", "binary_sensor", "number", "select"]

DATA_GLOBAL_OPTIONS = "global_options"

CONF_KIND = "kind"
CONF_GLOBAL = "global"
CONF_DEVICE = "device"

GLOBAL_OUTDOOR_DEVICE_ID = "ventilation_assistant_global"
GLOBAL_OUTDOOR_TEMP_ENTITY_ID = (
    "sensor.ventilation_assistant_global_outdoor_temperature"
)
GLOBAL_OUTDOOR_HUMIDITY_ENTITY_ID = (
    "sensor.ventilation_assistant_global_outdoor_humidity"
)
GLOBAL_OUTDOOR_ABSOLUTE_HUMIDITY_ENTITY_ID = (
    "sensor.ventilation_assistant_global_absolute_outdoor_humidity"
)
GLOBAL_OUTDOOR_CO2_ENTITY_ID = (
    "sensor.ventilation_assistant_global_outdoor_carbon_dioxide"
)

CONF_INDOOR_TEMP_ENTITIES = "indoor_temp_entities"
CONF_INDOOR_HUMIDITY_ENTITIES = "indoor_humidity_entities"
CONF_INDOOR_CO2_ENTITIES = "indoor_co2_entities"
CONF_OUTDOOR_TEMP_ENTITIES = "outdoor_temp_entities"
CONF_OUTDOOR_HUMIDITY_ENTITIES = "outdoor_humidity_entities"
CONF_OUTDOOR_CO2_ENTITIES = "outdoor_co2_entities"
CONF_DOOR_WINDOW_ENTITIES = "door_window_entities"

CONF_COMFORT_TEMP_MIN = "comfort_temp_min"
CONF_COMFORT_TEMP_MAX = "comfort_temp_max"
CONF_COMFORT_RH_MIN = "comfort_rh_min"
CONF_COMFORT_RH_MAX = "comfort_rh_max"
CONF_COMFORT_CO2_MIN = "comfort_co2_min"
CONF_COMFORT_CO2_MAX = "comfort_co2_max"
CONF_PRIORITY = "priority"

DEFAULT_COMFORT_TEMP_MIN = 19.0
DEFAULT_COMFORT_TEMP_MAX = 24.0
DEFAULT_COMFORT_RH_MIN = 40.0
DEFAULT_COMFORT_RH_MAX = 60.0
DEFAULT_COMFORT_CO2_MIN = 400.0
DEFAULT_COMFORT_CO2_MAX = 2000.0
DEFAULT_OUTDOOR_CO2 = 400


class Priority(StrEnum):
    """Ventilation advice priority."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    CO2 = "carbon_dioxide"


class Advice(StrEnum):
    """Ventilation advice."""

    KEEP_CLOSED = "keep_closed"
    OPEN = "open"
    KEEP_OPEN = "keep_open"
    CLOSE = "close"
