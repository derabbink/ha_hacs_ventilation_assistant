"""Binary sensor platform for Ventilation Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import VentilationCoordinator, device_coordinators_for_entry
from .const import CONF_GLOBAL, CONF_KIND, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Ventilation Assistant binary sensors."""

    for coordinator in device_coordinators_for_entry(hass, entry):
        kwargs = (
            {"config_subentry_id": coordinator.device_id}
            if entry.data[CONF_KIND] == CONF_GLOBAL
            else {}
        )
        async_add_entities([AnyDoorWindowOpenBinarySensor(coordinator)], **kwargs)


class AnyDoorWindowOpenBinarySensor(BinarySensorEntity):
    """Whether any configured door or window contact is open."""

    _attr_has_entity_name = True
    _attr_translation_key = "any_door_window_open"
    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(self, coordinator: VentilationCoordinator) -> None:
        """Initialize the binary sensor."""

        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.device_id}_any_door_window_open"
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
    def available(self) -> bool:
        """Return whether the current contact state is available."""

        return self.coordinator.snapshot().any_open is not None

    @property
    def is_on(self) -> bool | None:
        """Return whether any configured contact is open."""

        return self.coordinator.snapshot().any_open
