"""Pure calculation helpers for Ventilation Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from statistics import fmean

from .const import Advice, Priority


@dataclass(frozen=True)
class ComfortSettings:
    """Comfort band and decision priority."""

    temp_min: float
    temp_max: float
    rh_min: float
    rh_max: float
    priority: Priority


def average(values: list[float]) -> float | None:
    """Return the arithmetic mean, or None when no usable values exist."""

    return round(fmean(values), 2) if values else None


def absolute_humidity(temp_c: float | None, relative_humidity: float | None) -> float | None:
    """Calculate absolute humidity in g/m3 from temperature in C and RH in percent."""

    if temp_c is None or relative_humidity is None:
        return None
    saturation_hpa = 6.112 * exp((17.67 * temp_c) / (temp_c + 243.5))
    return round((saturation_hpa * relative_humidity * 2.1674) / (273.15 + temp_c), 2)


def relative_humidity(temp_c: float | None, absolute_humidity_g_m3: float | None) -> float | None:
    """Calculate RH in percent from temperature in C and absolute humidity in g/m3."""

    if temp_c is None or absolute_humidity_g_m3 is None:
        return None
    saturation_hpa = 6.112 * exp((17.67 * temp_c) / (temp_c + 243.5))
    rh = (absolute_humidity_g_m3 * (273.15 + temp_c)) / (2.1674 * saturation_hpa)
    return round(max(0.0, min(100.0, rh)), 2)


def difference(left: float | None, right: float | None) -> float | None:
    """Return left - right, preserving unavailable inputs."""

    if left is None or right is None:
        return None
    return round(left - right, 2)


def open_ratio(open_count: int | None, total_count: int | None) -> float | None:
    """Return the percentage of open contacts."""

    if not total_count:
        return None
    if open_count is None:
        return None
    return round((open_count / total_count) * 100, 1)


def ventilation_advice(
    *,
    settings: ComfortSettings,
    any_open: bool | None,
    indoor_temp: float | None,
    outdoor_temp: float | None,
    indoor_rh: float | None,
    projected_rh: float | None,
) -> Advice | None:
    """Return ventilation advice for the current measurements and contact state."""

    if any_open is None:
        return None

    should_open = _should_open(settings, indoor_temp, outdoor_temp, indoor_rh, projected_rh)
    if should_open is None:
        should_open = any_open

    if should_open and any_open:
        return Advice.KEEP_OPEN
    if should_open and not any_open:
        return Advice.OPEN
    if not should_open and any_open:
        return Advice.CLOSE
    return Advice.KEEP_CLOSED


def _should_open(
    settings: ComfortSettings,
    indoor_temp: float | None,
    outdoor_temp: float | None,
    indoor_rh: float | None,
    projected_rh: float | None,
) -> bool | None:
    checks = (
        (_temperature_should_open, _humidity_should_open)
        if settings.priority == Priority.TEMPERATURE
        else (_humidity_should_open, _temperature_should_open)
    )

    for check in checks:
        result = check(settings, indoor_temp, outdoor_temp, indoor_rh, projected_rh)
        if result is not None:
            return result
    return None


def _temperature_should_open(
    settings: ComfortSettings,
    indoor_temp: float | None,
    outdoor_temp: float | None,
    indoor_rh: float | None,
    projected_rh: float | None,
) -> bool | None:
    del indoor_rh, projected_rh
    if indoor_temp is None or outdoor_temp is None:
        return None
    if indoor_temp > settings.temp_max:
        return outdoor_temp < indoor_temp
    if indoor_temp < settings.temp_min:
        return outdoor_temp > indoor_temp
    return None


def _humidity_should_open(
    settings: ComfortSettings,
    indoor_temp: float | None,
    outdoor_temp: float | None,
    indoor_rh: float | None,
    projected_rh: float | None,
) -> bool | None:
    del indoor_temp, outdoor_temp
    if indoor_rh is None or projected_rh is None:
        return None
    if indoor_rh > settings.rh_max:
        return projected_rh < indoor_rh
    if indoor_rh < settings.rh_min:
        return projected_rh > indoor_rh
    return None
