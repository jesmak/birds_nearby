"""The sightings as a map feed, one point per location.

The format is documented in docs/map-feed-format.md of ha-map-card-plugin-map-feed.
Many species are seen at the same place, and markers at the same spot would hide each
other, so each location is one point listing its species.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

from .api import distance_km
from .pictures import Picture, SpeciesInfo
from .sightings import Observation

COORDINATE_DECIMALS = 5
# Commons' author field is free text, sometimes a sentence about the camera. The popup shows
# this much of it; the sensors and events carry it in full.
MAX_AUTHOR_LENGTH = 60
# The integration's icon green, and orange for a place with a notable sighting. Sent with every
# place, so the map is green even with versions of the map feed plugin that don't know birds.
BIRD_COLOR = "#2e7d32"
NOTABLE_COLOR = "#d84315"

# Closer to the area's centre than this, a direction means nothing.
CENTRE_KM = 0.1

# A place fades with the age of its newest sighting, down to this at the end of the recent days.
OLDEST_OPACITY = 0.4

# Shown after the species in the popup. Least concern says nothing, and data deficient too little.
SHOWN_IUCN = ("NT", "VU", "EN", "CR", "EW")

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "species": "{count} species",
        "one_bird": "1 bird",
        "birds": "{count} birds",
        "notable": "notable",
        "unreviewed": "not yet reviewed",
        "distance": "{km} km {direction}",
        "centre": "At the centre",
        "hotspot_link": "Hotspot on eBird",
    },
    "fi": {
        "species": "{count} lajia",
        "one_bird": "1 yksilö",
        "birds": "{count} yksilöä",
        "notable": "huomionarvoinen",
        "unreviewed": "ei vielä tarkastettu",
        "distance": "{km} km {direction}",
        "centre": "Alueen keskellä",
        "hotspot_link": "Havaintopaikka eBirdissä",
    },
}

# Compass directions from north, clockwise, in eight steps.
DIRECTIONS: dict[str, list[str]] = {
    "en": ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"],
    "fi": ["pohjoiseen", "koilliseen", "itään", "kaakkoon", "etelään", "lounaaseen", "länteen", "luoteeseen"],
}


@dataclass
class Place:
    feature_id: str
    location_id: str
    latitude: float
    longitude: float
    # The hotspot's name, or None for a personal location: its name is whatever the observer typed, often an address.
    hotspot_name: str | None
    observations: list[Observation] = field(default_factory=list)


def places(observations: list[Observation]) -> list[Place]:
    """The observations grouped by where they were made, newest first within each place."""
    by_id: dict[str, Place] = {}
    for observation in sorted(observations, key=lambda item: item.observed, reverse=True):
        feature_id = f"location:{observation.location_id}"
        place = by_id.setdefault(
            feature_id, Place(feature_id, observation.location_id, observation.latitude, observation.longitude, observation.hotspot_name)
        )
        # A species seen there more than once is listed once, by its newest sighting.
        if all(seen.species != observation.species for seen in place.observations):
            place.observations.append(observation)
    return list(by_id.values())


def features(
    observations: list[Observation],
    notable_keys: set[str],
    species_info: dict[str, SpeciesInfo],
    centre: tuple[float, float],
    language: str,
    recent_days: int,
    now: datetime,
) -> list[dict[str, Any]]:
    """The map feed's GeoJSON features, a point per place.

    A hotspot is titled with its name and links to its page on eBird. A personal location is titled
    with where it is from the area's centre, which is honest about what eBird knows of it.
    """
    texts = TEXTS.get(language, TEXTS["en"])
    result: list[dict[str, Any]] = []
    for place in places(observations):
        species = place.observations
        has_notable = any(observation.key in notable_keys for observation in species)
        # Notable species first, then the newest.
        shown = sorted(species, key=lambda item: item.key not in notable_keys)
        where = from_centre(centre, place.latitude, place.longitude, language)
        # All from one day, usually one visit: the date goes in the subtitle and the rows show only the time.
        one_day = len({observation.observed.date() for observation in species}) == 1
        day = short_date(species[0].observed) if one_day else None
        count = texts["species"].format(count=len(species))
        if place.hotspot_name:
            name, subtitle = place.hotspot_name, " · ".join(part for part in (count, day, where) if part)
        else:
            name, subtitle = where, " · ".join(part for part in (count, day) if part)
        properties: dict[str, Any] = {
            "name": name,
            "kind": "bird",
            "updated": local_iso(species[0].observed),
            "badge": str(len(species)),
            "subtitle": subtitle,
            "color": NOTABLE_COLOR if has_notable else BIRD_COLOR,
            "opacity": opacity(species[0].observed, now, recent_days),
            "details": [
                _row(
                    observation,
                    observation.key in notable_keys,
                    species_info.get(observation.species),
                    one_day,
                    texts,
                    language,
                )
                for observation in shown
            ],
        }
        if place.hotspot_name:
            properties["link"] = {
                "url": f"https://ebird.org/hotspot/{place.location_id}",
                "label": texts["hotspot_link"],
            }
        result.append(
            {
                "type": "Feature",
                "id": place.feature_id,
                "geometry": {"type": "Point", "coordinates": _position(place.longitude, place.latitude)},
                "properties": _without_empty(properties),
            }
        )
    return result


def opacity(newest: datetime, now: datetime, recent_days: int) -> float:
    """1 for a place with a sighting today, fading evenly to OLDEST_OPACITY at the end of the recent days."""
    if recent_days <= 1:
        return 1.0
    days = (now.date() - newest.date()).days
    return round(1 - (1 - OLDEST_OPACITY) * min(max(days, 0) / (recent_days - 1), 1), 2)


def _row(
    observation: Observation,
    notable: bool,
    info: SpeciesInfo | None,
    time_only: bool,
    texts: dict[str, str],
    language: str,
) -> dict[str, Any]:
    """A species: how many, when, whether notable or threatened, and its picture, shown large when tapped."""
    parts = []
    if observation.count is not None:
        parts.append(texts["one_bird"] if observation.count == 1 else texts["birds"].format(count=observation.count))
    when = clock(observation.observed, language) if time_only else short_time(observation.observed, language)
    if when:
        parts.append(when)
    if notable:
        parts.append(texts["notable"] if observation.reviewed else f"{texts['notable']}, {texts['unreviewed']}")
    if info and info.iucn in SHOWN_IUCN:
        parts.append(info.iucn)
    row: dict[str, Any] = {"label": observation.name, "value": " · ".join(parts)}
    if info and info.picture:
        row["image"] = {"url": info.picture.url, "caption": caption(observation.name, info.picture)}
    return row


def caption(name: str, picture: Picture) -> str:
    """The species and the picture's credit, the author shortened and the licence always in full."""
    author = picture.author
    if len(author) > MAX_AUTHOR_LENGTH:
        author = author[: MAX_AUTHOR_LENGTH - 1].rstrip(" ,.") + "…"
    return " · ".join(part for part in (name, ", ".join(part for part in (author, picture.licence) if part)) if part)


def from_centre(centre: tuple[float, float], latitude: float, longitude: float, language: str) -> str:
    """ "3,2 km lounaaseen" in Finnish, "3.2 km southwest" in English."""
    texts = TEXTS.get(language, TEXTS["en"])
    km, bearing = distance_and_bearing(centre, latitude, longitude)
    if km < CENTRE_KM:
        return texts["centre"]
    # Finnish formats only with Finnish texts: any other language gets the English ones.
    shown = f"{km:.1f}".replace(".", ",") if language == "fi" else f"{km:.1f}"
    return texts["distance"].format(km=shown, direction=direction(bearing, language))


def distance_and_bearing(centre: tuple[float, float], latitude: float, longitude: float) -> tuple[float, float]:
    """Kilometres from the area's centre, and the direction in degrees clockwise from north."""
    north = math.radians(latitude - centre[0])
    east = math.radians(longitude - centre[1]) * math.cos(math.radians((latitude + centre[0]) / 2))
    return distance_km(centre[0], centre[1], latitude, longitude), math.degrees(math.atan2(east, north)) % 360


def direction(bearing: float, language: str) -> str:
    return DIRECTIONS.get(language, DIRECTIONS["en"])[round(bearing / 45) % 8]


def short_date(observed: datetime) -> str:
    return f"{observed.day}.{observed.month}."


def short_time(observed: datetime, language: str) -> str:
    """ "11.10. 14.05" in Finnish, "11.10. 14:05" in English, or "11.10." when the observer gave no time."""
    time = clock(observed, language)
    return f"{short_date(observed)} {time}" if time else short_date(observed)


def clock(observed: datetime, language: str) -> str | None:
    """ "14.05" in Finnish, "14:05" in English, or None when the observer gave no time (eBird then sends midnight)."""
    if observed.hour == 0 and observed.minute == 0:
        return None
    return f"{observed:%H.%M}" if language == "fi" else f"{observed:%H:%M}"


def local_iso(observed: datetime) -> str:
    """eBird gives the observation's local time without a zone; Home Assistant's zone is the nearest guess."""
    return observed.replace(tzinfo=dt_util.get_default_time_zone()).isoformat(timespec="seconds")


def _position(longitude: float, latitude: float) -> list[float]:
    # GeoJSON order: longitude first.
    return [round(longitude, COORDINATE_DECIMALS), round(latitude, COORDINATE_DECIMALS)]


def _without_empty(properties: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in properties.items() if value not in (None, "", [])}
