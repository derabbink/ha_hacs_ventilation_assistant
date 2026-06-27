from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
import unittest

PACKAGE = "custom_components.ventilation_assistant"
ROOT = pathlib.Path(__file__).parents[1] / "custom_components" / "ventilation_assistant"

package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package

for module_name in ("const", "calculations"):
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.{module_name}", ROOT / f"{module_name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{PACKAGE}.{module_name}"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)

from custom_components.ventilation_assistant.calculations import (  # noqa: E402
    ComfortSettings,
    absolute_humidity,
    relative_humidity,
    ventilation_advice,
)
from custom_components.ventilation_assistant.const import Advice, Priority  # noqa: E402


class CalculationTests(unittest.TestCase):
    def test_absolute_humidity_round_trip(self) -> None:
        absolute = absolute_humidity(20.0, 50.0)

        self.assertEqual(absolute, 8.64)
        self.assertEqual(relative_humidity(20.0, absolute), 50.01)

    def test_temperature_priority_advises_open_when_cooling_helps(self) -> None:
        advice = ventilation_advice(
            settings=ComfortSettings(19, 24, 40, 60, Priority.TEMPERATURE),
            any_open=False,
            indoor_temp=26,
            outdoor_temp=18,
            indoor_rh=50,
            projected_rh=55,
        )

        self.assertEqual(advice, Advice.OPEN)

    def test_humidity_priority_advises_close_when_outdoor_air_worsens_humidity(
        self,
    ) -> None:
        advice = ventilation_advice(
            settings=ComfortSettings(19, 24, 40, 60, Priority.HUMIDITY),
            any_open=True,
            indoor_temp=21,
            outdoor_temp=18,
            indoor_rh=70,
            projected_rh=75,
        )

        self.assertEqual(advice, Advice.CLOSE)


if __name__ == "__main__":
    unittest.main()
