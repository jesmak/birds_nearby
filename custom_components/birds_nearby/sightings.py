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
    def hotspot_name(self) -> str | None:
        """None for a personal location: its name is whatever the observer typed, often an address."""
        return None if self.personal else self.location_name

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
    # Among eBird's notable observations, whatever the event.
    notable: bool = False
    # Days since the species was last seen, for the back-after-a-while event.
    days_unseen: int | None = None
    # For a notable event: whether the same sighting is a first record in the region, and how many days earlier the
    # species was last notable, so a rarity seen on many checklists can be told apart from a new one.
    first_in_region: bool = False
    days_since_notable: int | None = None


# Event kinds; the coordinator maps them to the events fired on the bus.
NOTABLE = "notable"
FIRST_OF_YEAR = "first_of_year"
BACK = "back"
FIRST_IN_REGION = "first_in_region"


@dataclass
class Memory:
    """What the integration has learned since it was set up. Kept in its own storage."""

    year: int
    # The day this year's list started: as far back as the year's first poll reached, which is 1 January when the
    # integration was running on it.
    year_started: str
    # Species code: the date it was first seen this year.
    year_list: dict[str, str] = field(default_factory=dict)
    # Species code: the newest date it was seen, kept across years.
    last_seen: dict[str, str] = field(default_factory=dict)
    # Earlier years' lists by year: {"since": the day the list started, "first_seen": {species code: date}}.
    past_years: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Observation key: its date. Only the last 30 days, which is all eBird can send again.
    seen: dict[str, str] = field(default_factory=dict)
    # Notable observations seen but not yet reviewed: they count once eBird has accepted them.
    pending: list[str] = field(default_factory=list)
    # The day of the last successful poll. After a longer gap than back_days, any species would look back.
    polled: str | None = None
    # Species code: the name eBird last gave it, in the language asked for.
    names: dict[str, str] = field(default_factory=dict)
    # Species code: its scientific name. eBird's yearly taxonomy update gives some species new codes, and the
    # scientific name is what links a new code to the memory of the old one. Empty for a code eBird no longer knows.
    scientific: dict[str, str] = field(default_factory=dict)
    # Species code: the day it was last among the notable observations. Only the last 30 days.
    notable_seen: dict[str, str] = field(default_factory=dict)
    # The region's species list: the one compared against, and the one fetched last.
    # Comparing against the older one means a sighting can't hide itself by already being on the list.
    region: str | None = None
    region_species: list[str] | None = None
    region_latest: list[str] | None = None
    region_fetched: str | None = None
    # The day the day's extra call to eBird was last made, failed or not: the region's list or, while species in the
    # memory have no scientific name, their names. One a day at most, across restarts and reloads.
    extra_call_tried: str | None = None
    # The day the names were last asked for. They are asked every other day at most, so the region's list is never
    # older than a day, even while eBird keeps failing to answer for the names.
    names_asked: str | None = None
    # Species already announced as a first record in the region, so a later checklist doesn't repeat it.
    region_announced: list[str] = field(default_factory=list)
    initialized: bool = False

    @classmethod
    def new(cls, today: date) -> Memory:
        return cls(year=today.year, year_started=list_start(today))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Memory:
        # 1.1.0 kept the day of the extra call as the day the region's list was tried, and older versions not at all,
        # so the day the list was last fetched counts too.
        earlier = max((day for day in (data.get("region_tried"), data.get("region_fetched")) if day), default=None)
        data = {"extra_call_tried": earlier, **data}
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
            previous = self.region_latest or species
            # A species is never taken off a region's list of everything ever recorded, except when eBird's taxonomy
            # changes. That day the new codes are old species, so both lists count as known.
            self.region_species = sorted({*previous, *species}) if set(previous) - set(species) else previous
        self.region_latest = species
        self.region_fetched = today.isoformat()

    def unnamed(self) -> list[str]:
        """The codes in the memory whose scientific name hasn't been asked from eBird yet."""
        codes = {*self.year_list, *self.last_seen, *(code for year in self.past_years.values() for code in year["first_seen"])}
        return sorted(code for code in codes if code not in self.scientific)

    def rename(self, old: str, new: str) -> None:
        """Moves everything remembered of a species from its old code to the new one eBird gave it.

        Where both codes have a date, the first sighting is the earlier one and the last sighting the later one.
        """
        first_dates = (self.year_list, *(year["first_seen"] for year in self.past_years.values()))
        for codes, keep in ((self.last_seen, max), (self.notable_seen, max), *((dates, min) for dates in first_dates)):
            if old in codes:
                codes[new] = keep(codes[old], codes[new]) if new in codes else codes[old]
                del codes[old]
        for codes in (self.names, self.scientific):
            if old in codes:
                codes.setdefault(new, codes[old])
                del codes[old]
        prefix = f"{old}/"
        self.seen = {f"{new}/{key[len(prefix) :]}" if key.startswith(prefix) else key: day for key, day in self.seen.items()}
        self.pending = [f"{new}/{key[len(prefix) :]}" if key.startswith(prefix) else key for key in self.pending]
        self.region_announced = sorted({new if code == old else code for code in self.region_announced})
        # Only the list compared against. The list fetched last stays as eBird sent it, so tomorrow's list still shows
        # the old code leaving it, and the taxonomy day is recognised then if it wasn't today.
        if self.region_species is not None and old in self.region_species:
            self.region_species = sorted({new if code == old else code for code in self.region_species})

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


def list_start(today: date) -> str:
    """The first day a year's list can have when its first poll is today: 30 days back, into this year or to its start."""
    return max(date(today.year, 1, 1), today - timedelta(days=WINDOW_DAYS)).isoformat()


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
        # After a gap over New Year, the list starts where the first poll reaches, not on 1 January.
        memory.year_started = list_start(today)
        memory.year_list = {}
    follow_new_codes(memory, [*recent, *notable])

    region_known = set(memory.region_species or [])
    announced = set(memory.region_announced)
    pending = set(memory.pending)
    notable_keys = {observation.key for observation in notable}
    # A notable report counts for the lists only once eBird has reviewed and accepted it.
    unconfirmed = {observation.key for observation in notable if not (observation.reviewed and observation.valid)}
    # Every species seen while nobody was watching would look back after a while.
    watched = memory.polled is not None and (today - date.fromisoformat(memory.polled)).days < back_days
    events: list[Event] = []

    # Oldest first, so a species seen on two new checklists is compared with the older one first.
    for observation in sorted([*recent, *notable], key=lambda item: item.observed):
        memory.names[observation.species] = observation.name
        if observation.scientific:
            memory.scientific[observation.species] = observation.scientific
        key = observation.key
        seen_on = observation.observed.date()
        if seen_on.year > memory.year:
            # Already New Year where the bird was seen, not yet in Home Assistant's time zone.
            continue
        is_new = key not in memory.seen
        if not is_new and (key not in pending or key in unconfirmed):
            continue
        memory.seen[key] = seen_on.isoformat()
        notable_here = key in notable_keys
        first_in_region = (
            memory.region_species is not None
            and observation.is_species
            and observation.species not in region_known
            and observation.species not in announced
        )
        if is_new and notable_here:
            earlier = memory.notable_seen.get(observation.species)
            if memory.initialized:
                events.append(
                    Event(
                        NOTABLE,
                        observation,
                        notable=True,
                        first_in_region=first_in_region and key not in unconfirmed,
                        # A checklist uploaded late can be older than the last notable sighting.
                        days_since_notable=max((seen_on - date.fromisoformat(earlier)).days, 0) if earlier else None,
                    )
                )
            if earlier is None or seen_on.isoformat() > earlier:
                memory.notable_seen[observation.species] = seen_on.isoformat()
        if key in unconfirmed:
            pending.add(key)
            continue
        pending.discard(key)

        is_new_this_year = seen_on.year == memory.year and observation.species not in memory.year_list
        previous = memory.last_seen.get(observation.species)
        days_unseen = (seen_on - date.fromisoformat(previous)).days if previous else None

        if memory.initialized:
            if is_new_this_year:
                events.append(Event(FIRST_OF_YEAR, observation, notable=notable_here))
            if watched and days_unseen is not None and days_unseen >= back_days:
                events.append(Event(BACK, observation, notable=notable_here, days_unseen=days_unseen))
            if first_in_region:
                announced.add(observation.species)
                events.append(Event(FIRST_IN_REGION, observation, notable=notable_here))

        # The earliest day of the year the species was seen, also from a checklist uploaded late. One of the last days of
        # December can reach eBird after New Year.
        past = memory.past_years.get(str(seen_on.year))
        first_dates = memory.year_list if seen_on.year == memory.year else past["first_seen"] if past else None
        first = first_dates.get(observation.species) if first_dates is not None else None
        if first_dates is not None and (first is None or seen_on.isoformat() < first):
            first_dates[observation.species] = seen_on.isoformat()
        if previous is None or seen_on.isoformat() > previous:
            memory.last_seen[observation.species] = seen_on.isoformat()

    # Every notable sighting counts as seen, also one handled before an upgrade that started keeping these dates.
    for observation in notable:
        seen_on = observation.observed.date().isoformat()
        if seen_on > memory.notable_seen.get(observation.species, ""):
            memory.notable_seen[observation.species] = seen_on

    oldest = (today - timedelta(days=WINDOW_DAYS + 2)).isoformat()
    memory.seen = {key: seen_on for key, seen_on in memory.seen.items() if seen_on >= oldest}
    memory.notable_seen = {code: seen_on for code, seen_on in memory.notable_seen.items() if seen_on >= oldest}
    # A report eBird rejected, or never reviewed within its 30 days, is forgotten with them.
    memory.pending = sorted(key for key in pending if key in memory.seen)
    memory.region_announced = sorted(announced)
    memory.polled = today.isoformat()
    memory.initialized = True
    return events


def follow_new_codes(memory: Memory, observations: list[Observation]) -> None:
    """Moves the memory of species that eBird has given a new code, recognised by their scientific name.

    When the old code is still in use too, the species was split and both are species of their own.
    """
    in_use = {observation.species for observation in observations}
    by_name = {name: code for code, name in memory.scientific.items() if name}
    for observation in observations:
        old = by_name.get(observation.scientific)
        if observation.species not in memory.scientific and old and old not in in_use and observation.is_species:
            memory.rename(old, observation.species)
            by_name[observation.scientific] = observation.species


def newest_first(observations: list[Observation]) -> list[Observation]:
    return sorted(observations, key=lambda item: item.observed, reverse=True)
