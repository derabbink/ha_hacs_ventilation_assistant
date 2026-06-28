"""Sensor platform for Ventilation Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VentilationCoordinator
from .const import Advice, DOMAIN

ABSOLUTE_HUMIDITY_UNIT = "g/m³"


@dataclass(frozen=True, kw_only=True)
class VentilationSensorEntityDescription(SensorEntityDescription):
    """Description for a Ventilation Assistant sensor."""

    value_key: str


SENSOR_DESCRIPTIONS = (
    VentilationSensorEntityDescription(
        key="indoor_temperature",
        translation_key="indoor_temperature",
        value_key="indoor_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VentilationSensorEntityDescription(
        key="indoor_humidity",
        translation_key="indoor_humidity",
        value_key="indoor_rh",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VentilationSensorEntityDescription(
        key="indoor_absolute_humidity",
        translation_key="indoor_absolute_humidity",
        value_key="indoor_absolute_humidity",
        native_unit_of_measurement=ABSOLUTE_HUMIDITY_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VentilationSensorEntityDescription(
        key="indoor_projected_absolute_humidity",
        translation_key="indoor_projected_absolute_humidity",
        value_key="indoor_projected_absolute_humidity",
        native_unit_of_measurement=ABSOLUTE_HUMIDITY_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VentilationSensorEntityDescription(
        key="indoor_projected_humidity",
        translation_key="indoor_projected_humidity",
        value_key="indoor_projected_rh",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VentilationSensorEntityDescription(
        key="indoor_projected_humidity_difference",
        translation_key="indoor_projected_humidity_difference",
        value_key="indoor_projected_rh_difference",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VentilationSensorEntityDescription(
        key="indoor_outdoor_temperature_difference",
        translation_key="indoor_outdoor_temperature_difference",
        value_key="indoor_outdoor_temp_difference",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VentilationSensorEntityDescription(
        key="outdoor_temperature",
        translation_key="outdoor_temperature",
        value_key="outdoor_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VentilationSensorEntityDescription(
        key="outdoor_humidity",
        translation_key="outdoor_humidity",
        value_key="outdoor_rh",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VentilationSensorEntityDescription(
        key="outdoor_absolute_humidity",
        translation_key="outdoor_absolute_humidity",
        value_key="outdoor_absolute_humidity",
        native_unit_of_measurement=ABSOLUTE_HUMIDITY_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VentilationSensorEntityDescription(
        key="doors_windows_open_percentage",
        translation_key="doors_windows_open_percentage",
        value_key="open_percentage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    VentilationSensorEntityDescription(
        key="temperature_advice",
        translation_key="temperature_advice",
        value_key="temperature_advice",
        device_class=SensorDeviceClass.ENUM,
        options=[advice.value for advice in Advice],
    ),
    VentilationSensorEntityDescription(
        key="humidity_advice",
        translation_key="humidity_advice",
        value_key="humidity_advice",
        device_class=SensorDeviceClass.ENUM,
        options=[advice.value for advice in Advice],
    ),
    VentilationSensorEntityDescription(
        key="advice",
        translation_key="advice",
        value_key="advice",
        device_class=SensorDeviceClass.ENUM,
        options=[advice.value for advice in Advice],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Ventilation Assistant sensors."""

    coordinator: VentilationCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        VentilationSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class VentilationSensor(SensorEntity):
    """A computed Ventilation Assistant sensor."""

    entity_description: VentilationSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VentilationCoordinator,
        description: VentilationSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""

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
    def native_value(self) -> Any:
        """Return the current calculated value."""

        return getattr(self.coordinator.snapshot(), self.entity_description.value_key)
