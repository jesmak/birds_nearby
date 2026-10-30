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
        return is_species(self.scientific)


def is_species(scientific: str) -> bool:
    """False for a spuh ("Larinae sp."), a slash between species ("Larus argentatus/smithsonianus") or a hybrid
    ("Larus smithsonianus x fuscus"). They count as no species: not on a year list, and never a first record in a region.

    eBird writes a species' two words first, so a subspecies group's, form's or intergrade's own slash or "x" comes
    after them ("Motacilla alba alba/dukhunensis", "Junco hyemalis [oreganus Group] x mearnsi").
    """
    words = scientific.split()
    return not (len(words) > 1 and ("sp." == words[1] or "/" in words[0] + words[1] or "x" in words[1:3]))


def binomial(scientific: str) -> str:
    """A species is its binomial. eBird's taxonomy gives a subspecies group's scientific name with its subspecies, its
    sightings without it. A spuh's, slash's or hybrid's name is kept whole, so it is still known as one."""
    return " ".join(scientific.split()[:2]) if is_species(scientific) else scientific


@dataclass(frozen=True)
class Taxon:
    """What eBird's taxonomy says of a species code."""

    scientific: str
    name: str
    # The code it counts as on a year list: itself for a species, its species for a subspecies group, and empty for a
    # spuh, a slash or a hybrid.
    counts_as: str


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
    # For a first of the year: the code it went on the year list as, which for a subspecies group is its species'.
    listed_as: str | None = None


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
    # Species code: the date it was first seen this year. Empty for a species already seen when the integration was set
    # up: eBird gives only the newest sighting of each species, so the first poll can't know when it was first seen.
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
    # Species code: its binomial (see binomial()). eBird's yearly taxonomy update gives some species new codes, and the
    # binomial is what links a new code to the memory of the old one. Codes on a list with the same one are one
    # species. Empty for a code eBird no longer knows, unless a sighting gave it one.
    scientific: dict[str, str] = field(default_factory=dict)
    # Species code: the code it counts as on a year list, from eBird's taxonomy (Taxon.counts_as). A code not yet here
    # is looked up in the day's extra call.
    counts_as: dict[str, str] = field(default_factory=dict)
    # Species code: the day it was last among the notable observations. Only the last 30 days.
    notable_seen: dict[str, str] = field(default_factory=dict)
    # The region's species list: the one compared against, and the one fetched last.
    # Comparing against the older one means a sighting can't hide itself by already being on the list.
    region: str | None = None
    region_species: list[str] | None = None
    region_latest: list[str] | None = None
    region_fetched: str | None = None
    # The day the day's extra call to eBird was last made, failed or not: the region's list or, while codes in the
    # memory haven't been looked up in eBird's taxonomy, their taxonomy. One a day at most, across restarts and reloads.
    extra_call_tried: str | None = None
    # The day the taxonomy was last asked for. It is asked every other day at most, so the region's list is never
    # older than a day, even while eBird keeps failing to answer for the taxonomy.
    names_asked: str | None = None
    # Codes already announced as a first record in the region, so a later checklist doesn't repeat it. Read as the
    # species they count as, so a group's lookup after its announcement counts too.
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
        # Before 1.3.0 the taxonomy's names were kept as eBird gave them.
        data["scientific"] = {code: binomial(name) for code, name in data.get("scientific", {}).items()}
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

    def unknown(self) -> list[str]:
        """The codes in the memory not yet looked up in eBird's taxonomy, also those seen but on no list, such as a
        subspecies group listed under its species' code."""
        codes = {
            *self.scientific,
            *self.year_list,
            *self.last_seen,
            *(code for year in self.past_years.values() for code in year["first_seen"]),
        }
        return sorted(code for code in codes if code not in self.counts_as)

    def learn(self, asked: list[str], taxa: dict[str, Taxon]) -> None:
        """The taxonomy of the codes asked for. A subspecies group's dates move to its species, and the dates of a code
        that counts as no species are dropped from the year lists."""
        for code in asked:
            taxon = taxa.get(code)
            if taxon is None:
                # A code eBird no longer knows stays as it is, unless its name says it counts as no species, and isn't
                # asked for again.
                self.scientific.setdefault(code, "")
                self.counts_as[code] = code if is_species(self.scientific[code]) else ""
                if not self.counts_as[code]:
                    self._count_as(code, "")
                continue
            self.scientific[code] = binomial(taxon.scientific)
            self.names[code] = taxon.name
            self.counts_as[code] = taxon.counts_as
            if taxon.counts_as != code:
                self._count_as(code, taxon.counts_as)

    def _count_as(self, code: str, species: str) -> None:
        # The earliest first sighting, and an empty date (before the installation) is earlier than any.
        for dates in self._first_dates():
            if code in dates:
                first = dates.pop(code)
                if species:
                    dates[species] = min(first, dates[species]) if species in dates else first
        if species:
            self._repoint(code, species)
        if species and code in self.last_seen:
            last = self.last_seen.pop(code)
            self.last_seen[species] = max(last, self.last_seen.get(species, last))
        if species:
            # Until the species itself is looked up, it goes by its group's name, and is matched by its group's binomial.
            self.names.setdefault(species, self.names.get(code, code))
            if self.scientific.get(code):
                self.scientific.setdefault(species, self.scientific[code])

    def _repoint(self, old: str, new: str) -> None:
        """The codes that counted as the old code count as the new one: a species' groups follow it."""
        self.counts_as = {code: new if counted == old else counted for code, counted in self.counts_as.items()}

    def _first_dates(self) -> tuple[dict[str, str], ...]:
        return (self.year_list, *(year["first_seen"] for year in self.past_years.values()))

    def listed_as(self, observation: Observation, first_dates: dict[str, str]) -> str | None:
        """The code an observation goes on a year list as, None when it counts as no species."""
        code = observation.species
        if code in self.counts_as:
            listed = self.counts_as[code]
            if not listed:
                return None
        elif not observation.is_species:
            return None
        else:
            listed = code
        # Codes with the same binomial on a list are one species, looked up or not. Until a group is looked up, it can be on
        # the list under its own code.
        name = binomial(observation.scientific)
        if listed not in first_dates and name:
            return next((other for other in first_dates if self.scientific.get(other) == name), listed)
        return listed

    def forget_backfill(self, installed: date) -> None:
        """Storage version 2. Before it, the first poll gave each species already seen its newest sighting in eBird's 30
        days as its first date. The dates up to the day of installation are dropped. Spuhs, slashes and hybrids leave
        the lists once the taxonomy is looked up, as every code is after the upgrade."""
        day = installed.isoformat()
        for dates in self._first_dates():
            for code, first in dates.items():
                if first <= day:
                    dates[code] = ""

    def rename(self, old: str, new: str) -> None:
        """Moves everything remembered of a species from its old code to the new one eBird gave it.

        Where both codes have a date, the first sighting is the earlier one and the last sighting the later one.
        """
        for codes, keep in ((self.last_seen, max), (self.notable_seen, max), *((dates, min) for dates in self._first_dates())):
            if old in codes:
                codes[new] = keep(codes[old], codes[new]) if new in codes else codes[old]
                del codes[old]
        for codes in (self.names, self.scientific):
            if old in codes:
                codes.setdefault(new, codes[old])
                del codes[old]
        # The new code is looked up on its own.
        self.counts_as.pop(old, None)
        self._repoint(old, new)
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
        """None also for a species seen before the installation, whose first date isn't known."""
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
            if first and species not in self.year_list and same_day(date.fromisoformat(first), today.year) <= today
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

    The first poll only fills the memory from the last 30 days, without events, and with no first dates.
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
    # A first record is judged by the species a code counts as: eBird's region list has species' codes, never their
    # groups'. An announced group counts as its species also when it was looked up after it was announced, and before
    # its lookup, a group is known by its species' binomial.
    known = region_known | {memory.counts_as.get(code) or code for code in announced}
    known_names = {memory.scientific[code] for code in known | announced if memory.scientific.get(code)}
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
            memory.scientific[observation.species] = binomial(observation.scientific)
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
            and memory.counts_as.get(observation.species) != ""
            and memory.counts_as.get(observation.species, observation.species) not in known
            and binomial(observation.scientific) not in known_names
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

        # The year's list, also last year's for a checklist uploaded late. One of the last days of December can reach
        # eBird after New Year.
        past = memory.past_years.get(str(seen_on.year))
        first_dates = memory.year_list if seen_on.year == memory.year else past["first_seen"] if past else None
        listed_as = memory.listed_as(observation, first_dates if first_dates is not None else {})
        is_new_this_year = listed_as is not None and seen_on.year == memory.year and listed_as not in memory.year_list
        # A subspecies group is last seen as its species, a spuh as itself.
        species = listed_as or observation.species
        previous = memory.last_seen.get(species)
        days_unseen = (seen_on - date.fromisoformat(previous)).days if previous else None

        if memory.initialized:
            if is_new_this_year:
                events.append(Event(FIRST_OF_YEAR, observation, notable=notable_here, listed_as=listed_as))
            if watched and days_unseen is not None and days_unseen >= back_days:
                events.append(Event(BACK, observation, notable=notable_here, days_unseen=days_unseen))
            if first_in_region:
                announced.add(observation.species)
                known.add(memory.counts_as.get(observation.species) or observation.species)
                known_names.add(binomial(observation.scientific))
                events.append(Event(FIRST_IN_REGION, observation, notable=notable_here))

        # The earliest day of the year the species was seen, also from a checklist uploaded late. An empty date stays
        # empty: the species was seen before the installation.
        if first_dates is not None and listed_as is not None:
            first = first_dates.get(listed_as)
            if first is None or seen_on.isoformat() < first:
                first_dates[listed_as] = seen_on.isoformat() if memory.initialized else ""
        if previous is None or seen_on.isoformat() > previous:
            memory.last_seen[species] = seen_on.isoformat()

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
    """Moves the memory of species that eBird has given a new code, recognised by their binomial.

    When the old code is still in use too, the species was split and both are species of their own.
    """
    in_use = {observation.species for observation in observations}
    # Only a code that counts as itself can be a species' old code, never a subspecies group the taxonomy has named. Of
    # the codes sharing a binomial, a looked-up species comes last and wins.
    codes = sorted(memory.scientific.items(), key=lambda item: item[0] in memory.counts_as)
    by_name = {name: code for code, name in codes if name and memory.counts_as.get(code, code) == code}
    for observation in observations:
        name = binomial(observation.scientific)
        old = by_name.get(name)
        if observation.species not in memory.scientific and old and old not in in_use and observation.is_species:
            memory.rename(old, observation.species)
            by_name[name] = observation.species


def newest_first(observations: list[Observation]) -> list[Observation]:
    return sorted(observations, key=lambda item: item.observed, reverse=True)
