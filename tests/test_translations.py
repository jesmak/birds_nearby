"""UI translations."""

from __future__ import annotations

import json
import re
from pathlib import Path

from custom_components.birds_nearby.const import USER_AGENT
from custom_components.birds_nearby.feed import DIRECTIONS, TEXTS

COMPONENT = Path(__file__).parent.parent / "custom_components" / "birds_nearby"
TRANSLATIONS = COMPONENT / "translations"


def flatten(tree: dict, prefix: str = "") -> dict[str, str]:
    result = {}
    for key, value in tree.items():
        if isinstance(value, dict):
            result |= flatten(value, f"{prefix}{key}.")
        else:
            result[f"{prefix}{key}"] = value
    return result


def placeholders(text: str) -> list[str]:
    return re.findall(r"\{\w+\}", text)


def test_finnish_has_the_same_texts_and_placeholders_as_english() -> None:
    english = flatten(json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8")))
    finnish = flatten(json.loads((TRANSLATIONS / "fi.json").read_text(encoding="utf-8")))
    assert finnish.keys() == english.keys()
    for key, text in english.items():
        assert placeholders(finnish[key]) == placeholders(text), key


def test_the_map_has_the_same_texts_and_placeholders_in_finnish() -> None:
    assert TEXTS["fi"].keys() == TEXTS["en"].keys()
    for key, text in TEXTS["en"].items():
        assert placeholders(TEXTS["fi"][key]) == placeholders(text), key
    assert [len(names) for names in DIRECTIONS.values()] == [8] * len(DIRECTIONS)


def test_the_user_agent_names_the_released_version() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    assert USER_AGENT.startswith(f"BirdsNearby/{manifest['version']} ")
