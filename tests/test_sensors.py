"""The sensors, the events and the memory across restarts, with eBird mocked."""

from __future__ import annotations

from datetime import datetime

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_capture_events, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.birds_nearby.const import EBIRD_URL, EVENT_FIRST_IN_REGION, EVENT_FIRST_OF_YEAR, EVENT_NOTABLE
from custom_components.birds_nearby.pictures import Picture, SpeciesInfo
from custom_components.birds_nearby.sightings import Memory

from .conftest import RECENT, REGION, answer, birds_entry, observation

NOW = datetime(2026, 10, 12, 12, 0)

RARITY = observation(
    species="palhar1",
    name="Pallid Harrier",
    scientific="Circus macrourus",
    observed="2026-10-12 10:30",
    checklist="S900100",
    count=1,
    reviewed=True,
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
    freezer: FrozenDateTimeFactory,
) -> None:
    entry = await set_up(hass)
    notable_events = async_capture_events(hass, EVENT_NOTABLE)
    first_events = async_capture_events(hass, EVENT_FIRST_OF_YEAR)
    region_events = async_capture_events(hass, EVENT_FIRST_IN_REGION)

    ebird.clear_requests()
    answer(ebird, recent=[*RECENT, RARITY], notable=[RARITY])
    freezer.tick(3600)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert len(notable_events) == 1
    data = notable_events[0].data
    assert data["species_code"] == "palhar1"
    assert data["name"] == "Pallid Harrier"
    assert data["count"] == 1
    assert data["location"] == "Example Bay"
    assert data["reviewed"] is True
    assert data["notable"] is True
    # Where it was, for automations that care only about what is close.
    assert (data["distance_km"], data["bearing"], data["direction"]) == (0.2, 45, "northeast")
    assert data["iucn_status"] is None, "Wikimedia knows none of the test species"
    assert [event.data["species_code"] for event in first_events] == ["palhar1"]
    # The first year has no last year to compare with.
    assert (first_events[0].data["last_year"], first_events[0].data["days_vs_last_year"]) == (None, None)
    assert [event.data["region"] for event in region_events] == [REGION]

    assert hass.states.get("sensor.birds_nearby_notable").state == "1"
    year_list = hass.states.get("sensor.birds_nearby_year_list")
    assert year_list.state == "3"
    assert year_list.attributes["last_year_since"] is None
    assert year_list.attributes["expected"] == []
    assert year_list.attributes["species"][0] == {
        "species_code": "palhar1",
        "name": "Pallid Harrier",
        "first_seen": NOW.date(),
        "last_year": None,
    }
    assert [item["first_seen"] for item in year_list.attributes["species"][1:]] == [None, None], "seen before the installation"
    # The region's list is fetched once a day, not on every poll.
    assert not any("spplist" in str(call[1]) for call in ebird.mock_calls)


async def test_a_rarity_on_many_checklists_is_listed_once(
    enable_custom_integrations, hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    reports = [{**RARITY, "subId": f"S90011{n}", "obsDt": f"2026-10-1{n} 09:00"} for n in range(3)]
    answer(aioclient_mock, recent=[*RECENT, RARITY], notable=reports)
    await set_up(hass)

    notable = hass.states.get("sensor.birds_nearby_notable")
    assert notable.state == "1"
    [sighting] = notable.attributes["sightings"]
    assert (sighting["species_code"], sighting["observed"], sighting["reports"]) == ("palhar1", "2026-10-12T09:00", 3)


async def test_the_memory_survives_a_restart(enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker) -> None:
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

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.birds_nearby_recent").state == "unavailable"
    assert [flow["context"]["source"] for flow in hass.config_entries.flow.async_progress()] == ["reauth"]


async def test_a_failing_region_list_is_tried_once_a_day(
    enable_custom_integrations, hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    aioclient_mock.get(f"{EBIRD_URL}/product/spplist/{REGION}", status=500)
    answer(aioclient_mock)
    entry = await set_up(hass)

    freezer.tick(3600)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    # Not after a reload either, such as saving the options.
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data.last_update_success, "the sightings are still updated"
    assert sum("spplist" in str(call[1]) for call in aioclient_mock.mock_calls) == 1


async def test_ebird_down_at_startup_is_not_retried_within_seconds(
    enable_custom_integrations, hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    aioclient_mock.get(f"{EBIRD_URL}/product/spplist/{REGION}", status=429)
    aioclient_mock.get(f"{EBIRD_URL}/data/obs/geo/recent", status=429)
    entry = birds_entry(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    freezer.tick(600)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.birds_nearby_recent").state == "unavailable"
    assert sum(str(call[1]).startswith(EBIRD_URL) for call in aioclient_mock.mock_calls) == 2, "one try, no setup retries"


async def test_a_refresh_by_hand_doesnt_poll_ebird_more_often_than_every_15_minutes(
    enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    assert await async_setup_component(hass, "homeassistant", {})
    await set_up(hass)
    ebird.clear_requests()
    answer(ebird)

    for _ in range(3):
        freezer.tick(60)
        await hass.services.async_call("homeassistant", "update_entity", {"entity_id": "sensor.birds_nearby_recent"}, blocking=True)
        await hass.async_block_till_done()
    assert not any(str(call[1]).startswith(EBIRD_URL) for call in ebird.mock_calls)

    freezer.tick(15 * 60)
    await hass.services.async_call("homeassistant", "update_entity", {"entity_id": "sensor.birds_nearby_recent"}, blocking=True)
    await hass.async_block_till_done()
    assert sum("geo/recent" in str(call[1]) for call in ebird.mock_calls) == 2, "recent and notable, once"


async def test_an_update_a_moment_early_at_the_shortest_interval_still_polls(
    enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    entry = await set_up(hass, scan_interval=15)
    ebird.clear_requests()
    answer(ebird)

    freezer.tick(15 * 60 - 1)
    await entry.runtime_data.async_refresh()

    assert sum("geo/recent" in str(call[1]) for call in ebird.mock_calls) == 2


async def test_a_reload_right_after_a_poll_keeps_its_memory(
    enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    entry = await set_up(hass)
    events = async_capture_events(hass, EVENT_FIRST_OF_YEAR)
    ebird.clear_requests()
    answer(ebird, recent=[*RECENT, RARITY], notable=[RARITY])
    freezer.tick(3600)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    # Within the delayed save's ten seconds.
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert [event.data["species_code"] for event in events] == ["palhar1"], "not fired again after the reload"
    assert hass.states.get("sensor.birds_nearby_year_list").state == "3"


async def test_an_unexpected_observation_fails_the_update_cleanly(
    enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    entry = await set_up(hass)
    broken = observation()
    del broken["obsDt"]
    ebird.clear_requests()
    answer(ebird, recent=[broken])
    freezer.tick(3600)
    await entry.runtime_data.async_refresh()

    assert not entry.runtime_data.last_update_success
    assert "unexpected format" in str(entry.runtime_data.last_exception)


async def test_a_memory_from_1_2_forgets_its_backfill_and_looks_up_its_taxonomy(
    enable_custom_integrations, hass: HomeAssistant, hass_storage, ebird: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    # Installed on the evening of 1 October, already 2 October in UTC. The first poll dated each species by its newest
    # sighting, and kept a hybrid.
    freezer.move_to(datetime(2026, 10, 1, 20, 0, tzinfo=dt_util.get_default_time_zone()))
    entry = birds_entry(hass)
    freezer.move_to(NOW.replace(tzinfo=dt_util.get_default_time_zone()))
    memory = Memory.new(datetime(2026, 10, 1).date())
    memory.year_list = {
        "eurbla": "2026-09-28",
        "comswi": "2026-10-02",
        "gwcspa": "2026-10-03",
        "x01134": "2026-10-06",
        "oldcod1": "2026-10-01",
    }
    memory.scientific = {"eurbla": "Turdus merula", "x01134": "Larus smithsonianus x fuscus"}
    memory.initialized = True
    stored = memory.as_dict()
    del stored["counts_as"]
    hass_storage[f"birds_nearby.{entry.entry_id}"] = {"version": 1, "key": f"birds_nearby.{entry.entry_id}", "data": {"memory": stored}}
    ebird.clear_requests()
    ebird.get(
        f"{EBIRD_URL}/ref/taxonomy/ebird",
        json=[
            {"speciesCode": "comswi", "sciName": "Apus apus", "comName": "Tervapääsky", "category": "species"},
            {"speciesCode": "x01134", "sciName": "Larus smithsonianus x fuscus", "comName": "Example Hybrid", "category": "hybrid"},
            {
                "speciesCode": "gwcspa",
                "sciName": "Zonotrichia leucophrys gambelii",
                "comName": "Juovapääsirkku (gambelii)",
                "category": "issf",
                "reportAs": "whcspa",
            },
        ],
    )
    answer(ebird)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    calls = [call[1].path.removeprefix("/v2/") for call in ebird.mock_calls if str(call[1]).startswith(EBIRD_URL)]
    assert sorted(calls) == ["data/obs/geo/recent", "data/obs/geo/recent/notable", "ref/taxonomy/ebird"], "still one extra call"
    taxonomy = next(call for call in ebird.mock_calls if call[1].path.endswith("taxonomy/ebird"))
    assert taxonomy[1].query["species"] == "comswi,eurbla,gwcspa,oldcod1,x01134"
    memory = entry.runtime_data.memory
    # Up to the day of installation no date, the hybrid off the list, and the subspecies group as its species. The poll
    # brought a species the memory didn't have.
    assert memory.year_list == {"eurbla": "", "comswi": "2026-10-02", "whcspa": "2026-10-03", "oldcod1": "", "hoocro1": "2026-10-09"}
    assert memory.names["comswi"] == "Tervapääsky"
    # A code eBird no longer knows stays as it is, and isn't asked for again.
    assert memory.counts_as["oldcod1"] == "oldcod1"
    assert memory.unknown() == ["hoocro1", "whcspa"], "the new species, and the group's species for its name"

    species = hass.states.get("sensor.birds_nearby_year_list").attributes["species"]
    assert [(item["species_code"], item["first_seen"]) for item in species] == [
        ("hoocro1", datetime(2026, 10, 9).date()),
        ("whcspa", datetime(2026, 10, 3).date()),
        ("comswi", datetime(2026, 10, 2).date()),
        ("eurbla", None),
        ("oldcod1", None),
    ]


async def test_an_event_carries_its_species_picture(
    enable_custom_integrations,
    hass: HomeAssistant,
    ebird: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def found(session, species, scientific):
        return SpeciesInfo(Picture("https://upload.wikimedia.org/harrier.jpg", "", "A. Author", "CC BY 4.0"), "LC")

    entry = await set_up(hass)
    monkeypatch.setattr("custom_components.birds_nearby.coordinator.find_species", found)
    events = async_capture_events(hass, EVENT_NOTABLE)
    ebird.clear_requests()
    answer(ebird, recent=[*RECENT, RARITY], notable=[RARITY])
    freezer.tick(3600)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert events[0].data["picture"] == "https://upload.wikimedia.org/harrier.jpg"
    assert events[0].data["iucn_status"] == "LC"


async def test_the_taxonomy_is_asked_every_other_day_at_most(
    enable_custom_integrations, hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    # eBird keeps failing to answer for the taxonomy: the region's list still comes every other day.
    aioclient_mock.get(f"{EBIRD_URL}/ref/taxonomy/ebird", status=500)
    answer(aioclient_mock)
    entry = birds_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = entry.runtime_data

    calls = []
    for _ in range(4):
        coordinator.memory.year_list["oldcod1"] = "2026-03-01"
        coordinator.memory.counts_as.pop("oldcod1", None)
        aioclient_mock.clear_requests()
        answer(aioclient_mock)
        aioclient_mock.get(f"{EBIRD_URL}/ref/taxonomy/ebird", status=500)
        freezer.tick(24 * 3600)
        await coordinator.async_refresh()
        extra = [call[1].path for call in aioclient_mock.mock_calls if "taxonomy" in str(call[1]) or "spplist" in str(call[1])]
        calls.append([path.rsplit("/", 2)[-2] for path in extra])

    assert calls == [["taxonomy"], ["spplist"], ["taxonomy"], ["spplist"]], "one extra call a day, and never two days of taxonomy"
