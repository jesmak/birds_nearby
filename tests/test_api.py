"""eBird's API client: what its errors say."""

from __future__ import annotations

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.birds_nearby.api import EbirdClient
from custom_components.birds_nearby.const import EBIRD_URL
from custom_components.birds_nearby.exceptions import EbirdError


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (TimeoutError(), "eBird couldn't be reached: TimeoutError"),
        (aiohttp.ClientConnectionError("Connection refused"), "eBird couldn't be reached: Connection refused"),
    ],
)
async def test_an_error_without_a_message_is_named(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, error, message) -> None:
    aioclient_mock.get(f"{EBIRD_URL}/product/spplist/FI-02", exc=error)
    with pytest.raises(EbirdError) as raised:
        await EbirdClient(hass, "example-key").region_species("FI-02")
    assert str(raised.value) == message
