"""Temperature unit helpers for user-facing configuration values."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import UnitOfTemperature

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def preferred_temperature_unit(hass: HomeAssistant) -> str:
    """Return the configured Home Assistant temperature unit."""

    return getattr(hass.config.units, "temperature_unit", UnitOfTemperature.CELSIUS)


def celsius_to_unit(value: float, unit: str) -> float:
    """Convert a Celsius value to the requested temperature unit."""

    if unit == UnitOfTemperature.FAHRENHEIT:
        return round((value * 9 / 5) + 32, 2)
    return value


def unit_to_celsius(value: float, unit: str | None) -> float:
    """Convert a temperature value to Celsius."""

    if unit == UnitOfTemperature.FAHRENHEIT:
        return round((value - 32) * 5 / 9, 2)
    return value
