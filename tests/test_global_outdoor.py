from __future__ import annotations

import asyncio
import importlib
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_homeassistant_stubs() -> None:
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__dict__["__version__"] = "test"
    sys.modules["homeassistant"] = homeassistant

    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.__dict__.update(
        {
            "ConfigEntry": type("ConfigEntry", (), {}),
            "ConfigSubentry": type("ConfigSubentry", (), {}),
        }
    )
    sys.modules["homeassistant.config_entries"] = config_entries
    homeassistant.__dict__["config_entries"] = config_entries

    const = types.ModuleType("homeassistant.const")
    const.__dict__.update(
        {
            "CONF_NAME": "name",
            "EntityCategory": types.SimpleNamespace(CONFIG="config"),
            "PERCENTAGE": "%",
            "STATE_UNAVAILABLE": "unavailable",
            "STATE_UNKNOWN": "unknown",
            "UnitOfTemperature": types.SimpleNamespace(
                CELSIUS="°C", FAHRENHEIT="°F"
            ),
        }
    )
    sys.modules["homeassistant.const"] = const

    core = types.ModuleType("homeassistant.core")
    core.__dict__.update(
        {
            "HomeAssistant": type("HomeAssistant", (), {}),
            "callback": lambda func: func,
        }
    )
    sys.modules["homeassistant.core"] = core

    helpers = types.ModuleType("homeassistant.helpers")
    event = types.ModuleType("homeassistant.helpers.event")
    event.__dict__["async_track_state_change_event"] = (
        lambda *args, **kwargs: (lambda: None)
    )
    ha_typing = types.ModuleType("homeassistant.helpers.typing")
    ha_typing.__dict__["StateType"] = Any
    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
    entity_platform.__dict__["AddConfigEntryEntitiesCallback"] = Any
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.event"] = event
    sys.modules["homeassistant.helpers.typing"] = ha_typing
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform

    components = types.ModuleType("homeassistant.components")
    sensor = types.ModuleType("homeassistant.components.sensor")
    number = types.ModuleType("homeassistant.components.number")

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription:
        key: str
        translation_key: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: str | None = None
        state_class: str | None = None
        options: list[str] | None = None

    sensor.__dict__.update(
        {
            "SensorDeviceClass": types.SimpleNamespace(
                TEMPERATURE="temperature", HUMIDITY="humidity", ENUM="enum"
            ),
            "SensorEntity": type("SensorEntity", (), {}),
            "SensorEntityDescription": SensorEntityDescription,
            "SensorStateClass": types.SimpleNamespace(MEASUREMENT="measurement"),
        }
    )
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.sensor"] = sensor

    @dataclass(frozen=True, kw_only=True)
    class NumberEntityDescription:
        key: str
        translation_key: str | None = None
        native_min_value: float | None = None
        native_max_value: float | None = None
        native_step: float | None = None
        native_unit_of_measurement: str | None = None
        mode: str | None = None

    number.__dict__.update(
        {
            "NumberEntity": type("NumberEntity", (), {}),
            "NumberEntityDescription": NumberEntityDescription,
            "NumberMode": types.SimpleNamespace(BOX="box"),
        }
    )
    sys.modules["homeassistant.components.number"] = number

    binary_sensor = types.ModuleType("homeassistant.components.binary_sensor")
    binary_sensor.__dict__.update(
        {
            "BinarySensorDeviceClass": types.SimpleNamespace(OPENING="opening"),
            "BinarySensorEntity": type("BinarySensorEntity", (), {}),
        }
    )
    sys.modules["homeassistant.components.binary_sensor"] = binary_sensor


def _load_integration_modules() -> tuple[Any, Any]:
    _install_homeassistant_stubs()
    for module_name in list(sys.modules):
        if module_name.startswith("custom_components.ventilation_assistant"):
            del sys.modules[module_name]

    integration = cast(
        "Any", importlib.import_module("custom_components.ventilation_assistant")
    )
    sensor = cast(
        "Any", importlib.import_module("custom_components.ventilation_assistant.sensor")
    )
    return integration, sensor


def _load_binary_sensor_modules() -> tuple[Any, Any, Any]:
    _install_homeassistant_stubs()
    for module_name in list(sys.modules):
        if module_name.startswith("custom_components.ventilation_assistant"):
            del sys.modules[module_name]

    integration = cast(
        "Any", importlib.import_module("custom_components.ventilation_assistant")
    )
    sensor = cast(
        "Any", importlib.import_module("custom_components.ventilation_assistant.sensor")
    )
    binary_sensor = cast(
        "Any",
        importlib.import_module(
            "custom_components.ventilation_assistant.binary_sensor"
        ),
    )
    return integration, sensor, binary_sensor


def _const_module() -> Any:
    return cast(
        "Any", importlib.import_module("custom_components.ventilation_assistant.const")
    )


def _number_module() -> Any:
    return cast(
        "Any", importlib.import_module("custom_components.ventilation_assistant.number")
    )


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


def _global_outdoor_coordinator(integration: Any, const: Any, hass: Any) -> Any:
    return integration.GlobalOutdoorCoordinator(
        hass,
        integration.VentilationDeviceConfig(
            id=const.GLOBAL_OUTDOOR_DEVICE_ID,
            name="Outdoor",
            options={
                const.CONF_OUTDOOR_TEMP_ENTITIES: ["sensor.global_outdoor_temp"],
                const.CONF_OUTDOOR_HUMIDITY_ENTITIES: [
                    "sensor.global_outdoor_humidity"
                ],
            },
        ),
    )


class GlobalOutdoorTests(unittest.TestCase):
    def test_global_outdoor_snapshot_averages_configured_sources(self) -> None:
        integration, _ = _load_integration_modules()
        const = _const_module()

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
            coordinator.input_entity_ids,
            {
                "sensor.outdoor_temp_a",
                "sensor.outdoor_temp_b",
                "sensor.outdoor_humidity_a",
                "sensor.outdoor_humidity_b",
            },
        )
        self.assertEqual(
            snapshot.outdoor_absolute_humidity,
            integration.absolute_humidity(15.0, 50.0),
        )

    def test_global_outdoor_snapshot_is_unavailable_without_sources(self) -> None:
        integration, _ = _load_integration_modules()
        const = _const_module()

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
        self.assertEqual(coordinator.input_entity_ids, set())

    def test_global_outdoor_snapshot_is_unavailable_with_missing_source_options(
        self,
    ) -> None:
        integration, sensor = _load_integration_modules()
        const = _const_module()
        coordinator = integration.GlobalOutdoorCoordinator(
            types.SimpleNamespace(states=_States({})),
            integration.VentilationDeviceConfig(
                id=const.GLOBAL_OUTDOOR_DEVICE_ID,
                name="Outdoor",
                options={},
            ),
        )

        snapshot = coordinator.snapshot()
        entities = [
            sensor.VentilationSensor(coordinator, description)
            for description in sensor.GLOBAL_OUTDOOR_SENSOR_DESCRIPTIONS
        ]

        self.assertIsNone(snapshot.outdoor_temp)
        self.assertIsNone(snapshot.outdoor_rh)
        self.assertIsNone(snapshot.outdoor_absolute_humidity)
        self.assertEqual(coordinator.input_entity_ids, set())
        self.assertTrue(all(entity.native_value is None for entity in entities))
        self.assertTrue(all(not entity.available for entity in entities))

    def test_global_outdoor_sensors_use_requested_entity_ids(self) -> None:
        integration, sensor = _load_integration_modules()
        const = _const_module()
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

    def test_temperature_number_reports_preferred_temperature_unit(self) -> None:
        integration, _ = _load_integration_modules()
        number = _number_module()
        const = _const_module()

        hass = types.SimpleNamespace(
            states=_States({}),
            data={},
            config=types.SimpleNamespace(
                units=types.SimpleNamespace(temperature_unit="°F")
            ),
        )
        coordinator = integration.VentilationCoordinator(
            hass,
            integration.VentilationDeviceConfig(
                id="area",
                name="Area",
                options={
                    const.CONF_COMFORT_TEMP_MIN: 19.0,
                    const.CONF_COMFORT_TEMP_MAX: 24.0,
                    const.CONF_COMFORT_RH_MIN: 40.0,
                    const.CONF_COMFORT_RH_MAX: 60.0,
                },
            ),
        )
        entity = number.VentilationNumber(
            types.SimpleNamespace(
                data={const.CONF_KIND: const.CONF_DEVICE}, options={}
            ),
            coordinator,
            number.NUMBER_DESCRIPTIONS[0],
        )
        entity.hass = hass

        self.assertEqual(entity.native_unit_of_measurement, "°F")
        self.assertEqual(entity.native_min_value, -22.0)
        self.assertEqual(entity.native_max_value, 122.0)
        self.assertEqual(entity.native_value, 66.2)

    def test_temperature_number_stores_fahrenheit_changes_as_celsius(
        self,
    ) -> None:
        integration, _ = _load_integration_modules()
        number = _number_module()
        const = _const_module()

        updates: list[dict[str, Any]] = []
        hass = types.SimpleNamespace(
            states=_States({}),
            data={},
            config=types.SimpleNamespace(
                units=types.SimpleNamespace(temperature_unit="°F")
            ),
            config_entries=types.SimpleNamespace(
                async_update_entry=lambda entry, options: updates.append(options)
            ),
        )
        entry = types.SimpleNamespace(
            data={const.CONF_KIND: const.CONF_DEVICE},
            options={const.CONF_COMFORT_TEMP_MIN: 19.0},
        )
        coordinator = integration.VentilationCoordinator(
            hass,
            integration.VentilationDeviceConfig(
                id="area",
                name="Area",
                options={const.CONF_COMFORT_TEMP_MIN: 19.0},
            ),
        )
        entity = number.VentilationNumber(
            entry,
            coordinator,
            number.NUMBER_DESCRIPTIONS[0],
        )
        entity.hass = hass

        asyncio.run(entity.async_set_native_value(68.0))

        self.assertEqual(updates, [{const.CONF_COMFORT_TEMP_MIN: 20.0}])
        self.assertEqual(coordinator.config.options[const.CONF_COMFORT_TEMP_MIN], 20.0)

    def test_device_snapshot_copies_global_outdoor_values_without_overrides(
        self,
    ) -> None:
        integration, _ = _load_integration_modules()
        const = _const_module()
        hass = types.SimpleNamespace(
            data={const.DOMAIN: {}},
            states=_States(
                {
                    "sensor.global_outdoor_temp": _State("14", "°C"),
                    "sensor.global_outdoor_humidity": _State("65", "%"),
                    "sensor.indoor_temp": _State("21", "°C"),
                }
            ),
        )
        global_coordinator = _global_outdoor_coordinator(integration, const, hass)
        coordinator = integration.VentilationCoordinator(
            hass,
            integration.VentilationDeviceConfig(
                id="living_room",
                name="Living room",
                options={const.CONF_INDOOR_TEMP_ENTITIES: ["sensor.indoor_temp"]},
            ),
            global_coordinator=global_coordinator,
        )

        snapshot = coordinator.snapshot()

        self.assertEqual(snapshot.outdoor_temp, 14.0)
        self.assertEqual(snapshot.outdoor_rh, 65.0)
        self.assertEqual(
            snapshot.outdoor_absolute_humidity,
            integration.absolute_humidity(14.0, 65.0),
        )
        self.assertEqual(
            snapshot.indoor_projected_absolute_humidity,
            integration.absolute_humidity(14.0, 65.0),
        )
        self.assertEqual(
            coordinator.input_entity_ids,
            {"sensor.indoor_temp"},
        )

    def test_device_snapshot_uses_local_temperature_with_global_humidity(
        self,
    ) -> None:
        integration, _ = _load_integration_modules()
        const = _const_module()
        hass = types.SimpleNamespace(
            data={const.DOMAIN: {}},
            states=_States(
                {
                    "sensor.outdoor_temp_a": _State("18", "°C"),
                    "sensor.outdoor_temp_b": _State("20", "°C"),
                    "sensor.global_outdoor_temp": _State("8", "°C"),
                    "sensor.global_outdoor_humidity": _State("60", "%"),
                }
            ),
        )
        global_coordinator = _global_outdoor_coordinator(integration, const, hass)
        coordinator = integration.VentilationCoordinator(
            hass,
            integration.VentilationDeviceConfig(
                id="bedroom",
                name="Bedroom",
                options={
                    const.CONF_OUTDOOR_TEMP_ENTITIES: [
                        "sensor.outdoor_temp_a",
                        "sensor.outdoor_temp_b",
                    ]
                },
            ),
            global_coordinator=global_coordinator,
        )

        snapshot = coordinator.snapshot()

        self.assertEqual(snapshot.outdoor_temp, 19.0)
        self.assertEqual(snapshot.outdoor_rh, 60.0)
        self.assertEqual(
            snapshot.outdoor_absolute_humidity,
            integration.absolute_humidity(19.0, 60.0),
        )
        self.assertEqual(
            coordinator.input_entity_ids,
            {
                "sensor.outdoor_temp_a",
                "sensor.outdoor_temp_b",
            },
        )

    def test_device_snapshot_uses_global_temperature_with_local_humidity(
        self,
    ) -> None:
        integration, _ = _load_integration_modules()
        const = _const_module()
        hass = types.SimpleNamespace(
            data={const.DOMAIN: {}},
            states=_States(
                {
                    "sensor.global_outdoor_temp": _State("12", "°C"),
                    "sensor.global_outdoor_humidity": _State("60", "%"),
                    "sensor.outdoor_humidity_a": _State("45", "%"),
                    "sensor.outdoor_humidity_b": _State("55", "%"),
                }
            ),
        )
        global_coordinator = _global_outdoor_coordinator(integration, const, hass)
        coordinator = integration.VentilationCoordinator(
            hass,
            integration.VentilationDeviceConfig(
                id="office",
                name="Office",
                options={
                    const.CONF_OUTDOOR_HUMIDITY_ENTITIES: [
                        "sensor.outdoor_humidity_a",
                        "sensor.outdoor_humidity_b",
                    ]
                },
            ),
            global_coordinator=global_coordinator,
        )

        snapshot = coordinator.snapshot()

        self.assertEqual(snapshot.outdoor_temp, 12.0)
        self.assertEqual(snapshot.outdoor_rh, 50.0)
        self.assertEqual(
            snapshot.outdoor_absolute_humidity,
            integration.absolute_humidity(12.0, 50.0),
        )
        self.assertEqual(
            coordinator.input_entity_ids,
            {
                "sensor.outdoor_humidity_a",
                "sensor.outdoor_humidity_b",
            },
        )

    def test_device_snapshot_accepts_scalar_entity_options(self) -> None:
        integration, _ = _load_integration_modules()
        const = _const_module()
        hass = types.SimpleNamespace(
            data={const.DOMAIN: {}},
            states=_States(
                {
                    "sensor.indoor_temp": _State("22", "°C"),
                    "sensor.indoor_humidity": _State("48", "%"),
                    "sensor.global_outdoor_temp": _State("10", "°C"),
                    "sensor.global_outdoor_humidity": _State("70", "%"),
                }
            ),
        )
        global_coordinator = _global_outdoor_coordinator(integration, const, hass)
        coordinator = integration.VentilationCoordinator(
            hass,
            integration.VentilationDeviceConfig(
                id="kitchen",
                name="Kitchen",
                options={
                    const.CONF_INDOOR_TEMP_ENTITIES: "sensor.indoor_temp",
                    const.CONF_INDOOR_HUMIDITY_ENTITIES: "sensor.indoor_humidity",
                    const.CONF_OUTDOOR_TEMP_ENTITIES: None,
                    const.CONF_OUTDOOR_HUMIDITY_ENTITIES: None,
                },
            ),
            global_coordinator=global_coordinator,
        )

        snapshot = coordinator.snapshot()

        self.assertEqual(snapshot.indoor_temp, 22.0)
        self.assertEqual(snapshot.indoor_rh, 48.0)
        self.assertEqual(snapshot.outdoor_temp, 10.0)
        self.assertEqual(snapshot.outdoor_rh, 70.0)
        self.assertEqual(
            snapshot.outdoor_absolute_humidity,
            integration.absolute_humidity(10.0, 70.0),
        )
        self.assertIn("sensor.indoor_temp", coordinator.input_entity_ids)
        self.assertIn("sensor.indoor_humidity", coordinator.input_entity_ids)

    def test_device_snapshot_has_no_indoor_values_without_indoor_sources(
        self,
    ) -> None:
        integration, _ = _load_integration_modules()
        const = _const_module()
        hass = types.SimpleNamespace(
            data={const.DOMAIN: {}},
            states=_States(
                {
                    "sensor.global_outdoor_temp": _State("10", "°C"),
                    "sensor.global_outdoor_humidity": _State("70", "%"),
                }
            ),
        )
        global_coordinator = _global_outdoor_coordinator(integration, const, hass)
        coordinator = integration.VentilationCoordinator(
            hass,
            integration.VentilationDeviceConfig(
                id="kitchen",
                name="Kitchen",
                options={
                    const.CONF_INDOOR_TEMP_ENTITIES: [],
                    const.CONF_INDOOR_HUMIDITY_ENTITIES: [],
                    const.CONF_OUTDOOR_TEMP_ENTITIES: [],
                    const.CONF_OUTDOOR_HUMIDITY_ENTITIES: [],
                },
            ),
            global_coordinator=global_coordinator,
        )

        snapshot = coordinator.snapshot()

        self.assertIsNone(snapshot.indoor_temp)
        self.assertIsNone(snapshot.indoor_rh)
        self.assertIsNone(snapshot.indoor_absolute_humidity)
        self.assertIsNone(snapshot.indoor_projected_absolute_humidity)
        self.assertIsNone(snapshot.indoor_projected_rh)
        self.assertIsNone(snapshot.indoor_projected_rh_difference)
        self.assertIsNone(snapshot.indoor_outdoor_temp_difference)
        self.assertIsNone(snapshot.temperature_advice)
        self.assertIsNone(snapshot.humidity_advice)
        self.assertIsNone(snapshot.advice)

    def test_indoor_sensor_entities_are_available_when_sources_have_values(
        self,
    ) -> None:
        integration, sensor = _load_integration_modules()
        const = _const_module()
        hass = types.SimpleNamespace(
            data={const.DOMAIN: {}},
            states=_States(
                {
                    "sensor.indoor_temp": _State("22", "°C"),
                    "sensor.indoor_humidity": _State("48", "%"),
                    "sensor.global_outdoor_temp": _State("10", "°C"),
                    "sensor.global_outdoor_humidity": _State("70", "%"),
                }
            ),
        )
        global_coordinator = _global_outdoor_coordinator(integration, const, hass)
        coordinator = integration.VentilationCoordinator(
            hass,
            integration.VentilationDeviceConfig(
                id="kitchen",
                name="Kitchen",
                options={
                    const.CONF_INDOOR_TEMP_ENTITIES: ["sensor.indoor_temp"],
                    const.CONF_INDOOR_HUMIDITY_ENTITIES: ["sensor.indoor_humidity"],
                    const.CONF_OUTDOOR_TEMP_ENTITIES: [],
                    const.CONF_OUTDOOR_HUMIDITY_ENTITIES: [],
                },
            ),
            global_coordinator=global_coordinator,
        )
        entities = {
            description.key: sensor.VentilationSensor(coordinator, description)
            for description in sensor.SENSOR_DESCRIPTIONS
            if description.key in ("indoor_temperature", "indoor_humidity")
        }

        self.assertTrue(entities["indoor_temperature"].available)
        self.assertEqual(entities["indoor_temperature"].native_value, 22.0)
        self.assertTrue(entities["indoor_humidity"].available)
        self.assertEqual(entities["indoor_humidity"].native_value, 48.0)

    def test_indoor_sensor_entities_are_unavailable_without_sources(self) -> None:
        integration, sensor = _load_integration_modules()
        const = _const_module()
        hass = types.SimpleNamespace(
            data={const.DOMAIN: {}},
            states=_States(
                {
                    "sensor.global_outdoor_temp": _State("10", "°C"),
                    "sensor.global_outdoor_humidity": _State("70", "%"),
                }
            ),
        )
        global_coordinator = _global_outdoor_coordinator(integration, const, hass)
        coordinator = integration.VentilationCoordinator(
            hass,
            integration.VentilationDeviceConfig(
                id="kitchen",
                name="Kitchen",
                options={
                    const.CONF_INDOOR_TEMP_ENTITIES: [],
                    const.CONF_INDOOR_HUMIDITY_ENTITIES: [],
                    const.CONF_OUTDOOR_TEMP_ENTITIES: [],
                    const.CONF_OUTDOOR_HUMIDITY_ENTITIES: [],
                },
            ),
            global_coordinator=global_coordinator,
        )
        entities = {
            description.key: sensor.VentilationSensor(coordinator, description)
            for description in sensor.SENSOR_DESCRIPTIONS
            if description.key in ("indoor_temperature", "indoor_humidity")
        }

        self.assertFalse(entities["indoor_temperature"].available)
        self.assertIsNone(entities["indoor_temperature"].native_value)
        self.assertFalse(entities["indoor_humidity"].available)
        self.assertIsNone(entities["indoor_humidity"].native_value)

    def test_door_window_entities_are_unavailable_without_sources(self) -> None:
        integration, sensor, binary_sensor = _load_binary_sensor_modules()
        const = _const_module()
        hass = types.SimpleNamespace(data={const.DOMAIN: {}}, states=_States({}))
        coordinator = integration.VentilationCoordinator(
            hass,
            integration.VentilationDeviceConfig(
                id="kitchen",
                name="Kitchen",
                options={
                    const.CONF_INDOOR_TEMP_ENTITIES: [],
                    const.CONF_INDOOR_HUMIDITY_ENTITIES: [],
                    const.CONF_OUTDOOR_TEMP_ENTITIES: [],
                    const.CONF_OUTDOOR_HUMIDITY_ENTITIES: [],
                    const.CONF_DOOR_WINDOW_ENTITIES: [],
                },
            ),
        )
        percentage_entity = next(
            sensor.VentilationSensor(coordinator, description)
            for description in sensor.SENSOR_DESCRIPTIONS
            if description.key == "doors_windows_open_percentage"
        )
        any_open_entity = binary_sensor.AnyDoorWindowOpenBinarySensor(coordinator)

        self.assertFalse(percentage_entity.available)
        self.assertIsNone(percentage_entity.native_value)
        self.assertFalse(any_open_entity.available)
        self.assertIsNone(any_open_entity.is_on)


if __name__ == "__main__":
    unittest.main()
