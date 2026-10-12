"""The memory: what is new, and which events it causes."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.birds_nearby.sightings import (
    BACK,
    FIRST_IN_REGION,
    FIRST_OF_YEAR,
    NOTABLE,
    Memory,
    parse_observations,
    remember,
)

from .conftest import observation

TODAY = date(2026, 10, 12)


def obs(**fields):
    [parsed] = parse_observations([observation(**fields)])
    return parsed


def started(*recent, region=("eurbla", "hoocro1"), today=TODAY) -> Memory:
    """A memory after its first poll, with the region's list in place."""
    memory = Memory.new(today)
    memory.set_region_species("FI-99", list(region), today)
    assert remember(memory, list(recent), [], today, 30) == []
    return memory


def kinds(events):
    return [(event.kind, event.observation.species) for event in events]


def test_parsing_a_date_without_a_time_and_a_count_given_as_present() -> None:
    parsed = obs(observed="2026-10-10", count=None)
    assert parsed.observed.isoformat() == "2026-10-10T00:00:00"
    assert parsed.count is None


def test_an_unexpected_observation_is_an_error() -> None:
    with pytest.raises(ValueError):
        parse_observations([{"speciesCode": "eurbla"}])
    with pytest.raises(ValueError):
        parse_observations({"error": "nope"})


def test_the_first_poll_fills_the_lists_without_events() -> None:
    memory = Memory.new(TODAY)
    events = remember(
        memory, [obs(), obs(species="hoocro1", checklist="S900002")], [obs(checklist="S900003")], TODAY, 30
    )

    assert events == []
    assert memory.initialized
    assert memory.year_list == {"eurbla": "2026-10-10", "hoocro1": "2026-10-10"}
    assert set(memory.seen) == {"eurbla/S900001", "hoocro1/S900002", "eurbla/S900003"}


def test_a_species_new_this_year_is_its_first_of_the_year() -> None:
    memory = started(obs())

    events = remember(
        memory, [obs(), obs(species="hoocro1", checklist="S900002", observed="2026-10-11 09:00")], [], TODAY, 30
    )

    assert kinds(events) == [(FIRST_OF_YEAR, "hoocro1")]
    assert memory.year_list["hoocro1"] == "2026-10-11"


def test_the_same_checklist_seen_again_is_not_new() -> None:
    memory = started(obs())
    assert remember(memory, [obs()], [], TODAY, 30) == []


def test_a_species_back_after_a_while() -> None:
    memory = started(obs(observed="2026-08-01 10:00"), today=date(2026, 8, 2))

    events = remember(memory, [obs(checklist="S900009", observed="2026-10-11 07:30")], [], TODAY, 30)

    assert kinds(events) == [(BACK, "eurbla")]
    assert events[0].days_unseen == 71
    assert memory.last_seen["eurbla"] == "2026-10-11"


def test_a_species_seen_again_soon_is_not_back() -> None:
    memory = started(obs(observed="2026-10-01 10:00"))
    assert remember(memory, [obs(checklist="S900009", observed="2026-10-11 07:30")], [], TODAY, 30) == []


def test_a_late_checklist_from_before_the_last_sighting_changes_nothing() -> None:
    memory = started(obs(observed="2026-10-11 10:00"))

    events = remember(memory, [obs(checklist="S900008", observed="2026-09-20 10:00")], [], TODAY, 30)

    assert events == []
    assert memory.last_seen["eurbla"] == "2026-10-11"


def test_a_species_never_recorded_in_the_region_is_announced_once() -> None:
    memory = started(obs())
    rarity = {"species": "palhar1", "name": "Pallid Harrier", "scientific": "Circus macrourus"}

    events = remember(memory, [obs(checklist="S900020", **rarity)], [obs(checklist="S900020", **rarity)], TODAY, 30)
    assert kinds(events) == [(NOTABLE, "palhar1"), (FIRST_OF_YEAR, "palhar1"), (FIRST_IN_REGION, "palhar1")]

    # Another checklist with it, before the region's list has caught up.
    events = remember(memory, [], [obs(checklist="S900021", **rarity)], TODAY, 30)
    assert kinds(events) == [(NOTABLE, "palhar1")]


def test_a_spuh_is_never_a_first_record() -> None:
    memory = started(obs())
    events = remember(
        memory, [obs(species="gull1", name="gull sp.", scientific="Larinae sp.", checklist="S900030")], [], TODAY, 30
    )
    assert kinds(events) == [(FIRST_OF_YEAR, "gull1")]


def test_the_region_list_compared_against_is_the_one_from_the_day_before() -> None:
    memory = started(obs())
    # Today's list already has the rarity, because its own checklist put it there.
    memory.set_region_species("FI-99", ["eurbla", "hoocro1", "palhar1"], date(2026, 10, 13))

    events = remember(
        memory, [obs(species="palhar1", scientific="Circus macrourus", checklist="S900040")], [], TODAY, 30
    )

    assert (FIRST_IN_REGION, "palhar1") in kinds(events)


def test_a_new_year_starts_an_empty_list_without_last_years_sightings() -> None:
    memory = started(obs(observed="2026-12-30 10:00"), today=date(2026, 12, 31))

    events = remember(
        memory,
        [obs(observed="2026-12-30 10:00"), obs(species="hoocro1", checklist="S900050", observed="2027-01-01 09:00")],
        [],
        date(2027, 1, 1),
        30,
    )

    assert memory.year == 2027
    assert memory.year_started == "2027-01-01"
    assert memory.year_list == {"hoocro1": "2027-01-01"}
    assert kinds(events) == [(FIRST_OF_YEAR, "hoocro1")]


def test_observations_older_than_the_window_are_forgotten() -> None:
    memory = started(obs(observed="2026-09-01 10:00"), today=date(2026, 9, 2))
    remember(memory, [], [], TODAY, 30)
    assert memory.seen == {}
    assert memory.last_seen == {"eurbla": "2026-09-01"}


def test_the_memory_survives_storage() -> None:
    memory = started(obs())
    assert Memory.from_dict(memory.as_dict()) == memory
