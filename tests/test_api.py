"""eBird's API client: what its errors say, and what its taxonomy means."""

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


@pytest.mark.parametrize(
    ("taxon", "counts_as"),
    [
        ({"speciesCode": "whcspa", "sciName": "Zonotrichia leucophrys", "category": "species"}, "whcspa"),
        ({"speciesCode": "gwcspa", "sciName": "Zonotrichia leucophrys", "category": "issf", "reportAs": "whcspa"}, "whcspa"),
        ({"speciesCode": "x00450", "sciName": "Ammospiza nelsoni x caudacuta", "category": "hybrid"}, ""),
        ({"speciesCode": "gull1", "sciName": "Larinae sp.", "category": "spuh"}, ""),
        ({"speciesCode": "y00679", "sciName": "Larus argentatus/smithsonianus", "category": "slash"}, ""),
        ({"speciesCode": "whiwag1", "sciName": "Motacilla alba alba/dukhunensis", "category": "issf", "reportAs": "whiwag"}, "whiwag"),
        ({"speciesCode": "comred", "sciName": "Acanthis flammea flammea/rostrata", "category": "form", "reportAs": "redpol1"}, "redpol1"),
        (
            {
                "speciesCode": "daejun3",
                "sciName": "Junco hyemalis [oreganus Group] x mearnsi",
                "category": "intergrade",
                "reportAs": "daejun",
            },
            "daejun",
        ),
    ],
    ids=["species", "subspecies group", "hybrid", "spuh", "slash", "slashed group", "form", "intergrade"],
)
async def test_what_a_code_counts_as(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, taxon, counts_as) -> None:
    aioclient_mock.get(f"{EBIRD_URL}/ref/taxonomy/ebird", json=[{**taxon, "comName": "Example Bird"}])
    taxa = await EbirdClient(hass, "example-key").taxonomy([taxon["speciesCode"]], "fi")
    assert taxa[taxon["speciesCode"]].counts_as == counts_as
    assert aioclient_mock.mock_calls[0][1].query["locale"] == "fi"
