"""The sensors, the events and the memory across restarts, with eBird mocked."""

from __future__ import annotations

from datetime import datetime

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_capture_events
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.birds_nearby.const import EBIRD_URL, EVENT_FIRST_IN_REGION, EVENT_FIRST_OF_YEAR, EVENT_NOTABLE

from .conftest import RECENT, REGION, answer, birds_entry, observation

NOW = datetime(2026, 10, 12, 12, 0)

RARITY = observation(
    species="palhar1",
    name="Pallid Harrier",
    scientific="Circus macrourus",
    observed="2026-10-12 10:30",
    checklist="S900100",
    count=1,
)


@pytest.fixture(autouse=True)
def frozen(freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(NOW.replace(tzinfo=dt_util.get_default_time_zone()))


async def set_up(hass: HomeAssistant, **options):
    entry = birds_entry(hass, **options)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_the_first_poll_fills_the_sensors_without_events(
    enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker
) -> None:
    events = async_capture_events(hass, EVENT_FIRST_OF_YEAR)
    await set_up(hass)

    assert events == []
    assert hass.states.get("sensor.birds_nearby_year_list").state == "2"
    recent = hass.states.get("sensor.birds_nearby_recent")
    assert recent.state == "2"
    assert [item["species_code"] for item in recent.attributes["species"]] == ["eurbla", "hoocro1"]
    crow = recent.attributes["species"][1]
    assert crow["location"] is None, "a personal location's name is never shown"
    assert crow["hotspot"] is False
    assert hass.states.get("sensor.birds_nearby_notable").state == "0"

    feed = hass.states.get("sensor.birds_nearby_sighting_places")
    assert feed.state == "2"
    assert feed.attributes["map_feed_version"] == 1
    assert feed.attributes["area"] == {"center": [60.98, 25.66], "radius_km": 25}
    assert "eBird" in feed.attributes["attribution"]


async def test_the_calls_to_ebird(enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker) -> None:
    await set_up(hass)

    ebird_calls = [call for call in ebird.mock_calls if str(call[1]).startswith(EBIRD_URL)]
    paths = sorted(call[1].path.removeprefix("/v2/") for call in ebird_calls)
    # Two per poll, and the region's species list once a day.
    assert paths == ["data/obs/geo/recent", "data/obs/geo/recent/notable", f"product/spplist/{REGION}"]
    notable = next(call for call in ebird_calls if call[1].path.endswith("notable"))
    assert notable[1].query["detail"] == "simple"
    assert notable[1].query["back"] == "30"


async def test_a_rarity_on_the_next_poll(
    enable_custom_integrations,
    hass: HomeAssistant,
    ebird: AiohttpClientMocker,
) -> None:
    entry = await set_up(hass)
    notable_events = async_capture_events(hass, EVENT_NOTABLE)
    first_events = async_capture_events(hass, EVENT_FIRST_OF_YEAR)
    region_events = async_capture_events(hass, EVENT_FIRST_IN_REGION)

    ebird.clear_requests()
    answer(ebird, recent=[*RECENT, RARITY], notable=[RARITY])
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert len(notable_events) == 1
    data = notable_events[0].data
    assert data["species_code"] == "palhar1"
    assert data["name"] == "Pallid Harrier"
    assert data["count"] == 1
    assert data["location"] == "Example Bay"
    assert data["reviewed"] is False
    assert [event.data["species_code"] for event in first_events] == ["palhar1"]
    assert [event.data["region"] for event in region_events] == [REGION]

    assert hass.states.get("sensor.birds_nearby_notable").state == "1"
    assert hass.states.get("sensor.birds_nearby_year_list").state == "3"
    # The region's list is fetched once a day, not on every poll.
    assert not any("spplist" in str(call[1]) for call in ebird.mock_calls)


async def test_the_memory_survives_a_restart(
    enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker
) -> None:
    entry = await set_up(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    events = async_capture_events(hass, EVENT_FIRST_OF_YEAR)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert events == [], "the species seen before the restart aren't new after it"
    assert hass.states.get("sensor.birds_nearby_year_list").state == "2"


async def test_a_refused_key_asks_for_a_new_one(
    enable_custom_integrations, hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{EBIRD_URL}/product/spplist/{REGION}", status=403)
    entry = birds_entry(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert [flow["context"]["source"] for flow in hass.config_entries.flow.async_progress()] == ["reauth"]


async def test_a_failing_region_list_is_tried_once_a_day(
    enable_custom_integrations, hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{EBIRD_URL}/product/spplist/{REGION}", status=500)
    answer(aioclient_mock)
    entry = await set_up(hass)

    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert entry.runtime_data.last_update_success, "the sightings are still updated"
    assert sum("spplist" in str(call[1]) for call in aioclient_mock.mock_calls) == 1
