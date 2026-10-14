"""eBird API 2.0, documented at https://documenter.getpostman.com/view/664302/S1ENwy59."""

from __future__ import annotations

import math
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import EBIRD_URL, REQUEST_DECIMALS, USER_AGENT, WINDOW_DAYS
from .exceptions import EbirdAuthError, EbirdError
from .sightings import Observation, parse_observations

TIMEOUT = aiohttp.ClientTimeout(total=30)


class EbirdClient:
    def __init__(self, hass: HomeAssistant, api_key: str) -> None:
        self._session = async_get_clientsession(hass)
        self._headers = {"x-ebirdapitoken": api_key, "User-Agent": USER_AGENT}

    async def recent(self, latitude: float, longitude: float, radius_km: int, locale: str) -> list[Observation]:
        """The newest observation of each species within the radius, over the last 30 days."""
        return parse_observations(await self._get("data/obs/geo/recent", self._near(latitude, longitude, radius_km, locale)))

    async def notable(self, latitude: float, longitude: float, radius_km: int, locale: str) -> list[Observation]:
        """eBird's notable observations within the radius, over the last 30 days.

        Only simple detail is asked for, which has no observer names.
        """
        params = {**self._near(latitude, longitude, radius_km, locale), "detail": "simple"}
        return parse_observations(await self._get("data/obs/geo/recent/notable", params))

    async def nearest_region(self, latitude: float, longitude: float) -> str | None:
        """The county of the nearest hotspot, or its region where eBird has no counties (Finland, for one).

        None when there is no hotspot within 50 km. Also the cheapest call that checks the key.
        """
        params = {
            "lat": round(latitude, REQUEST_DECIMALS),
            "lng": round(longitude, REQUEST_DECIMALS),
            "dist": 50,
            "fmt": "json",
        }
        hotspots = await self._get("ref/hotspot/geo", params)
        if not isinstance(hotspots, list):
            raise EbirdError("eBird sent the hotspots in an unexpected format")
        located = [spot for spot in hotspots if isinstance(spot, dict) and "lat" in spot and "lng" in spot]
        if not located:
            return None
        nearest = min(located, key=lambda spot: distance_km(latitude, longitude, spot["lat"], spot["lng"]))
        return nearest.get("subnational2Code") or nearest.get("subnational1Code")

    async def region_species(self, region: str) -> list[str]:
        """The codes of every species ever recorded in the region."""
        species = await self._get(f"product/spplist/{region}", {})
        if not isinstance(species, list) or not all(isinstance(code, str) for code in species):
            raise EbirdError(f"eBird sent the species of {region} in an unexpected format")
        return species

    @staticmethod
    def _near(latitude: float, longitude: float, radius_km: int, locale: str) -> dict[str, Any]:
        return {
            "lat": round(latitude, REQUEST_DECIMALS),
            "lng": round(longitude, REQUEST_DECIMALS),
            "dist": radius_km,
            "back": WINDOW_DAYS,
            "sppLocale": locale,
        }

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        try:
            async with self._session.get(f"{EBIRD_URL}/{path}", params=params, headers=self._headers, timeout=TIMEOUT) as response:
                if response.status in (401, 403):
                    raise EbirdAuthError("eBird refused the API key")
                if response.status != 200:
                    raise EbirdError(f"eBird answered with status {response.status}")
                return await response.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EbirdError(f"eBird couldn't be reached: {err}") from err
        except ValueError as err:
            raise EbirdError(f"eBird sent something unexpected: {err}") from err


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def ebird_locale(language: str) -> str:
    """Home Assistant's language as eBird's sppLocale: "pt-BR" is "pt_BR". eBird falls back to English."""
    return language.replace("-", "_")
