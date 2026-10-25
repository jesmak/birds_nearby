"""What Wikimedia knows of a species: its conservation status, and the lead image of its English Wikipedia
article with the picture's author and licence.

eBird species code → Wikidata item (P3444, or the scientific name in P225 when eBird renamed
the code and Wikidata hasn't caught up), with its IUCN status (P141) → its English Wikipedia article → the
article's lead image → that file's licence and author on Wikimedia Commons. A file that isn't on Commons isn't used.
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import USER_AGENT

_LOGGER = logging.getLogger(__name__)

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# One of Commons' standard thumbnail widths: it rounds any other up to the next one.
# Sharp enough in a map popup on a phone, and about a quarter of the file size of 960.
THUMB_WIDTH = 500

TIMEOUT = aiohttp.ClientTimeout(total=30)

# Wikidata's items for the IUCN Red List categories, as the categories' own abbreviations.
IUCN_STATUSES = {
    "Q211005": "LC",
    "Q719675": "NT",
    "Q278113": "VU",
    "Q11394": "EN",
    "Q219127": "CR",
    "Q239509": "EW",
    "Q237350": "EX",
    "Q3245245": "DD",
}


@dataclass(frozen=True)
class Picture:
    url: str
    # The file's page on Commons.
    page: str
    author: str
    licence: str

    @property
    def credit(self) -> str:
        return ", ".join(part for part in (self.author, self.licence) if part)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Picture:
        return cls(url=data["url"], page=data["page"], author=data["author"], licence=data["licence"])

    def as_dict(self) -> dict[str, str]:
        return {"url": self.url, "page": self.page, "author": self.author, "licence": self.licence}


@dataclass(frozen=True)
class SpeciesInfo:
    picture: Picture | None
    # The IUCN Red List category, such as "VU", or None when Wikidata has none.
    iucn: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpeciesInfo:
        picture = data.get("picture")
        return cls(picture=Picture.from_dict(picture) if picture else None, iucn=data.get("iucn"))

    def as_dict(self) -> dict[str, Any]:
        return {"picture": self.picture.as_dict() if self.picture else None, "iucn": self.iucn}


class WikimediaError(Exception):
    """Wikimedia couldn't be reached, or answered with something unexpected."""


async def find_species(session: aiohttp.ClientSession, species: str, scientific: str) -> SpeciesInfo:
    """What Wikimedia knows of the species. Nothing at all when Wikidata has no item with an article for it."""
    try:
        article = await _article(session, f"P3444={species}")
        if article is None and scientific:
            article = await _article(session, f'"P225={scientific}"')
        if article is None:
            return SpeciesInfo(picture=None, iucn=None)
        title, iucn = article
        return SpeciesInfo(picture=await _picture(session, title), iucn=iucn)
    except (AttributeError, KeyError, TypeError) as err:
        # The answers are read with .get() all the way down, which only holds while each level has the expected shape.
        raise WikimediaError(f"Wikimedia sent something unexpected for {species}: {err!r}") from err


async def _picture(session: aiohttp.ClientSession, title: str) -> Picture | None:
    """The article's lead image, or None when it has none that can be used."""
    pages = await _get(
        session,
        WIKIPEDIA_API,
        {"action": "query", "titles": title, "prop": "pageimages", "piprop": "name", "redirects": 1},
    )
    file_name = next((page.get("pageimage") for page in pages.get("query", {}).get("pages", [])), None)
    if not file_name:
        return None

    files = await _get(
        session,
        COMMONS_API,
        {
            "action": "query",
            "titles": f"File:{file_name}",
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": THUMB_WIDTH,
            "iiextmetadatafilter": "Artist|LicenseShortName",
        },
    )
    page = next(iter(files.get("query", {}).get("pages", [])), {})
    if page.get("missing") or not page.get("imageinfo"):
        # Not on Commons: a file uploaded to Wikipedia alone may not be freely licensed.
        return None
    return picture_from_imageinfo(page["imageinfo"][0])


def picture_from_imageinfo(info: dict[str, Any]) -> Picture | None:
    url = info.get("thumburl") or info.get("url")
    if not url or not url.startswith("https://"):
        return None
    metadata = info.get("extmetadata", {})
    return Picture(
        # Wikimedia adds tracking parameters to its thumbnail addresses; the file is the same without them.
        url=url.split("?", 1)[0],
        page=info.get("descriptionurl", ""),
        author=plain_text(metadata.get("Artist", {}).get("value", "")),
        licence=plain_text(metadata.get("LicenseShortName", {}).get("value", "")),
    )


def plain_text(value: str) -> str:
    """Commons gives the author as HTML, usually a link to their user page."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", value)).split())


async def _article(session: aiohttp.ClientSession, statement: str) -> tuple[str, str | None] | None:
    """The English Wikipedia article of the Wikidata items with this statement, and that item's IUCN status.

    A species can have several: when a genus is split, Wikidata often keeps the old name's
    item with the article and adds one for the new name without it. The first with an article wins.
    """
    result = await _get(
        session,
        WIKIDATA_API,
        {"action": "query", "list": "search", "srsearch": f"haswbstatement:{statement}", "srlimit": 5},
    )
    items = [hit["title"] for hit in result.get("query", {}).get("search", [])]
    if not items:
        return None
    entities = await _get(
        session,
        WIKIDATA_API,
        {"action": "wbgetentities", "ids": "|".join(items), "props": "sitelinks|claims", "sitefilter": "enwiki"},
    )
    for item in items:
        entity = entities.get("entities", {}).get(item, {})
        title = entity.get("sitelinks", {}).get("enwiki", {}).get("title")
        if title:
            return title, iucn_status(entity.get("claims", {}).get("P141", []))
    return None


def iucn_status(statements: list[dict[str, Any]]) -> str | None:
    """The current category. An item keeps older assessments too, the current one ranked preferred."""
    ranked = sorted(
        (statement for statement in statements if statement.get("rank") != "deprecated"),
        key=lambda statement: statement.get("rank") != "preferred",
    )
    for statement in ranked:
        value = statement.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if isinstance(value, dict) and value.get("id") in IUCN_STATUSES:
            return IUCN_STATUSES[value["id"]]
    return None


async def _get(session: aiohttp.ClientSession, url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        async with session.get(
            url,
            params={**params, "format": "json", "formatversion": 2},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        ) as response:
            if response.status != 200:
                raise WikimediaError(f"{url} answered with status {response.status}")
            payload = await response.json()
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        # A timeout's message is empty, so the type is the cause.
        raise WikimediaError(f"{url} couldn't be read: {str(err) or type(err).__name__}") from err
    if not isinstance(payload, dict):
        raise WikimediaError(f"{url} sent something unexpected")
    return payload
