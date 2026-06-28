"""Number platform for Ventilation Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VentilationCoordinator
from .const import (
    CONF_COMFORT_RH_MAX,
    CONF_COMFORT_RH_MIN,
    CONF_COMFORT_TEMP_MAX,
    CONF_COMFORT_TEMP_MIN,
    DOMAIN,
)


@dataclass(frozen=True, kw_only=True)
class VentilationNumberEntityDescription(NumberEntityDescription):
    """Description for a Ventilation Assistant number."""

    option_key: str


NUMBER_DESCRIPTIONS = (
    VentilationNumberEntityDescription(
        key="comfort_temp_min",
        translation_key="comfort_temp_min",
        option_key=CONF_COMFORT_TEMP_MIN,
        native_min_value=-30,
        native_max_value=50,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
    ),
    VentilationNumberEntityDescription(
        key="comfort_temp_max",
        translation_key="comfort_temp_max",
        option_key=CONF_COMFORT_TEMP_MAX,
        native_min_value=-30,
        native_max_value=50,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
    ),
    VentilationNumberEntityDescription(
        key="comfort_rh_min",
        translation_key="comfort_rh_min",
        option_key=CONF_COMFORT_RH_MIN,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
    ),
    VentilationNumberEntityDescription(
        key="comfort_rh_max",
        translation_key="comfort_rh_max",
        option_key=CONF_COMFORT_RH_MAX,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Ventilation Assistant numbers."""

    coordinator: VentilationCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        VentilationNumber(entry, coordinator, description)
        for description in NUMBER_DESCRIPTIONS
    )


class VentilationNumber(NumberEntity):
    """A configurable Ventilation Assistant number."""

    entity_description: VentilationNumberEntityDescription
    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: VentilationCoordinator,
        description: VentilationNumberEntityDescription,
    ) -> None:
        """Initialize the number."""

        self._entry = entry
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.device_id)},
            "name": coordinator.device_name,
            "manufacturer": "Ventilation Assistant",
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""

        self.async_on_remove(
            self.coordinator.async_add_listener(self._async_coordinator_updated)
        )

    @callback
    def _async_coordinator_updated(self) -> None:
        """Write the latest state."""

        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        """Return the current configured value."""

        settings = self.coordinator.comfort_settings
        values: dict[str, float] = {
            CONF_COMFORT_TEMP_MIN: settings.temp_min,
            CONF_COMFORT_TEMP_MAX: settings.temp_max,
            CONF_COMFORT_RH_MIN: settings.rh_min,
            CONF_COMFORT_RH_MAX: settings.rh_max,
        }
        return values[self.entity_description.option_key]

    async def async_set_native_value(self, value: float) -> None:
        """Update the configured value."""

        options: dict[str, Any] = dict(self._entry.options)
        options[self.entity_description.option_key] = value
        self.hass.config_entries.async_update_entry(self._entry, options=options)
        self.coordinator.async_update_options(options)

