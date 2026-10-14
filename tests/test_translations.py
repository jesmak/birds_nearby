"""UI translations."""

from __future__ import annotations

import json
import re
from pathlib import Path

TRANSLATIONS = Path(__file__).parent.parent / "custom_components" / "birds_nearby" / "translations"


def flatten(tree: dict, prefix: str = "") -> dict[str, str]:
    result = {}
    for key, value in tree.items():
        if isinstance(value, dict):
            result |= flatten(value, f"{prefix}{key}.")
        else:
            result[f"{prefix}{key}"] = value
    return result


def test_finnish_has_the_same_texts_and_placeholders_as_english() -> None:
    english = flatten(json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8")))
    finnish = flatten(json.loads((TRANSLATIONS / "fi.json").read_text(encoding="utf-8")))
    assert finnish.keys() == english.keys()
    for key, text in english.items():
        assert re.findall(r"\{\w+\}", finnish[key]) == re.findall(r"\{\w+\}", text), key


def test_the_user_agent_names_the_released_version() -> None:
    import json
    from pathlib import Path

    from custom_components.birds_nearby.const import USER_AGENT

    manifest = json.loads(Path("custom_components/birds_nearby/manifest.json").read_text())
    assert USER_AGENT.startswith(f"BirdsNearby/{manifest['version']} ")
