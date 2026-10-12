"""Polling eBird, remembering what has been seen, and firing events for what is new."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import EbirdClient, ebird_locale
from .const import (
    CONF_API_KEY,
    CONF_BACK_DAYS,
    CONF_RADIUS_KM,
    CONF_RECENT_DAYS,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    DEFAULT_BACK_DAYS,
    DEFAULT_RECENT_DAYS,
    DEFAULT_SCAN_MINUTES,
    DOMAIN,
    EVENT_BACK,
    EVENT_FIRST_IN_REGION,
    EVENT_FIRST_OF_YEAR,
    EVENT_NOTABLE,
    MIN_SCAN_MINUTES,
)
from .exceptions import EbirdAuthError, EbirdError
from .pictures import Picture, WikimediaError, find_picture
from .sightings import BACK, FIRST_IN_REGION, FIRST_OF_YEAR, NOTABLE, Event, Memory, Observation, newest_first, remember

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1

EVENT_TYPES = {
    NOTABLE: EVENT_NOTABLE,
    FIRST_OF_YEAR: EVENT_FIRST_OF_YEAR,
    BACK: EVENT_BACK,
    FIRST_IN_REGION: EVENT_FIRST_IN_REGION,
}


def memory_store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}")


type BirdsConfigEntry = ConfigEntry[BirdsCoordinator]


@dataclass(frozen=True)
class Sightings:
    """What the sensors show, from the latest poll."""

    # The newest sighting of each species within the recent days, newest first.
    recent: list[Observation]
    # Every notable observation of the last 30 days, newest first.
    notable: list[Observation]
    # The first of the recent days.
    since: date
    updated: datetime


class BirdsCoordinator(DataUpdateCoordinator[Sightings]):
    config_entry: BirdsConfigEntry

    def __init__(self, hass: HomeAssistant, entry: BirdsConfigEntry) -> None:
        minutes = max(int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_MINUTES)), MIN_SCAN_MINUTES)
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=timedelta(minutes=minutes))
        self.latitude: float = entry.data["latitude"]
        self.longitude: float = entry.data["longitude"]
        self.radius_km: int = entry.data[CONF_RADIUS_KM]
        self.region: str | None = entry.options.get(CONF_REGION) or None
        self.recent_days: int = int(entry.options.get(CONF_RECENT_DAYS, DEFAULT_RECENT_DAYS))
        self.back_days: int = int(entry.options.get(CONF_BACK_DAYS, DEFAULT_BACK_DAYS))
        self.language = hass.config.language.split("-")[0]
        self._client = EbirdClient(hass, entry.data[CONF_API_KEY])
        self._store = memory_store(hass, entry.entry_id)
        self.memory = Memory.new(dt_util.now().date())
        # Species code: its picture. Species found to have none are tried again after a restart,
        # so a fixed lookup or a new picture on Wikipedia gets its chance.
        self.pictures: dict[str, Picture] = {}
        self._no_picture: set[str] = set()
        self._looking_up = False
        self._region_tried: date | None = None

    async def _async_setup(self) -> None:
        stored = await self._store.async_load()
        if stored:
            self.memory = Memory.from_dict(stored.get("memory", {}))
            self.pictures = {code: Picture.from_dict(data) for code, data in stored.get("pictures", {}).items()}

    async def _async_update_data(self) -> Sightings:
        today = dt_util.now().date()
        locale = ebird_locale(self.hass.config.language)
        try:
            await self._refresh_region(today)
            recent = await self._client.recent(self.latitude, self.longitude, self.radius_km, locale)
            notable = await self._client.notable(self.latitude, self.longitude, self.radius_km, locale)
        except EbirdAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except EbirdError as err:
            raise UpdateFailed(str(err)) from err

        first_poll = not self.memory.initialized
        events = remember(self.memory, recent, notable, today, self.back_days)
        for event in events:
            self.hass.bus.async_fire(EVENT_TYPES[event.kind], self.event_data(event))
        self._save()
        _LOGGER.debug(
            "%s species recent, %s notable, %s events%s",
            len(recent),
            len(notable),
            len(events),
            " (first poll, no events)" if first_poll else "",
        )

        since = today - timedelta(days=self.recent_days - 1)
        sightings = Sightings(
            recent=newest_first([item for item in recent if item.observed.date() >= since]),
            notable=newest_first(notable),
            since=since,
            updated=dt_util.now(),
        )
        self._find_pictures([*sightings.notable, *sightings.recent])
        return sightings

    async def _refresh_region(self, today: date) -> None:
        """The region's species list, once a day. A failure leaves yesterday's list in use."""
        region = self.region
        if region is None:
            # First records are off: nothing to compare against.
            self.memory.region = self.memory.region_species = self.memory.region_latest = None
            return
        if not self.memory.region_due(region, today) or self._region_tried == today:
            return
        if region != self.memory.region:
            # Never compare against another region's list, even if the new one can't be read yet.
            self.memory.region_species = None
        # One try a day, failed or not: a call to eBird on every update would be more than its fair share.
        self._region_tried = today
        try:
            species = await self._client.region_species(region)
        except EbirdAuthError:
            raise
        except EbirdError as err:
            _LOGGER.warning("Couldn't read the species list of %s, trying again tomorrow: %s", region, err)
            return
        self.memory.set_region_species(region, species, today)

    def event_data(self, event: Event) -> dict[str, Any]:
        observation = event.observation
        data: dict[str, Any] = {
            "entry_id": self.config_entry.entry_id,
            "species_code": observation.species,
            "name": observation.name,
            "scientific_name": observation.scientific,
            "count": observation.count,
            "observed": observation.observed.isoformat(timespec="minutes"),
            # A personal location's name is whatever the observer typed, often an address, so only hotspots are named.
            "location": None if observation.personal else observation.location_name,
            "hotspot": not observation.personal,
            "notable": event.kind == NOTABLE,
            "reviewed": observation.reviewed,
            "url": f"https://ebird.org/species/{observation.species}",
        }
        if event.days_unseen is not None:
            data["days_unseen"] = event.days_unseen
        if event.kind == FIRST_IN_REGION:
            data["region"] = self.memory.region
        if picture := self.pictures.get(observation.species):
            data["picture"] = picture.url
            data["picture_credit"] = picture.credit
        return data

    def _find_pictures(self, observations: list[Observation]) -> None:
        """Looks up the pictures of species not yet looked up, in the background, one at a time."""
        wanted = {
            observation.species: observation.scientific
            for observation in observations
            if observation.species not in self.pictures and observation.species not in self._no_picture
        }
        if wanted and not self._looking_up:
            self._looking_up = True
            self.config_entry.async_create_background_task(
                self.hass, self._look_up_pictures(wanted), f"{DOMAIN} pictures"
            )

    async def _look_up_pictures(self, wanted: dict[str, str]) -> None:
        session = async_get_clientsession(self.hass)
        found = 0
        try:
            for species, scientific in wanted.items():
                try:
                    picture = await find_picture(session, species, scientific)
                except WikimediaError as err:
                    _LOGGER.debug("No picture for %s this time: %s", species, err)
                    continue
                if picture:
                    self.pictures[species] = picture
                    found += 1
                else:
                    self._no_picture.add(species)
        finally:
            self._looking_up = False
        self._save()
        if found:
            self.async_update_listeners()

    def _save(self) -> None:
        self._store.async_delay_save(
            lambda: {
                "memory": self.memory.as_dict(),
                "pictures": {code: picture.as_dict() for code, picture in self.pictures.items()},
            },
            10,
        )
