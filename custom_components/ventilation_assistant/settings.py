"""Global settings loaded from Home Assistant config files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.util.yaml.loader import load_yaml

from .const import (
    CONF_COMFORT_RH_MAX,
    CONF_COMFORT_RH_MIN,
    CONF_COMFORT_TEMP_MAX,
    CONF_COMFORT_TEMP_MIN,
    CONF_DEVICES,
    CONF_PRIORITY,
    DEFAULT_COMFORT_RH_MAX,
    DEFAULT_COMFORT_RH_MIN,
    DEFAULT_COMFORT_TEMP_MAX,
    DEFAULT_COMFORT_TEMP_MIN,
    Priority,
)


def default_global_options() -> dict[str, Any]:
    """Return built-in global defaults."""

    return {
        CONF_COMFORT_TEMP_MIN: DEFAULT_COMFORT_TEMP_MIN,
        CONF_COMFORT_TEMP_MAX: DEFAULT_COMFORT_TEMP_MAX,
        CONF_COMFORT_RH_MIN: DEFAULT_COMFORT_RH_MIN,
        CONF_COMFORT_RH_MAX: DEFAULT_COMFORT_RH_MAX,
        CONF_PRIORITY: Priority.TEMPERATURE.value,
    }


def load_global_options(path: str) -> dict[str, Any]:
    """Load global defaults from a YAML file."""

    return load_yaml_config(path)["global_options"]


def load_yaml_config(path: str) -> dict[str, Any]:
    """Load all Ventilation Assistant YAML configuration."""

    options = default_global_options()
    devices: list[dict[str, Any]] = []
    config_path = Path(path)
    if not config_path.exists():
        return {"global_options": options, "devices": devices}

    raw = load_yaml(str(config_path))
    if raw is None:
        return {"global_options": options, "devices": devices}
    if not isinstance(raw, dict):
        raise ValueError(f"{config_path.name} must contain a YAML mapping")

    for key in (
        CONF_COMFORT_TEMP_MIN,
        CONF_COMFORT_TEMP_MAX,
        CONF_COMFORT_RH_MIN,
        CONF_COMFORT_RH_MAX,
    ):
        if key in raw:
            options[key] = float(raw[key])

    if CONF_PRIORITY in raw:
        options[CONF_PRIORITY] = Priority(raw[CONF_PRIORITY]).value

    if CONF_DEVICES in raw:
        raw_devices = raw[CONF_DEVICES]
        if not isinstance(raw_devices, list):
            raise ValueError(f"{CONF_DEVICES} must be a YAML list")
        devices = [_normalize_device(device) for device in raw_devices]

    return {"global_options": options, "devices": devices}


def _normalize_device(device: Any) -> dict[str, Any]:
    """Normalize one YAML device entry."""

    if not isinstance(device, dict):
        raise ValueError("Each ventilation device must be a YAML mapping")
    return dict(device)
