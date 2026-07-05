from __future__ import annotations

from dataclasses import dataclass
import importlib
import sys
import types
import unittest
from typing import Any


def _install_homeassistant_stubs() -> None:
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__version__ = "test"
    sys.modules["homeassistant"] = homeassistant

    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = type("ConfigEntry", (), {})
    config_entries.ConfigSubentry = type("ConfigSubentry", (), {})
    sys.modules["homeassistant.config_entries"] = config_entries
    homeassistant.config_entries = config_entries

    const = types.ModuleType("homeassistant.const")
    const.CONF_NAME = "name"
    const.PERCENTAGE = "%"
    const.STATE_UNAVAILABLE = "unavailable"
    const.STATE_UNKNOWN = "unknown"
    const.UnitOfTemperature = types.SimpleNamespace(CELSIUS="°C", FAHRENHEIT="°F")
    sys.modules["homeassistant.const"] = const

    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = type("HomeAssistant", (), {})
    core.callback = lambda func: func
    sys.modules["homeassistant.core"] = core

    helpers = types.ModuleType("homeassistant.helpers")
    event = types.ModuleType("homeassistant.helpers.event")
    event.async_track_state_change_event = lambda *args, **kwargs: (lambda: None)
    typing = types.ModuleType("homeassistant.helpers.typing")
    typing.StateType = Any
    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
    entity_platform.AddConfigEntryEntitiesCallback = Any
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.event"] = event
    sys.modules["homeassistant.helpers.typing"] = typing
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform

    components = types.ModuleType("homeassistant.components")
    sensor = types.ModuleType("homeassistant.components.sensor")

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription:
        key: str
        translation_key: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: str | None = None
        state_class: str | None = None
        options: list[str] | None = None

    sensor.SensorDeviceClass = types.SimpleNamespace(
        TEMPERATURE="temperature", HUMIDITY="humidity", ENUM="enum"
    )
    sensor.SensorEntity = type("SensorEntity", (), {})
    sensor.SensorEntityDescription = SensorEntityDescription
    sensor.SensorStateClass = types.SimpleNamespace(MEASUREMENT="measurement")
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.sensor"] = sensor


def _load_integration_modules() -> tuple[types.ModuleType, types.ModuleType]:
    _install_homeassistant_stubs()
    for module_name in list(sys.modules):
        if module_name.startswith("custom_components.ventilation_assistant"):
            del sys.modules[module_name]

    integration = importlib.import_module("custom_components.ventilation_assistant")
    sensor = importlib.import_module("custom_components.ventilation_assistant.sensor")
    return integration, sensor


class _State:
    def __init__(
        self, state: str, unit_of_measurement: str | None = None
    ) -> None:
        self.state = state
        self.attributes = {"unit_of_measurement": unit_of_measurement}


class _States:
    def __init__(self, states: dict[str, _State]) -> None:
        self._states = states

    def get(self, entity_id: str) -> _State | None:
        return self._states.get(entity_id)


class GlobalOutdoorTests(unittest.TestCase):
    def test_global_outdoor_snapshot_averages_configured_sources(self) -> None:
        integration, _ = _load_integration_modules()
        const = importlib.import_module("custom_components.ventilation_assistant.const")

        hass = types.SimpleNamespace(
            states=_States(
                {
                    "sensor.outdoor_temp_a": _State("10", "°C"),
                    "sensor.outdoor_temp_b": _State("68", "°F"),
                    "sensor.outdoor_humidity_a": _State("40", "%"),
                    "sensor.outdoor_humidity_b": _State("60", "%"),
                }
            )
        )
        coordinator = integration.GlobalOutdoorCoordinator(
            hass,
            integration.VentilationDeviceConfig(
                id=const.GLOBAL_OUTDOOR_DEVICE_ID,
                name="Outdoor",
                options={
                    const.CONF_OUTDOOR_TEMP_ENTITIES: [
                        "sensor.outdoor_temp_a",
                        "sensor.outdoor_temp_b",
                    ],
                    const.CONF_OUTDOOR_HUMIDITY_ENTITIES: [
                        "sensor.outdoor_humidity_a",
                        "sensor.outdoor_humidity_b",
                    ],
                },
            ),
        )

        snapshot = coordinator.snapshot()

        self.assertEqual(snapshot.outdoor_temp, 15.0)
        self.assertEqual(snapshot.outdoor_rh, 50.0)
        self.assertEqual(
            snapshot.outdoor_absolute_humidity,
            integration.absolute_humidity(15.0, 50.0),
        )

    def test_global_outdoor_snapshot_is_unavailable_without_sources(self) -> None:
        integration, _ = _load_integration_modules()
        const = importlib.import_module("custom_components.ventilation_assistant.const")

        coordinator = integration.GlobalOutdoorCoordinator(
            types.SimpleNamespace(states=_States({})),
            integration.VentilationDeviceConfig(
                id=const.GLOBAL_OUTDOOR_DEVICE_ID,
                name="Outdoor",
                options={
                    const.CONF_OUTDOOR_TEMP_ENTITIES: [],
                    const.CONF_OUTDOOR_HUMIDITY_ENTITIES: [],
                },
            ),
        )

        snapshot = coordinator.snapshot()

        self.assertIsNone(snapshot.outdoor_temp)
        self.assertIsNone(snapshot.outdoor_rh)
        self.assertIsNone(snapshot.outdoor_absolute_humidity)

    def test_global_outdoor_sensors_use_requested_entity_ids(self) -> None:
        integration, sensor = _load_integration_modules()
        const = importlib.import_module("custom_components.ventilation_assistant.const")
        coordinator = integration.GlobalOutdoorCoordinator(
            types.SimpleNamespace(states=_States({})),
            integration.VentilationDeviceConfig(
                id=const.GLOBAL_OUTDOOR_DEVICE_ID,
                name="Outdoor",
                options={},
            ),
        )

        entity_ids = [
            sensor.VentilationSensor(coordinator, description).entity_id
            for description in sensor.GLOBAL_OUTDOOR_SENSOR_DESCRIPTIONS
        ]

        self.assertEqual(
            entity_ids,
            [
                "sensor.ventilation_assistant_global_outdoor_temperature",
                "sensor.ventilation_assistant_global_outdoor_humidity",
                "sensor.ventilation_assistant_global_absolute_outdoor_humidity",
            ],
        )


if __name__ == "__main__":
    unittest.main()
