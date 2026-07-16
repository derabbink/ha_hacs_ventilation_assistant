from __future__ import annotations

import importlib
import sys
import types
import unittest
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).parents[1]
PACKAGE = "custom_components.ventilation_assistant"
INTEGRATION_ROOT = ROOT / "custom_components" / "ventilation_assistant"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_homeassistant_stubs() -> None:
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__dict__["__version__"] = "test"
    sys.modules["homeassistant"] = homeassistant

    config_entries = types.ModuleType("homeassistant.config_entries")

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs: Any) -> None:
            del kwargs

    config_entries.__dict__.update(
        {
            "ConfigEntry": type("ConfigEntry", (), {}),
            "ConfigFlow": ConfigFlow,
            "ConfigFlowResult": dict[str, Any],
            "ConfigSubentryFlow": type("ConfigSubentryFlow", (), {}),
            "OptionsFlow": type("OptionsFlow", (), {}),
            "SubentryFlowResult": dict[str, Any],
        }
    )
    sys.modules["homeassistant.config_entries"] = config_entries
    homeassistant.__dict__["config_entries"] = config_entries

    const = types.ModuleType("homeassistant.const")
    const.__dict__.update(
        {
            "CONF_NAME": "name",
            "UnitOfTemperature": types.SimpleNamespace(
                CELSIUS="°C", FAHRENHEIT="°F"
            ),
        }
    )
    sys.modules["homeassistant.const"] = const

    core = types.ModuleType("homeassistant.core")
    core.__dict__["callback"] = lambda func: func
    sys.modules["homeassistant.core"] = core

    class _Marker(str):
        def __new__(cls, key: str, kind: str, **kwargs: Any) -> _Marker:
            marker = str.__new__(cls, key)
            marker.kind = kind
            marker.kwargs = kwargs
            return marker

    helpers = types.ModuleType("homeassistant.helpers")
    selector = types.ModuleType("homeassistant.helpers.selector")

    class _SelectorConfig:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    class _Selector:
        def __init__(self, config: Any) -> None:
            self.config = config

    class _NumberSelector(_Selector):
        pass

    selector.__dict__.update(
        {
            "EntitySelector": _Selector,
            "EntitySelectorConfig": _SelectorConfig,
            "NumberSelector": _NumberSelector,
            "NumberSelectorConfig": _SelectorConfig,
            "NumberSelectorMode": types.SimpleNamespace(BOX="box"),
            "SelectOptionDict": lambda **kwargs: kwargs,
            "SelectSelector": _Selector,
            "SelectSelectorConfig": _SelectorConfig,
            "SelectSelectorMode": types.SimpleNamespace(DROPDOWN="dropdown"),
        }
    )
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.selector"] = selector

    voluptuous = types.ModuleType("voluptuous")
    voluptuous.__dict__.update(
        {
            "Any": lambda *args: args,
            "Optional": lambda key, **kwargs: _Marker(key, "optional", **kwargs),
            "Required": lambda key, **kwargs: _Marker(key, "required", **kwargs),
            "Schema": lambda schema: schema,
        }
    )
    sys.modules["voluptuous"] = voluptuous


def _load_config_flow_module() -> Any:
    _install_homeassistant_stubs()
    for module_name in list(sys.modules):
        if module_name.startswith("custom_components.ventilation_assistant"):
            del sys.modules[module_name]

    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(INTEGRATION_ROOT)]
    sys.modules[PACKAGE] = package

    return cast(
        "Any",
        importlib.import_module("custom_components.ventilation_assistant.config_flow"),
    )


class ConfigFlowOptionsTests(unittest.TestCase):
    def test_device_options_clear_omitted_selectors(self) -> None:
        config_flow = _load_config_flow_module()
        const = importlib.import_module("custom_components.ventilation_assistant.const")

        options = config_flow._device_options(
            {
                const.CONF_OUTDOOR_TEMP_ENTITIES: [],
                const.CONF_OUTDOOR_HUMIDITY_ENTITIES: [],
            }
        )

        self.assertEqual(options[const.CONF_INDOOR_TEMP_ENTITIES], [])
        self.assertEqual(options[const.CONF_INDOOR_HUMIDITY_ENTITIES], [])
        self.assertEqual(options[const.CONF_OUTDOOR_TEMP_ENTITIES], [])
        self.assertEqual(options[const.CONF_OUTDOOR_HUMIDITY_ENTITIES], [])

    def test_options_store_fahrenheit_comfort_temperatures_as_celsius(self) -> None:
        config_flow = _load_config_flow_module()
        const = importlib.import_module("custom_components.ventilation_assistant.const")

        global_options = config_flow._global_options(
            {
                const.CONF_COMFORT_TEMP_MIN: 68.0,
                const.CONF_COMFORT_TEMP_MAX: 75.2,
                const.CONF_COMFORT_RH_MIN: 40.0,
                const.CONF_COMFORT_RH_MAX: 60.0,
                const.CONF_PRIORITY: const.Priority.TEMPERATURE.value,
            },
            temperature_unit="°F",
        )
        device_options = config_flow._device_options(
            {
                const.CONF_COMFORT_TEMP_MIN: 68.0,
                const.CONF_COMFORT_TEMP_MAX: 75.2,
            },
            temperature_unit="°F",
        )

        self.assertEqual(global_options[const.CONF_COMFORT_TEMP_MIN], 20.0)
        self.assertEqual(global_options[const.CONF_COMFORT_TEMP_MAX], 24.0)
        self.assertEqual(device_options[const.CONF_COMFORT_TEMP_MIN], 20.0)
        self.assertEqual(device_options[const.CONF_COMFORT_TEMP_MAX], 24.0)

    def test_device_options_normalize_scalar_selectors(self) -> None:
        config_flow = _load_config_flow_module()
        const = importlib.import_module("custom_components.ventilation_assistant.const")

        options = config_flow._device_options(
            {
                const.CONF_INDOOR_TEMP_ENTITIES: "sensor.indoor_temp",
                const.CONF_INDOOR_HUMIDITY_ENTITIES: None,
            }
        )

        self.assertEqual(
            options[const.CONF_INDOOR_TEMP_ENTITIES], ["sensor.indoor_temp"]
        )
        self.assertEqual(options[const.CONF_INDOOR_HUMIDITY_ENTITIES], [])

    def test_device_schema_uses_number_selectors_for_comfort_overrides(self) -> None:
        config_flow = _load_config_flow_module()
        const = importlib.import_module("custom_components.ventilation_assistant.const")
        selector = importlib.import_module("homeassistant.helpers.selector")

        schema = config_flow._device_schema(temperature_unit="°F")

        for key in (
            const.CONF_COMFORT_TEMP_MIN,
            const.CONF_COMFORT_TEMP_MAX,
            const.CONF_COMFORT_RH_MIN,
            const.CONF_COMFORT_RH_MAX,
        ):
            self.assertIsInstance(schema[key], selector.NumberSelector)

        self.assertEqual(
            schema[const.CONF_COMFORT_TEMP_MIN].config.kwargs,
            {
                "min": -22.0,
                "max": 122.0,
                "step": 0.5,
                "mode": selector.NumberSelectorMode.BOX,
                "unit_of_measurement": "°F",
            },
        )
        self.assertEqual(
            schema[const.CONF_COMFORT_RH_MIN].config.kwargs,
            {
                "min": 0,
                "max": 100,
                "step": 1,
                "mode": selector.NumberSelectorMode.BOX,
                "unit_of_measurement": "%",
            },
        )

    def test_device_schema_prefills_only_configured_comfort_overrides(self) -> None:
        config_flow = _load_config_flow_module()
        const = importlib.import_module("custom_components.ventilation_assistant.const")

        empty_schema = config_flow._device_schema(temperature_unit="°F")
        empty_temp_min = next(
            field
            for field in empty_schema
            if field == const.CONF_COMFORT_TEMP_MIN
        )
        self.assertNotIn("default", empty_temp_min.kwargs)

        configured_schema = config_flow._device_schema(
            {
                const.CONF_COMFORT_TEMP_MIN: 20.0,
                const.CONF_COMFORT_RH_MIN: 45.0,
            },
            temperature_unit="°F",
        )
        configured_temp_min = next(
            field
            for field in configured_schema
            if field == const.CONF_COMFORT_TEMP_MIN
        )
        configured_rh_min = next(
            field
            for field in configured_schema
            if field == const.CONF_COMFORT_RH_MIN
        )
        self.assertEqual(configured_temp_min.kwargs["default"], 68.0)
        self.assertEqual(configured_rh_min.kwargs["default"], 45.0)

    def test_global_schema_displays_stored_temperatures_in_preferred_unit(self) -> None:
        config_flow = _load_config_flow_module()
        const = importlib.import_module("custom_components.ventilation_assistant.const")

        schema = config_flow._global_schema(
            {
                const.CONF_COMFORT_TEMP_MIN: 20.0,
                const.CONF_COMFORT_TEMP_MAX: 24.0,
            },
            temperature_unit="°F",
        )
        temp_min = next(
            field
            for field in schema
            if field == const.CONF_COMFORT_TEMP_MIN
        )
        temp_max = next(
            field
            for field in schema
            if field == const.CONF_COMFORT_TEMP_MAX
        )

        self.assertEqual(temp_min.kwargs["default"], 68.0)
        self.assertEqual(temp_max.kwargs["default"], 75.2)


if __name__ == "__main__":
    unittest.main()
