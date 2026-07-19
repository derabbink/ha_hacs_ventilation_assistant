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
    co2_min: float = 400.0
    co2_max: float = 2000.0


@dataclass(frozen=True)
class VentilationAdvice:
    """Advice split by decision input plus the priority-resolved result."""

    temperature: Advice | None
    humidity: Advice | None
    carbon_dioxide: Advice | None
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
    indoor_co2: float | None = None,
    outdoor_co2: float | None = None,
) -> Advice | None:
    """Return ventilation advice for the current measurements and contact state."""

    return ventilation_advices(
        settings=settings,
        any_open=any_open,
        indoor_temp=indoor_temp,
        outdoor_temp=outdoor_temp,
        indoor_rh=indoor_rh,
        projected_rh=projected_rh,
        indoor_co2=indoor_co2,
        outdoor_co2=outdoor_co2,
    ).overall


def ventilation_advices(
    *,
    settings: ComfortSettings,
    any_open: bool | None,
    indoor_temp: float | None,
    outdoor_temp: float | None,
    indoor_rh: float | None,
    projected_rh: float | None,
    indoor_co2: float | None = None,
    outdoor_co2: float | None = None,
) -> VentilationAdvice:
    """Return component and priority-resolved overall ventilation advice."""

    temperature_advice = _temperature_advice(
        settings, indoor_temp, outdoor_temp, indoor_rh, projected_rh
    )
    humidity_advice = _humidity_advice(
        settings, indoor_temp, outdoor_temp, indoor_rh, projected_rh
    )
    carbon_dioxide_advice = _carbon_dioxide_advice(settings, indoor_co2, outdoor_co2)

    if any_open is not None:
        temperature_advice = _apply_contact_state(temperature_advice, any_open)
        humidity_advice = _apply_contact_state(humidity_advice, any_open)
        carbon_dioxide_advice = _apply_contact_state(carbon_dioxide_advice, any_open)

    return VentilationAdvice(
        temperature=temperature_advice,
        humidity=humidity_advice,
        carbon_dioxide=carbon_dioxide_advice,
        overall=_prioritized_advice(
            settings,
            temperature_advice,
            humidity_advice,
            carbon_dioxide_advice,
        ),
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
    carbon_dioxide_advice: Advice | None,
) -> Advice | None:
    ordered = {
        Priority.TEMPERATURE: (
            temperature_advice,
            humidity_advice,
            carbon_dioxide_advice,
        ),
        Priority.HUMIDITY: (
            humidity_advice,
            temperature_advice,
            carbon_dioxide_advice,
        ),
        Priority.CO2: (
            carbon_dioxide_advice,
            temperature_advice,
            humidity_advice,
        ),
    }[settings.priority]
    return next((advice for advice in ordered if advice is not None), None)


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


def _carbon_dioxide_advice(
    settings: ComfortSettings,
    indoor_co2: float | None,
    outdoor_co2: float | None,
) -> Advice | None:
    if indoor_co2 is None or outdoor_co2 is None:
        return None
    if indoor_co2 > settings.co2_max and outdoor_co2 < indoor_co2:
        return Advice.OPEN
    if indoor_co2 < settings.co2_min and outdoor_co2 > indoor_co2:
        return Advice.OPEN
    return Advice.CLOSE
