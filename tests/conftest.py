"""Shared fixtures: eBird and Wikimedia answers, made up but shaped like the real ones."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.birds_nearby.const import (
    CONF_API_KEY,
    CONF_BACK_DAYS,
    CONF_RADIUS_KM,
    CONF_RECENT_DAYS,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    EBIRD_URL,
)
from custom_components.birds_nearby.pictures import COMMONS_API, WIKIDATA_API, WIKIPEDIA_API

LATITUDE = 60.98
LONGITUDE = 25.66
REGION = "FI-99"
API_KEY = "test-key-0001"


def observation(
    species: str = "eurbla",
    name: str = "Eurasian Blackbird",
    observed: str = "2026-10-10 08:15",
    checklist: str = "S900001",
    location: str = "L900001",
    location_name: str = "Example Bay",
    personal: bool = False,
    count: int | None = 2,
    latitude: float = 60.9811,
    longitude: float = 25.6623,
    reviewed: bool = False,
    scientific: str = "Turdus merula",
) -> dict[str, Any]:
    """One observation as eBird sends it at simple detail."""
    result = {
        "speciesCode": species,
        "comName": name,
        "sciName": scientific,
        "locId": location,
        "locName": location_name,
        "obsDt": observed,
        "lat": latitude,
        "lng": longitude,
        "obsValid": True,
        "obsReviewed": reviewed,
        "locationPrivate": personal,
        "subId": checklist,
    }
    if count is not None:
        result["howMany"] = count
    return result


RECENT = [
    observation(),
    observation(
        species="hoocro1",
        name="Hooded Crow",
        scientific="Corvus cornix",
        observed="2026-10-09 17:40",
        checklist="S900002",
        location="L900002",
        location_name="Backyard, Example Street 1",
        personal=True,
        count=5,
        latitude=60.9702,
        longitude=25.6411,
    ),
]

HOTSPOTS = [
    {
        "locId": "L900010",
        "locName": "Far Marsh",
        "countryCode": "FI",
        "subnational1Code": "FI-98",
        "lat": 61.30,
        "lng": 25.90,
    },
    {
        "locId": "L900001",
        "locName": "Example Bay",
        "countryCode": "FI",
        "subnational1Code": REGION,
        "lat": 60.9811,
        "lng": 25.6623,
    },
]

REGION_SPECIES = ["eurbla", "hoocro1", "gretit1"]


def answer(
    aioclient_mock: AiohttpClientMocker,
    recent: list[dict[str, Any]] = RECENT,
    notable: list[dict[str, Any]] | None = None,
) -> None:
    """eBird's answers, and Wikimedia knowing none of the species."""
    aioclient_mock.get(f"{EBIRD_URL}/ref/hotspot/geo", json=HOTSPOTS)
    aioclient_mock.get(f"{EBIRD_URL}/data/obs/geo/recent/notable", json=notable or [])
    aioclient_mock.get(f"{EBIRD_URL}/data/obs/geo/recent", json=recent)
    aioclient_mock.get(f"{EBIRD_URL}/product/spplist/{REGION}", json=REGION_SPECIES)
    aioclient_mock.get(WIKIDATA_API, json={"query": {"search": []}})
    aioclient_mock.get(WIKIPEDIA_API, json={})
    aioclient_mock.get(COMMONS_API, json={})


@pytest.fixture
def ebird(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """eBird, with two recent species, nothing notable, and a region where both are known."""
    answer(aioclient_mock)
    return aioclient_mock


def birds_entry(hass: HomeAssistant, **options: Any) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Birds Nearby",
        version=1,
        minor_version=1,
        unique_id=f"{LATITUDE:.2f}_{LONGITUDE:.2f}",
        data={CONF_API_KEY: API_KEY, "latitude": LATITUDE, "longitude": LONGITUDE, CONF_RADIUS_KM: 25},
        options={CONF_SCAN_INTERVAL: 60, CONF_RECENT_DAYS: 7, CONF_BACK_DAYS: 30, CONF_REGION: REGION, **options},
    )
    entry.add_to_hass(hass)
    return entry
