"""Select platform for Ventilation Assistant."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import (
    VentilationCoordinator,
    async_update_device_options,
    coordinators_for_entry,
)
from .const import CONF_GLOBAL, CONF_KIND, CONF_PRIORITY, DOMAIN, Priority


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Ventilation Assistant selects."""

    for coordinator in coordinators_for_entry(hass, entry):
        kwargs = (
            {"config_subentry_id": coordinator.device_id}
            if entry.data[CONF_KIND] == CONF_GLOBAL
            else {}
        )
        async_add_entities([VentilationPrioritySelect(entry, coordinator)], **kwargs)


class VentilationPrioritySelect(SelectEntity):
    """Priority selector for Ventilation Assistant advice."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_options = [priority.value for priority in Priority]
    _attr_translation_key = "priority"

    def __init__(self, entry: ConfigEntry, coordinator: VentilationCoordinator) -> None:
        """Initialize the select."""

        self._entry = entry
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.device_id}_priority"
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
    def current_option(self) -> str:
        """Return the current configured priority."""

        return self.coordinator.comfort_settings.priority.value

    async def async_select_option(self, option: str) -> None:
        """Update the configured priority."""

        if option not in self.options:
            return

        options = (
            dict(self.coordinator.config.options)
            if self._entry.data.get(CONF_KIND) == CONF_GLOBAL
            else dict(self._entry.options)
        )
        options[CONF_PRIORITY] = option
        async_update_device_options(self.hass, self._entry, self.coordinator, options)
