"""Observations from eBird, and the memory the integration builds of them over time.

eBird's API looks back 30 days at most and gives no time an observation was loaded,
so everything that needs a longer memory, or needs to know what is new, is kept here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from .const import WINDOW_DAYS


@dataclass(frozen=True)
class Observation:
    species: str
    name: str
    scientific: str
    # None when the observer only noted the species as present ("X" in eBird).
    count: int | None
    # In the observation's own local time, as eBird gives it.
    observed: datetime
    location_id: str
    location_name: str
    latitude: float
    longitude: float
    # A spot the observer pinned for themselves rather than a public hotspot (eBird's locationPrivate).
    personal: bool
    checklist: str
    valid: bool
    reviewed: bool

    @property
    def key(self) -> str:
        """A species on a checklist: what is new to the integration is keyed on this."""
        return f"{self.species}/{self.checklist}"

    @property
    def is_species(self) -> bool:
        # Spuhs ("gull sp."), slashes and hybrids are reported too. They never make a
        # first record in a region, so they are left out of that comparison.
        return not any(mark in self.scientific for mark in ("sp.", "/", " x "))


def parse_observations(payload: Any) -> list[Observation]:
    """eBird's observations at simple detail. Raises ValueError on an unexpected shape."""
    if not isinstance(payload, list):
        raise ValueError("expected a list of observations")
    return [_parse(item) for item in payload]


def _parse(item: dict[str, Any]) -> Observation:
    try:
        observed = item["obsDt"]
        # A time is given when the observer recorded one; otherwise only the date.
        parsed = datetime.strptime(observed, "%Y-%m-%d %H:%M" if len(observed) > 10 else "%Y-%m-%d")
        count = item.get("howMany")
        return Observation(
            species=item["speciesCode"],
            name=item.get("comName") or item["speciesCode"],
            scientific=item.get("sciName") or "",
            count=int(count) if count is not None else None,
            observed=parsed,
            location_id=item["locId"],
            location_name=item.get("locName") or "",
            latitude=float(item["lat"]),
            longitude=float(item["lng"]),
            personal=bool(item.get("locationPrivate", False)),
            checklist=item["subId"],
            valid=bool(item.get("obsValid", True)),
            reviewed=bool(item.get("obsReviewed", False)),
        )
    except (KeyError, TypeError, ValueError) as err:
        raise ValueError(f"unexpected observation: {err}") from err


@dataclass(frozen=True)
class Event:
    kind: str
    observation: Observation
    # Days since the species was last seen, for the back-after-a-while event.
    days_unseen: int | None = None


# Event kinds; the coordinator maps them to the events fired on the bus.
NOTABLE = "notable"
FIRST_OF_YEAR = "first_of_year"
BACK = "back"
FIRST_IN_REGION = "first_in_region"


@dataclass
class Memory:
    """What the integration has learned since it was set up. Kept in its own storage."""

    year: int
    # The day this year's list started: installation, or 1 January after that.
    year_started: str
    # Species code: the date it was first seen this year.
    year_list: dict[str, str] = field(default_factory=dict)
    # Species code: the newest date it was seen, kept across years.
    last_seen: dict[str, str] = field(default_factory=dict)
    # Earlier years' lists by year: {"since": the day the list started, "first_seen": {species code: date}}.
    past_years: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Observation key: its date. Only the last 30 days, which is all eBird can send again.
    seen: dict[str, str] = field(default_factory=dict)
    # Species code: the name eBird last gave it, in the language asked for.
    names: dict[str, str] = field(default_factory=dict)
    # The region's species list: the one compared against, and the one fetched last.
    # Comparing against the older one means a sighting can't hide itself by already being on the list.
    region: str | None = None
    region_species: list[str] | None = None
    region_latest: list[str] | None = None
    region_fetched: str | None = None
    # Species already announced as a first record in the region, so a later checklist doesn't repeat it.
    region_announced: list[str] = field(default_factory=list)
    initialized: bool = False

    @classmethod
    def new(cls, today: date) -> Memory:
        return cls(year=today.year, year_started=today.isoformat())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Memory:
        return cls(**{key: value for key, value in data.items() if key in cls.__dataclass_fields__})

    def as_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    def set_region_species(self, region: str, species: list[str], today: date) -> None:
        """A freshly fetched species list of the region. A new region starts its comparison over."""
        if region != self.region:
            self.region = region
            self.region_species = species
            self.region_announced = []
        else:
            self.region_species = self.region_latest or species
        self.region_latest = species
        self.region_fetched = today.isoformat()

    def region_due(self, region: str | None, today: date) -> bool:
        return region is not None and (region != self.region or self.region_fetched != today.isoformat())

    @property
    def last_year(self) -> dict[str, Any] | None:
        return self.past_years.get(str(self.year - 1))

    def last_year_first_seen(self, species: str) -> date | None:
        last_year = self.last_year
        first = last_year["first_seen"].get(species) if last_year else None
        return date.fromisoformat(first) if first else None

    def days_vs_last_year(self, species: str, seen_on: date) -> int | None:
        """How many days later than last year the species was first seen, negative when earlier.

        Only against a list that ran from 1 January: in the year of installation, a species' first date is
        often only the day the list started.
        """
        last_year = self.last_year
        first = self.last_year_first_seen(species)
        if last_year is None or first is None or last_year["since"] != date(first.year, 1, 1).isoformat():
            return None
        return (seen_on - same_day(first, seen_on.year)).days

    def expected(self, today: date) -> list[tuple[str, date]]:
        """Species seen by this date last year but not yet this year, with last year's date, the earliest first."""
        last_year = self.last_year
        if last_year is None:
            return []
        found = [
            (species, date.fromisoformat(first))
            for species, first in last_year["first_seen"].items()
            if species not in self.year_list and same_day(date.fromisoformat(first), today.year) <= today
        ]
        return sorted(found, key=lambda item: item[1])


def same_day(day: date, year: int) -> date:
    """The day in another year; 29 February becomes the 28th in a year without it."""
    try:
        return day.replace(year=year)
    except ValueError:
        return day.replace(year=year, day=28)


def remember(
    memory: Memory,
    recent: list[Observation],
    notable: list[Observation],
    today: date,
    back_days: int,
) -> list[Event]:
    """Adds a poll's observations to the memory, and returns the events they cause.

    The first poll only fills the memory from the last 30 days, without events.
    """
    if today.year != memory.year:
        memory.past_years[str(memory.year)] = {"since": memory.year_started, "first_seen": memory.year_list}
        memory.year = today.year
        memory.year_started = date(today.year, 1, 1).isoformat()
        memory.year_list = {}

    region_known = set(memory.region_species or [])
    announced = set(memory.region_announced)
    notable_keys = {observation.key for observation in notable}
    events: list[Event] = []

    # Oldest first, so a species seen on two new checklists is compared with the older one first.
    for observation in sorted([*recent, *notable], key=lambda item: item.observed):
        memory.names[observation.species] = observation.name
        if observation.key in memory.seen:
            continue
        seen_on = observation.observed.date()
        memory.seen[observation.key] = seen_on.isoformat()
        is_new_this_year = seen_on.year == memory.year and observation.species not in memory.year_list
        previous = memory.last_seen.get(observation.species)
        days_unseen = (seen_on - date.fromisoformat(previous)).days if previous else None

        if memory.initialized:
            if observation.key in notable_keys:
                events.append(Event(NOTABLE, observation))
            if is_new_this_year:
                events.append(Event(FIRST_OF_YEAR, observation))
            if days_unseen is not None and days_unseen >= back_days:
                events.append(Event(BACK, observation, days_unseen))
            if (
                memory.region_species is not None
                and observation.is_species
                and observation.species not in region_known
                and observation.species not in announced
            ):
                announced.add(observation.species)
                events.append(Event(FIRST_IN_REGION, observation))

        if is_new_this_year:
            memory.year_list[observation.species] = seen_on.isoformat()
        elif (past := memory.past_years.get(str(seen_on.year))) and observation.species not in past["first_seen"]:
            # A checklist of the last days of December that reached eBird after New Year.
            past["first_seen"][observation.species] = seen_on.isoformat()
        if previous is None or seen_on.isoformat() > previous:
            memory.last_seen[observation.species] = seen_on.isoformat()

    oldest = (today - timedelta(days=WINDOW_DAYS + 2)).isoformat()
    memory.seen = {key: seen_on for key, seen_on in memory.seen.items() if seen_on >= oldest}
    memory.region_announced = sorted(announced)
    memory.initialized = True
    return events


def newest_first(observations: list[Observation]) -> list[Observation]:
    return sorted(observations, key=lambda item: item.observed, reverse=True)
