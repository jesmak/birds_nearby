"""Adding an area, a refused key, a new key, and the options."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.birds_nearby.const import (
    CONF_API_KEY,
    CONF_BACK_DAYS,
    CONF_LOCATION,
    CONF_RADIUS_KM,
    CONF_RECENT_DAYS,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    EBIRD_URL,
)

from .conftest import API_KEY, HOTSPOTS, LATITUDE, LONGITUDE, REGION, birds_entry

AREA = {"latitude": LATITUDE, "longitude": LONGITUDE, "radius": 20000}

# Keeps the reload after a reconfigure from polling, so the calls counted are the flow's own.
NO_SETUP = patch("custom_components.birds_nearby.async_setup_entry", return_value=True)


async def start(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["step_id"] == "user"
    return result


async def test_adding_an_area_checks_the_key_and_picks_the_region(hass: HomeAssistant, ebird: AiohttpClientMocker) -> None:
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Garden birds", CONF_API_KEY: API_KEY, CONF_LOCATION: AREA}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Garden birds"
    assert result["data"] == {CONF_API_KEY: API_KEY, "latitude": LATITUDE, "longitude": LONGITUDE, CONF_RADIUS_KM: 20}
    # The nearest hotspot's region, not the first one listed.
    assert result["options"][CONF_REGION] == REGION
    # The location is rounded before it is sent.
    hotspot_call = next(call for call in ebird.mock_calls if "hotspot" in str(call[1]))
    assert hotspot_call[1].query["lat"] == "60.98"
    assert hotspot_call[3]["x-ebirdapitoken"] == API_KEY


async def test_a_hotspot_without_coordinates_is_passed_over(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    hotspots = [{**HOTSPOTS[1], "subnational1Code": "FI-97", "lat": None}, *HOTSPOTS]
    aioclient_mock.get(f"{EBIRD_URL}/ref/hotspot/geo", json=hotspots)

    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Birds Nearby", CONF_API_KEY: API_KEY, CONF_LOCATION: AREA}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_REGION] == REGION


async def test_a_refused_key(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{EBIRD_URL}/ref/hotspot/geo", status=403)

    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Birds Nearby", CONF_API_KEY: "wrong", CONF_LOCATION: AREA}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_a_radius_beyond_ebirds_limit(hass: HomeAssistant, ebird: AiohttpClientMocker) -> None:
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Birds Nearby", CONF_API_KEY: API_KEY, CONF_LOCATION: {**AREA, "radius": 80000}}
    )

    assert result["errors"] == {CONF_LOCATION: "radius_out_of_range"}
    assert ebird.call_count == 0


async def test_the_same_area_twice(hass: HomeAssistant, ebird: AiohttpClientMocker) -> None:
    birds_entry(hass)
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Birds Nearby", CONF_API_KEY: API_KEY, CONF_LOCATION: AREA}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_a_new_key_after_ebird_refuses_the_old_one(hass: HomeAssistant, ebird: AiohttpClientMocker) -> None:
    entry = birds_entry(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "new-key-0002"})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == "new-key-0002"


async def test_options(hass: HomeAssistant, ebird: AiohttpClientMocker) -> None:
    entry = birds_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 30, CONF_RECENT_DAYS: 3, CONF_BACK_DAYS: 60, CONF_REGION: "nope!"}
    )
    assert result["errors"] == {CONF_REGION: "invalid_region"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 30, CONF_RECENT_DAYS: 3, CONF_BACK_DAYS: 60, CONF_REGION: " us-ny-109 "}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_SCAN_INTERVAL: 30, CONF_RECENT_DAYS: 3, CONF_BACK_DAYS: 60, CONF_REGION: "US-NY-109"}


async def test_a_new_radius_keeps_the_region_without_asking_ebird(hass: HomeAssistant, ebird: AiohttpClientMocker) -> None:
    entry = birds_entry(hass, region="US-NY-109")
    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_LOCATION: {**AREA, "radius": 80000}})
    assert result["errors"] == {CONF_LOCATION: "radius_out_of_range"}

    with NO_SETUP:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_LOCATION: {**AREA, "radius": 40000}})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert ebird.call_count == 0

    assert entry.data == {CONF_API_KEY: API_KEY, "latitude": LATITUDE, "longitude": LONGITUDE, CONF_RADIUS_KM: 40}
    assert entry.options[CONF_REGION] == "US-NY-109"


async def test_a_moved_centre_picks_its_region_again(hass: HomeAssistant, ebird: AiohttpClientMocker) -> None:
    entry = birds_entry(hass, region="US-NY-109")
    result = await entry.start_reconfigure_flow(hass)
    with NO_SETUP:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_LOCATION: {"latitude": 61.0, "longitude": 25.7, "radius": 25000}}
        )
        await hass.async_block_till_done()
    assert ebird.call_count == 1

    assert result["reason"] == "reconfigure_successful"
    assert (entry.data["latitude"], entry.data["longitude"], entry.unique_id) == (61.0, 25.7, "61.00_25.70")
    assert entry.options == {CONF_SCAN_INTERVAL: 60, CONF_RECENT_DAYS: 7, CONF_BACK_DAYS: 30, CONF_REGION: REGION}


async def test_an_area_cant_move_onto_another(hass: HomeAssistant, ebird: AiohttpClientMocker) -> None:
    birds_entry(hass)
    other = birds_entry(hass, area=1)
    result = await other.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_LOCATION: AREA})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert other.unique_id == "area1"


async def test_a_refused_key_while_moving_the_centre_changes_nothing(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{EBIRD_URL}/ref/hotspot/geo", status=403)
    entry = birds_entry(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_LOCATION: {"latitude": 61.0, "longitude": 25.7, "radius": 40000}}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert entry.data == {CONF_API_KEY: API_KEY, "latitude": LATITUDE, "longitude": LONGITUDE, CONF_RADIUS_KM: 25}
    assert (entry.unique_id, entry.options[CONF_REGION]) == (f"{LATITUDE:.2f}_{LONGITUDE:.2f}", REGION)
