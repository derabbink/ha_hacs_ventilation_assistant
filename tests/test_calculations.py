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
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{PACKAGE}.{module_name}"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)

from custom_components.ventilation_assistant.calculations import (  # noqa: E402
    ComfortSettings,
    absolute_humidity,
    relative_humidity,
    ventilation_advice,
    ventilation_advices,
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

    def test_returns_temperature_humidity_and_overall_advice(self) -> None:
        advices = ventilation_advices(
            settings=ComfortSettings(19, 24, 40, 60, Priority.TEMPERATURE),
            any_open=None,
            indoor_temp=26,
            outdoor_temp=18,
            indoor_rh=70,
            projected_rh=75,
        )

        self.assertEqual(advices.temperature, Advice.OPEN)
        self.assertEqual(advices.humidity, Advice.CLOSE)
        self.assertIsNone(advices.carbon_dioxide)
        self.assertEqual(advices.overall, Advice.OPEN)

    def test_carbon_dioxide_advice_opens_when_ventilation_reduces_high_co2(
        self,
    ) -> None:
        advices = ventilation_advices(
            settings=ComfortSettings(
                19, 24, 40, 60, Priority.CO2, co2_min=400, co2_max=2000
            ),
            any_open=None,
            indoor_temp=22,
            outdoor_temp=18,
            indoor_rh=50,
            projected_rh=50,
            indoor_co2=2400,
            outdoor_co2=500,
        )

        self.assertEqual(advices.carbon_dioxide, Advice.OPEN)
        self.assertEqual(advices.overall, Advice.OPEN)

    def test_carbon_dioxide_advice_applies_contact_state(self) -> None:
        advices = ventilation_advices(
            settings=ComfortSettings(
                19, 24, 40, 60, Priority.CO2, co2_min=400, co2_max=2000
            ),
            any_open=True,
            indoor_temp=None,
            outdoor_temp=None,
            indoor_rh=None,
            projected_rh=None,
            indoor_co2=2400,
            outdoor_co2=500,
        )

        self.assertEqual(advices.carbon_dioxide, Advice.KEEP_OPEN)
        self.assertEqual(advices.overall, Advice.KEEP_OPEN)

    def test_co2_priority_falls_back_to_temperature_then_humidity(self) -> None:
        temperature_fallback = ventilation_advice(
            settings=ComfortSettings(19, 24, 40, 60, Priority.CO2),
            any_open=None,
            indoor_temp=26,
            outdoor_temp=18,
            indoor_rh=70,
            projected_rh=75,
        )
        humidity_fallback = ventilation_advice(
            settings=ComfortSettings(19, 24, 40, 60, Priority.CO2),
            any_open=None,
            indoor_temp=None,
            outdoor_temp=None,
            indoor_rh=70,
            projected_rh=55,
        )

        self.assertEqual(temperature_fallback, Advice.OPEN)
        self.assertEqual(humidity_fallback, Advice.OPEN)

    def test_temperature_and_humidity_priorities_fall_back_to_co2_last(self) -> None:
        for priority in (Priority.TEMPERATURE, Priority.HUMIDITY):
            with self.subTest(priority=priority):
                advice = ventilation_advice(
                    settings=ComfortSettings(19, 24, 40, 60, priority),
                    any_open=False,
                    indoor_temp=None,
                    outdoor_temp=None,
                    indoor_rh=None,
                    projected_rh=None,
                    indoor_co2=2400,
                    outdoor_co2=500,
                )

                self.assertEqual(advice, Advice.OPEN)

    def test_split_advices_include_contact_state_when_available(self) -> None:
        advices = ventilation_advices(
            settings=ComfortSettings(19, 24, 40, 60, Priority.HUMIDITY),
            any_open=False,
            indoor_temp=26,
            outdoor_temp=18,
            indoor_rh=70,
            projected_rh=75,
        )

        self.assertEqual(advices.temperature, Advice.OPEN)
        self.assertEqual(advices.humidity, Advice.KEEP_CLOSED)
        self.assertEqual(advices.overall, Advice.KEEP_CLOSED)

    def test_advises_open_without_contact_state_when_cooling_helps(self) -> None:
        advice = ventilation_advice(
            settings=ComfortSettings(19, 24, 40, 60, Priority.TEMPERATURE),
            any_open=None,
            indoor_temp=26,
            outdoor_temp=18,
            indoor_rh=None,
            projected_rh=None,
        )

        self.assertEqual(advice, Advice.OPEN)

    def test_advises_close_without_contact_state_when_temperature_does_not_help(
        self,
    ) -> None:
        advice = ventilation_advice(
            settings=ComfortSettings(19, 24, 40, 60, Priority.TEMPERATURE),
            any_open=None,
            indoor_temp=22,
            outdoor_temp=18,
            indoor_rh=None,
            projected_rh=None,
        )

        self.assertEqual(advice, Advice.CLOSE)

    def test_known_open_contact_changes_open_to_keep_open(self) -> None:
        advice = ventilation_advice(
            settings=ComfortSettings(19, 24, 40, 60, Priority.TEMPERATURE),
            any_open=True,
            indoor_temp=26,
            outdoor_temp=18,
            indoor_rh=None,
            projected_rh=None,
        )

        self.assertEqual(advice, Advice.KEEP_OPEN)

    def test_known_closed_contact_changes_close_to_keep_closed(self) -> None:
        advice = ventilation_advice(
            settings=ComfortSettings(19, 24, 40, 60, Priority.TEMPERATURE),
            any_open=False,
            indoor_temp=22,
            outdoor_temp=18,
            indoor_rh=None,
            projected_rh=None,
        )

        self.assertEqual(advice, Advice.KEEP_CLOSED)

    def test_temperature_priority_falls_back_to_humidity_when_temperature_missing(
        self,
    ) -> None:
        advice = ventilation_advice(
            settings=ComfortSettings(19, 24, 40, 60, Priority.TEMPERATURE),
            any_open=None,
            indoor_temp=None,
            outdoor_temp=None,
            indoor_rh=70,
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

    def test_humidity_priority_falls_back_to_temperature_when_humidity_missing(
        self,
    ) -> None:
        advice = ventilation_advice(
            settings=ComfortSettings(19, 24, 40, 60, Priority.HUMIDITY),
            any_open=None,
            indoor_temp=26,
            outdoor_temp=18,
            indoor_rh=None,
            projected_rh=None,
        )

        self.assertEqual(advice, Advice.OPEN)

    def test_advice_unavailable_when_no_temperature_or_humidity_advice_exists(
        self,
    ) -> None:
        advice = ventilation_advice(
            settings=ComfortSettings(19, 24, 40, 60, Priority.HUMIDITY),
            any_open=False,
            indoor_temp=None,
            outdoor_temp=None,
            indoor_rh=None,
            projected_rh=None,
        )

        self.assertIsNone(advice)


if __name__ == "__main__":
    unittest.main()
