from __future__ import annotations

import json
import pathlib
import re
import unittest
from typing import Any

ROOT = pathlib.Path(__file__).parents[1] / "custom_components" / "ventilation_assistant"
TRANSLATIONS = ROOT / "translations"


def _load_translation(language: str) -> dict[str, Any]:
    with (TRANSLATIONS / f"{language}.json").open(encoding="utf-8") as file:
        return json.load(file)


def _leaf_paths(value: object, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    if not isinstance(value, dict):
        return {prefix}

    paths: set[tuple[str, ...]] = set()
    for key, child in value.items():
        assert isinstance(key, str)
        paths.update(_leaf_paths(child, (*prefix, key)))
    return paths


def _translation_keys(filename: str) -> set[str]:
    source = (ROOT / filename).read_text(encoding="utf-8")
    return set(re.findall(r'translation_key\s*=\s*"([^"]+)"', source))


class TranslationTests(unittest.TestCase):
    def test_german_translation_has_same_leaf_keys_as_english(self) -> None:
        self.assertEqual(
            _leaf_paths(_load_translation("en")),
            _leaf_paths(_load_translation("de")),
        )

    def test_all_entity_translation_keys_have_names(self) -> None:
        platforms = {
            "sensor": _translation_keys("sensor.py"),
            "number": _translation_keys("number.py"),
            "binary_sensor": _translation_keys("binary_sensor.py"),
            "select": _translation_keys("select.py"),
        }

        for language in ("en", "de"):
            entities = _load_translation(language)["entity"]
            for platform, keys in platforms.items():
                with self.subTest(language=language, platform=platform):
                    self.assertEqual(keys, set(entities[platform]))
                    for key in keys:
                        self.assertIsInstance(entities[platform][key]["name"], str)
                        self.assertTrue(entities[platform][key]["name"])


if __name__ == "__main__":
    unittest.main()
