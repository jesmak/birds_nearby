"""The sightings as a map feed, one point per location.

The format is documented in docs/map-feed-format.md of map-feed-card.
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
# The integration's icon green, and orange for a place with a notable sighting.
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
        "place": "sighting place",
        "places": "sighting places",
        "notable_place": "notable sighting",
        "by_distance": "Distance",
        "by_newest": "Newest",
        "km": "{km} km",
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
        "place": "havaintopaikka",
        "places": "havaintopaikkaa",
        "notable_place": "huomionarvoinen havainto",
        "by_distance": "Etäisyys",
        "by_newest": "Uusimmat",
        "km": "{km} km",
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


def feed_attributes(language: str) -> dict[str, Any]:
    """What the map feed card shows beside the places: the feed's type, what its colours mean and how its list sorts."""
    texts = TEXTS.get(language, TEXTS["en"])
    return {
        "feed_type": "nature",
        "legend": [{"color": BIRD_COLOR, "label": texts["place"]}, {"color": NOTABLE_COLOR, "label": texts["notable_place"]}],
        "list": {
            "sort": [
                {"key": "distance", "label": texts["by_distance"], "property": "distance_km"},
                {"key": "newest", "label": texts["by_newest"], "property": "updated", "order": "desc"},
            ],
            "default": "distance",
            "count": texts["places"],
            "count_one": texts["place"],
        },
    }


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
        km = round(distance_and_bearing(centre, place.latitude, place.longitude)[0], 1)
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
            "distance_km": km,
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
            # In the card's list a hotspot's row is its name, what was seen and its distance; the direction stays in
            # the subtitle, which the card shows with the details.
            properties["list"] = {
                "text": " · ".join(part for part in (count, day) if part),
                "value": texts["km"].format(km=decimal(km, language)),
            }
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
    if notable and not observation.reviewed:
        parts.append(texts["unreviewed"])
    threatened = info.iucn if info and info.iucn in SHOWN_IUCN else None
    # One tag a row: notable in the place's own colour, which is what made the place orange, or else the threat
    # status. A notable species that is also threatened keeps its status in the text.
    if notable and threatened:
        parts.append(threatened)
    row: dict[str, Any] = {"label": observation.name, "value": " · ".join(parts)}
    if notable:
        row["tag"] = {"text": texts["notable"], "tone": "item"}
    elif threatened:
        row["tag"] = {"text": threatened, "tone": "warning"}
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
    return texts["distance"].format(km=decimal(km, language), direction=direction(bearing, language))


def decimal(km: float, language: str) -> str:
    """ "3,2" in Finnish, "3.2" otherwise: Finnish formats only with Finnish texts, any other language gets English ones."""
    return f"{km:.1f}".replace(".", ",") if language == "fi" else f"{km:.1f}"


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
