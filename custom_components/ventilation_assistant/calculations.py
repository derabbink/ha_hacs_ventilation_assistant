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


@dataclass(frozen=True)
class VentilationAdvice:
    """Advice split by decision input plus the priority-resolved result."""

    temperature: Advice | None
    humidity: Advice | None
    overall: Advice | None


def average(values: list[float]) -> float | None:
    """Return the arithmetic mean, or None when no usable values exist."""

    return round(fmean(values), 2) if values else None


def absolute_humidity(
    temp_c: float | None, relative_humidity: float | None
) -> float | None:
    """Calculate absolute humidity in g/m3 from temperature in C and RH in percent."""

    if temp_c is None or relative_humidity is None:
        return None
    saturation_hpa = 6.112 * exp((17.67 * temp_c) / (temp_c + 243.5))
    return round((saturation_hpa * relative_humidity * 2.1674) / (273.15 + temp_c), 2)


def relative_humidity(
    temp_c: float | None, absolute_humidity_g_m3: float | None
) -> float | None:
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

    return ventilation_advices(
        settings=settings,
        any_open=any_open,
        indoor_temp=indoor_temp,
        outdoor_temp=outdoor_temp,
        indoor_rh=indoor_rh,
        projected_rh=projected_rh,
    ).overall


def ventilation_advices(
    *,
    settings: ComfortSettings,
    any_open: bool | None,
    indoor_temp: float | None,
    outdoor_temp: float | None,
    indoor_rh: float | None,
    projected_rh: float | None,
) -> VentilationAdvice:
    """Return temperature, humidity, and overall ventilation advice."""

    temperature_advice = _temperature_advice(
        settings, indoor_temp, outdoor_temp, indoor_rh, projected_rh
    )
    humidity_advice = _humidity_advice(
        settings, indoor_temp, outdoor_temp, indoor_rh, projected_rh
    )

    if any_open is not None:
        temperature_advice = _apply_contact_state(temperature_advice, any_open)
        humidity_advice = _apply_contact_state(humidity_advice, any_open)

    if settings.priority == Priority.HUMIDITY_TEMPERATURE:
        raw = _humidity_temperature_advice(
            settings, indoor_temp, outdoor_temp, indoor_rh, projected_rh
        )
        overall = _apply_contact_state(raw, any_open) if any_open is not None else raw
    elif settings.priority == Priority.TEMPERATURE_HUMIDITY:
        raw = _temperature_humidity_advice(
            settings, indoor_temp, outdoor_temp, indoor_rh, projected_rh
        )
        overall = _apply_contact_state(raw, any_open) if any_open is not None else raw
    else:
        overall = _prioritized_advice(settings, temperature_advice, humidity_advice)

    return VentilationAdvice(
        temperature=temperature_advice,
        humidity=humidity_advice,
        overall=overall,
    )


def _apply_contact_state(advice: Advice | None, any_open: bool) -> Advice | None:
    """Translate action advice to keep-state advice when contact state is known."""

    if any_open and advice == Advice.OPEN:
        return Advice.KEEP_OPEN
    if not any_open and advice == Advice.CLOSE:
        return Advice.KEEP_CLOSED
    return advice


def _prioritized_advice(
    settings: ComfortSettings,
    temperature_advice: Advice | None,
    humidity_advice: Advice | None,
) -> Advice | None:
    primary, fallback = (
        (temperature_advice, humidity_advice)
        if settings.priority == Priority.TEMPERATURE
        else (humidity_advice, temperature_advice)
    )

    return primary if primary is not None else fallback


def _humidity_temperature_advice(
    settings: ComfortSettings,
    indoor_temp: float | None,
    outdoor_temp: float | None,
    indoor_rh: float | None,
    projected_rh: float | None,
) -> Advice | None:
    """Humidity-gated advice: humidity must be in range before temperature is checked.

    OPEN when humidity is above max and opening reduces it, or when humidity is
    within bounds but temperature is outside bounds and opening helps.
    CLOSE when humidity is below min (guard against further drying), when
    opening would worsen high humidity, or when both values are in range.
    Falls back to temperature advice when no humidity data is available.
    """
    if indoor_rh is None or projected_rh is None:
        return _temperature_advice(settings, indoor_temp, outdoor_temp, None, None)
    if indoor_rh < settings.rh_min:
        return Advice.CLOSE
    if indoor_rh > settings.rh_max:
        return Advice.OPEN if projected_rh < indoor_rh else Advice.CLOSE
    # Humidity is within bounds: check temperature
    temp_adv = _temperature_advice(settings, indoor_temp, outdoor_temp, None, None)
    return temp_adv if temp_adv == Advice.OPEN else Advice.CLOSE


def _temperature_humidity_advice(
    settings: ComfortSettings,
    indoor_temp: float | None,
    outdoor_temp: float | None,
    indoor_rh: float | None,
    projected_rh: float | None,
) -> Advice | None:
    """Temperature-gated advice: temperature must be in range before humidity is checked.

    OPEN when temperature is above max and opening cools it, or when temperature
    is within bounds but humidity is outside bounds and opening helps.
    CLOSE when temperature is below min (guard against further cooling), when
    opening would worsen high temperature, or when both values are in range.
    Falls back to humidity advice when no temperature data is available.
    """
    if indoor_temp is None or outdoor_temp is None:
        return _humidity_advice(settings, None, None, indoor_rh, projected_rh)
    if indoor_temp < settings.temp_min:
        return Advice.CLOSE
    if indoor_temp > settings.temp_max:
        return Advice.OPEN if outdoor_temp < indoor_temp else Advice.CLOSE
    # Temperature is within bounds: check humidity
    hum_adv = _humidity_advice(settings, None, None, indoor_rh, projected_rh)
    return hum_adv if hum_adv == Advice.OPEN else Advice.CLOSE


def _temperature_advice(
    settings: ComfortSettings,
    indoor_temp: float | None,
    outdoor_temp: float | None,
    indoor_rh: float | None,
    projected_rh: float | None,
) -> Advice | None:
    del indoor_rh, projected_rh
    if indoor_temp is None or outdoor_temp is None:
        return None
    if indoor_temp > settings.temp_max and outdoor_temp < indoor_temp:
        return Advice.OPEN
    if indoor_temp < settings.temp_min and outdoor_temp > indoor_temp:
        return Advice.OPEN
    return Advice.CLOSE


def _humidity_advice(
    settings: ComfortSettings,
    indoor_temp: float | None,
    outdoor_temp: float | None,
    indoor_rh: float | None,
    projected_rh: float | None,
) -> Advice | None:
    del indoor_temp, outdoor_temp
    if indoor_rh is None or projected_rh is None:
        return None
    if indoor_rh > settings.rh_max and projected_rh < indoor_rh:
        return Advice.OPEN
    if indoor_rh < settings.rh_min and projected_rh > indoor_rh:
        return Advice.OPEN
    return Advice.CLOSE
