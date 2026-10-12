"""Adding an area, a refused key, a new key, and the options."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

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

from .conftest import API_KEY, LATITUDE, LONGITUDE, REGION, birds_entry

AREA = {"latitude": LATITUDE, "longitude": LONGITUDE, "radius": 20000}


async def start(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["step_id"] == "user"
    return result


async def test_adding_an_area_checks_the_key_and_picks_the_region(
    enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker
) -> None:
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


async def test_a_refused_key(
    enable_custom_integrations, hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{EBIRD_URL}/ref/hotspot/geo", status=403)

    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Birds Nearby", CONF_API_KEY: "wrong", CONF_LOCATION: AREA}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_a_radius_beyond_ebirds_limit(
    enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker
) -> None:
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Birds Nearby", CONF_API_KEY: API_KEY, CONF_LOCATION: {**AREA, "radius": 80000}}
    )

    assert result["errors"] == {CONF_LOCATION: "radius_out_of_range"}
    assert ebird.call_count == 0


async def test_the_same_area_twice(enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker) -> None:
    birds_entry(hass)
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Birds Nearby", CONF_API_KEY: API_KEY, CONF_LOCATION: AREA}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_a_new_key_after_ebird_refuses_the_old_one(
    enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker
) -> None:
    entry = birds_entry(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "new-key-0002"})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == "new-key-0002"


async def test_options(enable_custom_integrations, hass: HomeAssistant, ebird: AiohttpClientMocker) -> None:
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
