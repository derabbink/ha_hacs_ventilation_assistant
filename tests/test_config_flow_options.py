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
    const.__dict__["CONF_NAME"] = "name"
    sys.modules["homeassistant.const"] = const

    core = types.ModuleType("homeassistant.core")
    core.__dict__["callback"] = lambda func: func
    sys.modules["homeassistant.core"] = core

    helpers = types.ModuleType("homeassistant.helpers")
    selector = types.ModuleType("homeassistant.helpers.selector")

    class _SelectorConfig:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    class _Selector:
        def __init__(self, config: Any) -> None:
            self.config = config

    selector.__dict__.update(
        {
            "EntitySelector": _Selector,
            "EntitySelectorConfig": _SelectorConfig,
            "NumberSelector": _Selector,
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
            "Optional": lambda key, **kwargs: key,
            "Required": lambda key, **kwargs: key,
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


if __name__ == "__main__":
    unittest.main()
