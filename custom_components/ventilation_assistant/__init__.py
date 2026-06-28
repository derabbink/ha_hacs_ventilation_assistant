"""Ventilation Assistant integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import discovery
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import StateType

from .calculations import (
    ComfortSettings,
    absolute_humidity,
    average,
    difference,
    open_ratio,
    relative_humidity,
    ventilation_advice,
)
from .const import (
    CONF_COMFORT_RH_MAX,
    CONF_COMFORT_RH_MIN,
    CONF_COMFORT_TEMP_MAX,
    CONF_COMFORT_TEMP_MIN,
    CONF_DEVICE,
    CONF_DEVICES,
    CONF_DOOR_WINDOW_ENTITIES,
    CONF_ID,
    CONF_INDOOR_HUMIDITY_ENTITIES,
    CONF_INDOOR_TEMP_ENTITIES,
    CONF_KIND,
    CONF_OUTDOOR_HUMIDITY_ENTITIES,
    CONF_OUTDOOR_TEMP_ENTITIES,
    CONF_PRIORITY,
    DATA_COORDINATORS,
    DATA_GLOBAL_OPTIONS,
    DEFAULT_COMFORT_RH_MAX,
    DEFAULT_COMFORT_RH_MIN,
    DEFAULT_COMFORT_TEMP_MAX,
    DEFAULT_COMFORT_TEMP_MIN,
    DOMAIN,
    GLOBAL_CONFIG_FILE,
    PLATFORMS,
    Priority,
)
from .settings import default_global_options, load_yaml_config

VentilationConfigEntry = ConfigEntry

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Any(None, vol.Schema({}))}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up global state for Ventilation Assistant."""

    hass.data.setdefault(DOMAIN, {})
    await _async_load_yaml_config(hass)
    if hass.data[DOMAIN][DATA_COORDINATORS]:
        for platform in PLATFORMS:
            await discovery.async_load_platform(hass, platform, DOMAIN, {}, config)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: VentilationConfigEntry
) -> bool:
    """Set up Ventilation Assistant from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    if DATA_GLOBAL_OPTIONS not in hass.data[DOMAIN]:
        await _async_load_yaml_config(hass)

    if entry.data.get(CONF_KIND) != CONF_DEVICE:
        return True

    coordinator = VentilationCoordinator.from_entry(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await coordinator.async_setup()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: VentilationConfigEntry
) -> bool:
    """Unload a config entry."""

    if entry.data.get(CONF_KIND) != CONF_DEVICE:
        return True

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: VentilationCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator.async_unload()
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: VentilationConfigEntry
) -> None:
    """Reload entries when options change."""

    await hass.config_entries.async_reload(entry.entry_id)


async def _async_load_yaml_config(hass: HomeAssistant) -> None:
    """Load hidden YAML config and build coordinators."""

    path = hass.config.path(GLOBAL_CONFIG_FILE)
    yaml_config = await hass.async_add_executor_job(load_yaml_config, path)
    hass.data[DOMAIN][DATA_GLOBAL_OPTIONS] = yaml_config["global_options"]
    coordinators = [
        VentilationCoordinator.from_yaml(hass, device)
        for device in yaml_config[CONF_DEVICES]
    ]
    hass.data[DOMAIN][DATA_COORDINATORS] = coordinators
    await _async_setup_coordinators(coordinators)


async def _async_setup_coordinators(coordinators: list[VentilationCoordinator]) -> None:
    """Start all YAML-backed coordinators."""

    for coordinator in coordinators:
        await coordinator.async_setup()


def async_unload_yaml(hass: HomeAssistant) -> None:
    """Unload YAML-backed coordinators."""

    for coordinator in hass.data.get(DOMAIN, {}).get(DATA_COORDINATORS, []):
        coordinator.async_unload()


@dataclass(frozen=True)
class VentilationDeviceConfig:
    """Configuration for one virtual ventilation device."""

    id: str
    name: str
    options: dict[str, Any]

    @classmethod
    def from_yaml(cls, device: dict[str, Any]) -> VentilationDeviceConfig:
        """Create a device config from YAML."""

        name = str(device[CONF_NAME])
        device_id = str(device.get(CONF_ID) or _slugify(name))
        options = {
            key: device.get(key, [])
            for key in (
                CONF_INDOOR_TEMP_ENTITIES,
                CONF_INDOOR_HUMIDITY_ENTITIES,
                CONF_OUTDOOR_TEMP_ENTITIES,
                CONF_OUTDOOR_HUMIDITY_ENTITIES,
                CONF_DOOR_WINDOW_ENTITIES,
            )
        }
        for key in (
            CONF_COMFORT_TEMP_MIN,
            CONF_COMFORT_TEMP_MAX,
            CONF_COMFORT_RH_MIN,
            CONF_COMFORT_RH_MAX,
            CONF_PRIORITY,
        ):
            if key in device and device[key] not in (None, ""):
                options[key] = device[key]
        return cls(id=device_id, name=name, options=options)

    @classmethod
    def from_entry(cls, entry: VentilationConfigEntry) -> VentilationDeviceConfig:
        """Create a device config from a legacy config entry."""

        return cls(
            id=entry.entry_id,
            name=entry.data[CONF_NAME],
            options=dict(entry.options),
        )


def _slugify(value: str) -> str:
    """Create a stable-enough id from a YAML device name."""

    slug = "".join(char.lower() if char.isalnum() else "_" for char in value)
    return "_".join(part for part in slug.split("_") if part)


def yaml_coordinators(hass: HomeAssistant) -> list[VentilationCoordinator]:
    """Return YAML-backed coordinators."""

    return list(hass.data.get(DOMAIN, {}).get(DATA_COORDINATORS, []))


@dataclass
class VentilationSnapshot:
    """Computed state for one virtual device."""

    indoor_temp: float | None
    indoor_rh: float | None
    indoor_absolute_humidity: float | None
    indoor_projected_absolute_humidity: float | None
    indoor_projected_rh: float | None
    indoor_projected_rh_difference: float | None
    indoor_outdoor_temp_difference: float | None
    outdoor_temp: float | None
    outdoor_rh: float | None
    outdoor_absolute_humidity: float | None
    any_open: bool | None
    open_percentage: float | None
    advice: str | None


class VentilationCoordinator:
    """Small coordinator for state-derived virtual entities."""

    def __init__(self, hass: HomeAssistant, config: VentilationDeviceConfig) -> None:
        """Initialize the coordinator."""

        self.hass = hass
        self.config = config
        self.device_name = config.name
        self._listeners: list[Callable[[], None]] = []
        self._remove_state_listener: Callable[[], None] | None = None

    @classmethod
    def from_yaml(
        cls, hass: HomeAssistant, device: dict[str, Any]
    ) -> VentilationCoordinator:
        """Create a YAML-backed coordinator."""

        return cls(hass, VentilationDeviceConfig.from_yaml(device))

    @classmethod
    def from_entry(
        cls, hass: HomeAssistant, entry: VentilationConfigEntry
    ) -> VentilationCoordinator:
        """Create a coordinator from a legacy config entry."""

        return cls(hass, VentilationDeviceConfig.from_entry(entry))

    @property
    def device_id(self) -> str:
        """Return a stable identifier for the virtual device."""

        return self.config.id

    async def async_setup(self) -> None:
        """Start tracking referenced input entities."""

        entity_ids = sorted(self.input_entity_ids)
        if entity_ids:
            self._remove_state_listener = async_track_state_change_event(
                self.hass, entity_ids, self._async_input_changed
            )

    def async_unload(self) -> None:
        """Stop tracking input entities."""

        if self._remove_state_listener is not None:
            self._remove_state_listener()
            self._remove_state_listener = None

    @property
    def input_entity_ids(self) -> set[str]:
        """Return all referenced input entity ids."""

        options = self.config.options
        return {
            entity_id
            for key in (
                CONF_INDOOR_TEMP_ENTITIES,
                CONF_INDOOR_HUMIDITY_ENTITIES,
                CONF_OUTDOOR_TEMP_ENTITIES,
                CONF_OUTDOOR_HUMIDITY_ENTITIES,
                CONF_DOOR_WINDOW_ENTITIES,
            )
            for entity_id in options.get(key, [])
        }

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an entity update listener."""

        self._listeners.append(listener)

        @callback
        def remove_listener() -> None:
            self._listeners.remove(listener)

        return remove_listener

    @callback
    def _async_input_changed(self, event: Any) -> None:
        """Notify entities that one of the inputs changed."""

        for listener in self._listeners:
            listener()

    def snapshot(self) -> VentilationSnapshot:
        """Compute the latest virtual device snapshot."""

        indoor_temp = average(self._numeric_states(CONF_INDOOR_TEMP_ENTITIES, "temperature"))
        indoor_rh = average(self._numeric_states(CONF_INDOOR_HUMIDITY_ENTITIES, PERCENTAGE))
        outdoor_temp = average(self._numeric_states(CONF_OUTDOOR_TEMP_ENTITIES, "temperature"))
        outdoor_rh = average(self._numeric_states(CONF_OUTDOOR_HUMIDITY_ENTITIES, PERCENTAGE))

        indoor_ah = absolute_humidity(indoor_temp, indoor_rh)
        outdoor_ah = absolute_humidity(outdoor_temp, outdoor_rh)
        projected_ah = outdoor_ah if indoor_temp is not None and outdoor_ah is not None else None
        projected_rh = relative_humidity(indoor_temp, projected_ah)
        any_open, open_count, total_count = self._open_counts()

        settings = self.comfort_settings
        advice = ventilation_advice(
            settings=settings,
            any_open=any_open,
            indoor_temp=indoor_temp,
            outdoor_temp=outdoor_temp,
            indoor_rh=indoor_rh,
            projected_rh=projected_rh,
        )

        return VentilationSnapshot(
            indoor_temp=indoor_temp,
            indoor_rh=indoor_rh,
            indoor_absolute_humidity=indoor_ah,
            indoor_projected_absolute_humidity=projected_ah,
            indoor_projected_rh=projected_rh,
            indoor_projected_rh_difference=difference(indoor_rh, projected_rh),
            indoor_outdoor_temp_difference=difference(indoor_temp, outdoor_temp),
            outdoor_temp=outdoor_temp,
            outdoor_rh=outdoor_rh,
            outdoor_absolute_humidity=outdoor_ah,
            any_open=any_open,
            open_percentage=open_ratio(open_count, total_count),
            advice=advice.value if advice is not None else None,
        )

    @property
    def comfort_settings(self) -> ComfortSettings:
        """Return device settings with global fallbacks applied."""

        options = self.config.options
        global_options = self._global_options()
        return ComfortSettings(
            temp_min=float(
                options.get(
                    CONF_COMFORT_TEMP_MIN,
                    global_options.get(CONF_COMFORT_TEMP_MIN, DEFAULT_COMFORT_TEMP_MIN),
                )
            ),
            temp_max=float(
                options.get(
                    CONF_COMFORT_TEMP_MAX,
                    global_options.get(CONF_COMFORT_TEMP_MAX, DEFAULT_COMFORT_TEMP_MAX),
                )
            ),
            rh_min=float(
                options.get(
                    CONF_COMFORT_RH_MIN,
                    global_options.get(CONF_COMFORT_RH_MIN, DEFAULT_COMFORT_RH_MIN),
                )
            ),
            rh_max=float(
                options.get(
                    CONF_COMFORT_RH_MAX,
                    global_options.get(CONF_COMFORT_RH_MAX, DEFAULT_COMFORT_RH_MAX),
                )
            ),
            priority=Priority(
                options.get(CONF_PRIORITY, global_options.get(CONF_PRIORITY, Priority.TEMPERATURE))
            ),
        )

    def _global_options(self) -> dict[str, Any]:
        return dict(
            self.hass.data.get(DOMAIN, {}).get(
                DATA_GLOBAL_OPTIONS, default_global_options()
            )
        )

    def _numeric_states(self, key: str, expected_unit: str) -> list[float]:
        values: list[float] = []
        for entity_id in self.config.options.get(key, []):
            state = self.hass.states.get(entity_id)
            if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                continue
            value = _state_float(state.state)
            if value is None:
                continue
            if expected_unit == "temperature":
                value = _temperature_to_celsius(
                    value, state.attributes.get("unit_of_measurement")
                )
            values.append(value)
        return values

    def _open_counts(self) -> tuple[bool | None, int | None, int | None]:
        entity_ids = self.config.options.get(CONF_DOOR_WINDOW_ENTITIES, [])
        if not entity_ids:
            return None, None, None

        open_count = 0
        total_count = 0
        for entity_id in entity_ids:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                continue
            total_count += 1
            if state.state == "on":
                open_count += 1

        if total_count == 0:
            return None, None, None
        return open_count > 0, open_count, total_count


def _state_float(value: StateType) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _temperature_to_celsius(value: float, unit: str | None) -> float:
    if unit == UnitOfTemperature.FAHRENHEIT:
        return round((value - 32) * 5 / 9, 2)
    return value
