"""Ventilation Assistant integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant import config_entries
    from homeassistant.helpers.typing import StateType

from .calculations import (
    ComfortSettings,
    absolute_humidity,
    average,
    difference,
    open_ratio,
    relative_humidity,
    ventilation_advices,
)
from .const import (
    CONF_COMFORT_CO2_MAX,
    CONF_COMFORT_CO2_MIN,
    CONF_COMFORT_RH_MAX,
    CONF_COMFORT_RH_MIN,
    CONF_COMFORT_TEMP_MAX,
    CONF_COMFORT_TEMP_MIN,
    CONF_DEVICE,
    CONF_DOOR_WINDOW_ENTITIES,
    CONF_GLOBAL,
    CONF_INDOOR_CO2_ENTITIES,
    CONF_INDOOR_HUMIDITY_ENTITIES,
    CONF_INDOOR_TEMP_ENTITIES,
    CONF_KIND,
    CONF_OUTDOOR_CO2_ENTITIES,
    CONF_OUTDOOR_HUMIDITY_ENTITIES,
    CONF_OUTDOOR_TEMP_ENTITIES,
    CONF_PRIORITY,
    DATA_GLOBAL_OPTIONS,
    DEFAULT_COMFORT_CO2_MAX,
    DEFAULT_COMFORT_CO2_MIN,
    DEFAULT_COMFORT_RH_MAX,
    DEFAULT_COMFORT_RH_MIN,
    DEFAULT_COMFORT_TEMP_MAX,
    DEFAULT_COMFORT_TEMP_MIN,
    DEFAULT_OUTDOOR_CO2,
    DOMAIN,
    GLOBAL_OUTDOOR_DEVICE_ID,
    PLATFORMS,
    Priority,
)

VentilationConfigEntry = ConfigEntry


async def async_migrate_entry(
    hass: HomeAssistant, entry: VentilationConfigEntry
) -> bool:
    """Migrate config entry to the current version."""

    if entry.version == 1 and entry.minor_version < 2:
        if entry.data[CONF_KIND] == CONF_GLOBAL:
            new_options = dict(entry.options)
            if CONF_PRIORITY in new_options:
                new_options[CONF_PRIORITY] = new_options[CONF_PRIORITY].lower()
            hass.config_entries.async_update_entry(
                entry, minor_version=2, options=new_options
            )
            for subentry in entry.subentries.values():
                new_data = dict(subentry.data)
                if CONF_PRIORITY in new_data:
                    new_data[CONF_PRIORITY] = new_data[CONF_PRIORITY].lower()
                    hass.config_entries.async_update_subentry(
                        entry, subentry, data=new_data
                    )
        else:
            new_options = dict(entry.options)
            if CONF_PRIORITY in new_options:
                new_options[CONF_PRIORITY] = new_options[CONF_PRIORITY].lower()
            hass.config_entries.async_update_entry(
                entry, minor_version=2, options=new_options
            )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: VentilationConfigEntry) -> bool:
    """Set up Ventilation Assistant from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    if entry.data[CONF_KIND] == CONF_GLOBAL:
        global_options = _global_options_from_entry(entry)
        hass.data[DOMAIN][DATA_GLOBAL_OPTIONS] = global_options
        global_coordinator = GlobalOutdoorCoordinator(
            hass,
            VentilationDeviceConfig(
                id=GLOBAL_OUTDOOR_DEVICE_ID,
                name="Outdoor",
                options=global_options,
            ),
        )
        coordinators = [
            global_coordinator,
            *[
                VentilationCoordinator(
                    hass,
                    VentilationDeviceConfig.from_subentry(subentry),
                    global_coordinator=global_coordinator,
                )
                for subentry in entry.get_subentries_of_type(CONF_DEVICE)
            ],
        ]
        hass.data[DOMAIN][entry.entry_id] = coordinators
        for coordinator in coordinators:
            await coordinator.async_setup()
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(_async_update_listener))
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

    if entry.data[CONF_KIND] == CONF_GLOBAL:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok:
            coordinators: list[VentilationCoordinator] = hass.data[DOMAIN].pop(
                entry.entry_id, []
            )
            for coordinator in coordinators:
                coordinator.async_unload()
            hass.data[DOMAIN].pop(DATA_GLOBAL_OPTIONS, None)
        return unload_ok

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
    if entry.data[CONF_KIND] == CONF_GLOBAL:
        for other_entry in hass.config_entries.async_entries(DOMAIN):
            if other_entry.data[CONF_KIND] == CONF_DEVICE:
                await hass.config_entries.async_reload(other_entry.entry_id)


def coordinators_for_entry(
    hass: HomeAssistant, entry: VentilationConfigEntry
) -> list[VentilationCoordinator]:
    """Return all coordinators owned by a config entry."""

    coordinators = hass.data[DOMAIN][entry.entry_id]
    if isinstance(coordinators, list):
        return coordinators
    return [coordinators]


def device_coordinators_for_entry(
    hass: HomeAssistant, entry: VentilationConfigEntry
) -> list[VentilationCoordinator]:
    """Return ventilation-area coordinators owned by a config entry."""

    return [
        coordinator
        for coordinator in coordinators_for_entry(hass, entry)
        if not isinstance(coordinator, GlobalOutdoorCoordinator)
    ]


@callback
def async_update_device_options(
    hass: HomeAssistant,
    entry: VentilationConfigEntry,
    coordinator: VentilationCoordinator,
    options: dict[str, Any],
) -> None:
    """Persist device options for global-owned and legacy device entries."""

    if entry.data[CONF_KIND] == CONF_GLOBAL:
        for subentry in entry.subentries.values():
            if subentry.subentry_id == coordinator.device_id:
                hass.config_entries.async_update_subentry(entry, subentry, data=options)
                break
    else:
        hass.config_entries.async_update_entry(entry, options=options)

    coordinator.async_update_options(options)


@dataclass(frozen=True)
class VentilationDeviceConfig:
    """Configuration for one virtual ventilation device."""

    id: str
    name: str
    options: dict[str, Any]

    @classmethod
    def from_entry(cls, entry: VentilationConfigEntry) -> VentilationDeviceConfig:
        """Create a device config from a legacy config entry."""

        return cls(
            id=entry.entry_id,
            name=entry.data[CONF_NAME],
            options=dict(entry.options),
        )

    @classmethod
    def from_subentry(
        cls, subentry: config_entries.ConfigSubentry
    ) -> VentilationDeviceConfig:
        """Create a device config from a config subentry."""

        return cls(
            id=subentry.subentry_id,
            name=subentry.title,
            options=dict(subentry.data),
        )


@dataclass
class VentilationSnapshot:
    """Computed state for one virtual device."""

    indoor_temp: float | None
    indoor_rh: float | None
    indoor_co2: int | None
    indoor_absolute_humidity: float | None
    indoor_projected_absolute_humidity: float | None
    indoor_projected_rh: float | None
    indoor_projected_rh_difference: float | None
    indoor_outdoor_temp_difference: float | None
    projected_indoor_co2_difference: int | None
    outdoor_temp: float | None
    outdoor_rh: float | None
    outdoor_co2: int | None
    outdoor_absolute_humidity: float | None
    any_open: bool | None
    open_percentage: float | None
    temperature_advice: str | None
    humidity_advice: str | None
    carbon_dioxide_advice: str | None
    advice: str | None


class VentilationCoordinator:
    """Small coordinator for state-derived virtual entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: VentilationDeviceConfig,
        *,
        global_coordinator: GlobalOutdoorCoordinator | None = None,
    ) -> None:
        """Initialize the coordinator."""

        self.hass = hass
        self.config = config
        self.device_name = config.name
        self._global_coordinator = global_coordinator
        self._listeners: list[Callable[[], None]] = []
        self._remove_state_listener: Callable[[], None] | None = None
        self._remove_global_listener: Callable[[], None] | None = None

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

        self._async_track_inputs()

    @callback
    def _async_track_inputs(self) -> None:
        """Track the current set of referenced input entities."""

        if self._remove_state_listener is not None:
            self._remove_state_listener()
            self._remove_state_listener = None

        entity_ids = sorted(self.input_entity_ids)
        if entity_ids:
            self._remove_state_listener = async_track_state_change_event(
                self.hass, entity_ids, self._async_input_changed
            )
        self._async_track_global_fallback()

    @callback
    def _async_track_global_fallback(self) -> None:
        """Track global outdoor coordinator updates when using fallback values."""

        if self._remove_global_listener is not None:
            self._remove_global_listener()
            self._remove_global_listener = None

        global_coordinator = self._global_outdoor_coordinator()
        if global_coordinator is not None and self._uses_global_outdoor():
            self._remove_global_listener = global_coordinator.async_add_listener(
                self._async_notify_listeners
            )

    def async_unload(self) -> None:
        """Stop tracking input entities."""

        if self._remove_state_listener is not None:
            self._remove_state_listener()
            self._remove_state_listener = None
        if self._remove_global_listener is not None:
            self._remove_global_listener()
            self._remove_global_listener = None

    @property
    def input_entity_ids(self) -> set[str]:
        """Return all referenced input entity ids."""

        options = self.config.options
        return {
            entity_id
            for key in (
                CONF_INDOOR_TEMP_ENTITIES,
                CONF_INDOOR_HUMIDITY_ENTITIES,
                CONF_INDOOR_CO2_ENTITIES,
                CONF_DOOR_WINDOW_ENTITIES,
            )
            for entity_id in _entity_ids(options.get(key))
        } | self._outdoor_input_entity_ids()

    def _outdoor_input_entity_ids(self) -> set[str]:
        """Return outdoor inputs, including global fallback entities."""

        options = self.config.options
        outdoor_temp_entities = _entity_ids(options.get(CONF_OUTDOOR_TEMP_ENTITIES))
        outdoor_rh_entities = _entity_ids(options.get(CONF_OUTDOOR_HUMIDITY_ENTITIES))
        outdoor_co2_entities = _entity_ids(options.get(CONF_OUTDOOR_CO2_ENTITIES))
        return (
            set(outdoor_temp_entities)
            | set(outdoor_rh_entities)
            | set(outdoor_co2_entities)
        )

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

        self._async_notify_listeners()

    @callback
    def async_update_options(self, options: dict[str, Any]) -> None:
        """Update in-memory options and notify entities."""

        self.config.options.clear()
        self.config.options.update(options)
        self._async_track_inputs()
        self._async_notify_listeners()

    @callback
    def _async_notify_listeners(self) -> None:
        """Notify entities that derived state changed."""

        for listener in self._listeners:
            listener()

    def snapshot(self) -> VentilationSnapshot:
        """Compute the latest virtual device snapshot."""

        indoor_temp = average(
            self._numeric_states(CONF_INDOOR_TEMP_ENTITIES, "temperature")
        )
        indoor_rh = average(
            self._numeric_states(CONF_INDOOR_HUMIDITY_ENTITIES, PERCENTAGE)
        )
        indoor_co2 = _co2_average(self._numeric_states(CONF_INDOOR_CO2_ENTITIES, "ppm"))
        outdoor_temp = self._outdoor_temp()
        outdoor_rh = self._outdoor_rh()
        outdoor_co2 = self._outdoor_co2()

        indoor_ah = absolute_humidity(indoor_temp, indoor_rh)
        outdoor_ah = self._outdoor_absolute_humidity(outdoor_temp, outdoor_rh)
        projected_ah = (
            outdoor_ah if indoor_temp is not None and outdoor_ah is not None else None
        )
        projected_rh = relative_humidity(indoor_temp, projected_ah)
        any_open, open_count, total_count = self._open_counts()

        settings = self.comfort_settings
        advices = ventilation_advices(
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
            indoor_co2=indoor_co2,
            indoor_absolute_humidity=indoor_ah,
            indoor_projected_absolute_humidity=projected_ah,
            indoor_projected_rh=projected_rh,
            indoor_projected_rh_difference=difference(projected_rh, indoor_rh),
            indoor_outdoor_temp_difference=difference(outdoor_temp, indoor_temp),
            projected_indoor_co2_difference=_integer_difference(
                outdoor_co2, indoor_co2
            ),
            outdoor_temp=outdoor_temp,
            outdoor_rh=outdoor_rh,
            outdoor_co2=outdoor_co2,
            outdoor_absolute_humidity=outdoor_ah,
            any_open=any_open,
            open_percentage=open_ratio(open_count, total_count),
            temperature_advice=(
                advices.temperature.value if advices.temperature is not None else None
            ),
            humidity_advice=(
                advices.humidity.value if advices.humidity is not None else None
            ),
            carbon_dioxide_advice=None,
            advice=advices.overall.value if advices.overall is not None else None,
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
                options.get(
                    CONF_PRIORITY,
                    global_options.get(CONF_PRIORITY, Priority.TEMPERATURE),
                )
            ),
            co2_min=float(
                options.get(
                    CONF_COMFORT_CO2_MIN,
                    global_options.get(CONF_COMFORT_CO2_MIN, DEFAULT_COMFORT_CO2_MIN),
                )
            ),
            co2_max=float(
                options.get(
                    CONF_COMFORT_CO2_MAX,
                    global_options.get(CONF_COMFORT_CO2_MAX, DEFAULT_COMFORT_CO2_MAX),
                )
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
        for entity_id in _entity_ids(self.config.options.get(key)):
            value = self._numeric_state(entity_id, expected_unit)
            if value is None:
                continue
            values.append(value)
        return values

    def _numeric_state(self, entity_id: str, expected_unit: str) -> float | None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        value = _state_float(state.state)
        if value is None:
            return None
        if expected_unit == "temperature":
            value = _temperature_to_celsius(
                value, state.attributes.get("unit_of_measurement")
            )
        return value

    def _outdoor_temp(self) -> float | None:
        if _entity_ids(self.config.options.get(CONF_OUTDOOR_TEMP_ENTITIES)):
            return average(
                self._numeric_states(CONF_OUTDOOR_TEMP_ENTITIES, "temperature")
            )
        global_snapshot = self._global_outdoor_snapshot()
        return global_snapshot.outdoor_temp if global_snapshot is not None else None

    def _outdoor_rh(self) -> float | None:
        if _entity_ids(self.config.options.get(CONF_OUTDOOR_HUMIDITY_ENTITIES)):
            return average(
                self._numeric_states(CONF_OUTDOOR_HUMIDITY_ENTITIES, PERCENTAGE)
            )
        global_snapshot = self._global_outdoor_snapshot()
        return global_snapshot.outdoor_rh if global_snapshot is not None else None

    def _outdoor_co2(self) -> int | None:
        if _entity_ids(self.config.options.get(CONF_OUTDOOR_CO2_ENTITIES)):
            return _co2_average(self._numeric_states(CONF_OUTDOOR_CO2_ENTITIES, "ppm"))
        global_snapshot = self._global_outdoor_snapshot()
        return global_snapshot.outdoor_co2 if global_snapshot is not None else None

    def _outdoor_absolute_humidity(
        self, outdoor_temp: float | None, outdoor_rh: float | None
    ) -> float | None:
        if not _entity_ids(
            self.config.options.get(CONF_OUTDOOR_TEMP_ENTITIES)
        ) and not _entity_ids(self.config.options.get(CONF_OUTDOOR_HUMIDITY_ENTITIES)):
            global_snapshot = self._global_outdoor_snapshot()
            return (
                global_snapshot.outdoor_absolute_humidity
                if global_snapshot is not None
                else None
            )
        return absolute_humidity(outdoor_temp, outdoor_rh)

    def _uses_global_outdoor(self) -> bool:
        return (
            not _entity_ids(self.config.options.get(CONF_OUTDOOR_TEMP_ENTITIES))
            or not _entity_ids(self.config.options.get(CONF_OUTDOOR_HUMIDITY_ENTITIES))
            or not _entity_ids(self.config.options.get(CONF_OUTDOOR_CO2_ENTITIES))
        )

    def _global_outdoor_snapshot(self) -> VentilationSnapshot | None:
        global_coordinator = self._global_outdoor_coordinator()
        return global_coordinator.snapshot() if global_coordinator is not None else None

    def _global_outdoor_coordinator(self) -> GlobalOutdoorCoordinator | None:
        if self._global_coordinator is not None:
            return self._global_coordinator

        domain_data = self.hass.data.get(DOMAIN, {})
        for coordinators in domain_data.values():
            if not isinstance(coordinators, list):
                continue
            for coordinator in coordinators:
                if isinstance(coordinator, GlobalOutdoorCoordinator):
                    return coordinator
        return None

    def _open_counts(self) -> tuple[bool | None, int | None, int | None]:
        entity_ids = _entity_ids(self.config.options.get(CONF_DOOR_WINDOW_ENTITIES))
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


class GlobalOutdoorCoordinator(VentilationCoordinator):
    """Coordinator for global outdoor weather sensors."""

    @property
    def input_entity_ids(self) -> set[str]:
        """Return configured global outdoor source entity ids."""

        options = self.config.options
        return {
            entity_id
            for key in (
                CONF_OUTDOOR_TEMP_ENTITIES,
                CONF_OUTDOOR_HUMIDITY_ENTITIES,
                CONF_OUTDOOR_CO2_ENTITIES,
            )
            for entity_id in _entity_ids(options.get(key))
        }

    def snapshot(self) -> VentilationSnapshot:
        """Compute the latest global outdoor snapshot."""

        outdoor_temp = average(
            self._numeric_states(CONF_OUTDOOR_TEMP_ENTITIES, "temperature")
        )
        outdoor_rh = average(
            self._numeric_states(CONF_OUTDOOR_HUMIDITY_ENTITIES, PERCENTAGE)
        )
        configured_co2 = _entity_ids(self.config.options.get(CONF_OUTDOOR_CO2_ENTITIES))
        outdoor_co2 = (
            _co2_average(self._numeric_states(CONF_OUTDOOR_CO2_ENTITIES, "ppm"))
            if configured_co2
            else DEFAULT_OUTDOOR_CO2
        )

        return VentilationSnapshot(
            indoor_temp=None,
            indoor_rh=None,
            indoor_co2=None,
            indoor_absolute_humidity=None,
            indoor_projected_absolute_humidity=None,
            indoor_projected_rh=None,
            indoor_projected_rh_difference=None,
            indoor_outdoor_temp_difference=None,
            projected_indoor_co2_difference=None,
            outdoor_temp=outdoor_temp,
            outdoor_rh=outdoor_rh,
            outdoor_co2=outdoor_co2,
            outdoor_absolute_humidity=absolute_humidity(outdoor_temp, outdoor_rh),
            any_open=None,
            open_percentage=None,
            temperature_advice=None,
            humidity_advice=None,
            carbon_dioxide_advice=None,
            advice=None,
        )


def _state_float(value: StateType) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _co2_average(values: list[float]) -> int | None:
    """Return a whole-ppm arithmetic mean."""

    result = average(values)
    return round(result) if result is not None else None


def _integer_difference(left: int | None, right: int | None) -> int | None:
    """Return a whole-number difference, preserving unavailable inputs."""

    return left - right if left is not None and right is not None else None


def _temperature_to_celsius(value: float, unit: str | None) -> float:
    if unit == UnitOfTemperature.FAHRENHEIT:
        return round((value - 32) * 5 / 9, 2)
    return value


def _entity_ids(value: Any) -> list[str]:
    """Return selector entity ids as a list."""

    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return list(value)


def default_global_options() -> dict[str, Any]:
    """Return built-in global defaults."""

    return {
        CONF_OUTDOOR_TEMP_ENTITIES: [],
        CONF_OUTDOOR_HUMIDITY_ENTITIES: [],
        CONF_OUTDOOR_CO2_ENTITIES: [],
        CONF_COMFORT_TEMP_MIN: DEFAULT_COMFORT_TEMP_MIN,
        CONF_COMFORT_TEMP_MAX: DEFAULT_COMFORT_TEMP_MAX,
        CONF_COMFORT_RH_MIN: DEFAULT_COMFORT_RH_MIN,
        CONF_COMFORT_RH_MAX: DEFAULT_COMFORT_RH_MAX,
        CONF_COMFORT_CO2_MIN: DEFAULT_COMFORT_CO2_MIN,
        CONF_COMFORT_CO2_MAX: DEFAULT_COMFORT_CO2_MAX,
        CONF_PRIORITY: Priority.TEMPERATURE.value,
    }


def _global_options_from_entry(entry: VentilationConfigEntry) -> dict[str, Any]:
    """Return only the options that act as global defaults."""

    options = default_global_options()
    for key in options:
        if key in entry.options:
            options[key] = entry.options[key]
    return options
