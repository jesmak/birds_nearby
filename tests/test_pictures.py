"""Finding a species' picture through Wikidata, Wikipedia and Commons."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.birds_nearby.pictures import (
    COMMONS_API,
    WIKIDATA_API,
    WIKIPEDIA_API,
    find_picture,
    plain_text,
)

IMAGEINFO = {
    "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Example_bird.jpg/960px-Example_bird.jpg?utm_source=commons.wikimedia.org",
    "url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Example_bird.jpg",
    "descriptionurl": "https://commons.wikimedia.org/wiki/File:Example_bird.jpg",
    "extmetadata": {
        "Artist": {"value": '<a href="//commons.wikimedia.org/wiki/User:Example">Matti Meikäläinen</a> &amp; friend'},
        "LicenseShortName": {"value": "CC BY-SA 4.0"},
    },
}


def wikimedia(aioclient_mock: AiohttpClientMocker, on_commons: bool = True) -> None:
    aioclient_mock.get(
        WIKIDATA_API,
        params={"action": "wbgetentities"},
        # The first item, the species under its new genus name, has no article yet.
        json={
            "entities": {"Q900002": {"sitelinks": {}}, "Q900001": {"sitelinks": {"enwiki": {"title": "Example bird"}}}}
        },
    )
    aioclient_mock.get(WIKIDATA_API, json={"query": {"search": [{"title": "Q900002"}, {"title": "Q900001"}]}})
    aioclient_mock.get(
        WIKIPEDIA_API, json={"query": {"pages": [{"title": "Example bird", "pageimage": "Example_bird.jpg"}]}}
    )
    page = (
        {"title": "File:Example_bird.jpg", "imageinfo": [IMAGEINFO]}
        if on_commons
        else {"title": "File:Example_bird.jpg", "missing": True}
    )
    aioclient_mock.get(COMMONS_API, json={"query": {"pages": [page]}})


async def test_the_lead_image_with_its_author_and_licence(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    wikimedia(aioclient_mock)

    picture = await find_picture(async_get_clientsession(hass), "exabir1", "Avis exempli")

    assert picture is not None
    assert (
        picture.url
        == "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Example_bird.jpg/960px-Example_bird.jpg"
    )
    assert picture.page == "https://commons.wikimedia.org/wiki/File:Example_bird.jpg"
    assert picture.credit == "Matti Meikäläinen & friend, CC BY-SA 4.0"


async def test_a_file_that_is_not_on_commons_is_not_used(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    wikimedia(aioclient_mock, on_commons=False)
    assert await find_picture(async_get_clientsession(hass), "exabir1", "Avis exempli") is None


async def test_a_species_wikidata_does_not_know(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(WIKIDATA_API, json={"query": {"search": []}})
    assert await find_picture(async_get_clientsession(hass), "exabir1", "Avis exempli") is None
    # Looked up by its eBird code and then by its scientific name.
    assert aioclient_mock.call_count == 2


def test_plain_text() -> None:
    assert plain_text('<span class="x">Jane <b>Doe</b></span>\n') == "Jane Doe"
