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
    same_day,
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
    events = remember(memory, [obs(), obs(species="hoocro1", checklist="S900002")], [obs(checklist="S900003")], TODAY, 30)

    assert events == []
    assert memory.initialized
    assert memory.year_list == {"eurbla": "2026-10-10", "hoocro1": "2026-10-10"}
    assert set(memory.seen) == {"eurbla/S900001", "hoocro1/S900002", "eurbla/S900003"}


def test_a_species_new_this_year_is_its_first_of_the_year() -> None:
    memory = started(obs())

    events = remember(memory, [obs(), obs(species="hoocro1", checklist="S900002", observed="2026-10-11 09:00")], [], TODAY, 30)

    assert kinds(events) == [(FIRST_OF_YEAR, "hoocro1")]
    assert memory.year_list["hoocro1"] == "2026-10-11"


def test_the_same_checklist_seen_again_is_not_new() -> None:
    memory = started(obs())
    assert remember(memory, [obs()], [], TODAY, 30) == []


def test_a_species_back_after_a_while() -> None:
    memory = started(obs(observed="2026-08-01 10:00"), today=date(2026, 8, 2))
    remember(memory, [], [], date(2026, 10, 11), 30)

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
    rarity = {"species": "palhar1", "name": "Pallid Harrier", "scientific": "Circus macrourus", "reviewed": True}

    events = remember(memory, [obs(checklist="S900020", **rarity)], [obs(checklist="S900020", **rarity)], TODAY, 30)
    assert kinds(events) == [(NOTABLE, "palhar1"), (FIRST_OF_YEAR, "palhar1"), (FIRST_IN_REGION, "palhar1")]
    assert all(event.notable for event in events), "every event of a notable sighting says so"

    # Another checklist with it, before the region's list has caught up.
    events = remember(memory, [], [obs(checklist="S900021", **rarity)], TODAY, 30)
    assert kinds(events) == [(NOTABLE, "palhar1")]


def test_a_spuh_is_never_a_first_record() -> None:
    memory = started(obs())
    events = remember(memory, [obs(species="gull1", name="gull sp.", scientific="Larinae sp.", checklist="S900030")], [], TODAY, 30)
    assert kinds(events) == [(FIRST_OF_YEAR, "gull1")]


def test_the_region_list_compared_against_is_the_one_from_the_day_before() -> None:
    memory = started(obs())
    # Today's list already has the rarity, because its own checklist put it there.
    memory.set_region_species("FI-99", ["eurbla", "hoocro1", "palhar1"], date(2026, 10, 13))

    events = remember(memory, [obs(species="palhar1", scientific="Circus macrourus", checklist="S900040")], [], TODAY, 30)

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
    assert memory.past_years == {"2026": {"since": "2026-12-01", "first_seen": {"eurbla": "2026-12-30"}}}


def test_a_late_december_checklist_goes_on_last_years_list() -> None:
    memory = started(obs(observed="2026-12-30 10:00"), today=date(2026, 12, 31))
    remember(memory, [], [], date(2027, 1, 1), 30)

    remember(memory, [obs(species="gretit1", checklist="S900060", observed="2026-12-31 15:00")], [], date(2027, 1, 2), 30)

    assert memory.past_years["2026"]["first_seen"] == {"eurbla": "2026-12-30", "gretit1": "2026-12-31"}
    assert memory.year_list == {}


def test_a_new_year_after_a_gap_starts_where_its_first_poll_reaches() -> None:
    memory = started(obs(observed="2026-12-18 10:00"), today=date(2026, 12, 20))

    remember(memory, [obs(species="hoocro1", checklist="S900051", observed="2027-02-10 09:00")], [], date(2027, 2, 15), 30)

    assert memory.year_started == "2027-01-16", "the list can't know what was seen before the poll's 30 days"


def test_a_late_checklist_moves_a_first_sighting_earlier_without_an_event() -> None:
    memory = started(obs(observed="2026-10-11 10:00"))

    events = remember(memory, [obs(checklist="S900052", observed="2026-10-02 10:00")], [], TODAY, 30)

    assert events == []
    assert memory.year_list["eurbla"] == "2026-10-02"
    assert memory.last_seen["eurbla"] == "2026-10-11"


def test_a_late_december_checklist_moves_last_years_first_sighting_earlier() -> None:
    memory = started(obs(observed="2026-12-30 10:00"), today=date(2026, 12, 31))
    remember(memory, [], [], date(2027, 1, 1), 30)

    remember(memory, [obs(checklist="S900061", observed="2026-12-24 15:00")], [], date(2027, 1, 2), 30)

    assert memory.past_years["2026"]["first_seen"] == {"eurbla": "2026-12-24"}


def last_year(since: str, **first_seen: str) -> Memory:
    memory = Memory.new(date(2027, 5, 1))
    memory.past_years["2026"] = {"since": since, "first_seen": first_seen}
    return memory


def test_the_first_sighting_compared_with_last_year() -> None:
    memory = last_year("2026-01-01", eurbla="2026-04-10")
    assert memory.last_year_first_seen("eurbla") == date(2026, 4, 10)
    assert memory.days_vs_last_year("eurbla", date(2027, 4, 21)) == 11
    assert memory.days_vs_last_year("eurbla", date(2027, 4, 3)) == -7
    assert memory.days_vs_last_year("hoocro1", date(2027, 4, 3)) is None, "not seen last year"


def test_no_comparison_with_the_year_of_installation() -> None:
    # The list started in October: a first date then is often only the day the list started.
    memory = last_year("2026-10-12", eurbla="2026-10-12")
    assert memory.last_year_first_seen("eurbla") == date(2026, 10, 12)
    assert memory.days_vs_last_year("eurbla", date(2027, 4, 21)) is None


def test_species_seen_by_now_last_year_but_not_yet_this_year() -> None:
    # Expected also from a year that started late: what it saw by this date, it saw.
    memory = last_year("2026-03-15", eurbla="2026-04-10", hoocro1="2026-03-20", gretit1="2026-05-02", comcra="2026-04-30")
    memory.year_list = {"hoocro1": "2027-03-25"}
    assert memory.expected(date(2027, 5, 1)) == [("eurbla", date(2026, 4, 10)), ("comcra", date(2026, 4, 30))]
    assert Memory.new(date(2027, 5, 1)).expected(date(2027, 5, 1)) == [], "nothing to expect in the first year"


def test_29_february_in_a_year_without_one() -> None:
    assert same_day(date(2028, 2, 29), 2029) == date(2029, 2, 28)
    assert same_day(date(2026, 3, 1), 2028) == date(2028, 3, 1)


def test_observations_older_than_the_window_are_forgotten() -> None:
    memory = started(obs(observed="2026-09-01 10:00"), today=date(2026, 9, 2))
    remember(memory, [], [], TODAY, 30)
    assert memory.seen == {}
    assert memory.last_seen == {"eurbla": "2026-09-01"}


def test_the_memory_survives_storage() -> None:
    memory = started(obs())
    assert Memory.from_dict(memory.as_dict()) == memory


def test_an_unreviewed_rarity_counts_once_ebird_accepts_it() -> None:
    memory = started(obs())
    rarity = {"species": "palhar1", "name": "Pallid Harrier", "scientific": "Circus macrourus", "checklist": "S900030"}

    events = remember(memory, [], [obs(**rarity)], TODAY, 30)
    assert kinds(events) == [(NOTABLE, "palhar1")]
    assert "palhar1" not in memory.year_list
    assert remember(memory, [], [obs(**rarity)], TODAY, 30) == [], "still waiting, and the notable event isn't repeated"

    events = remember(memory, [obs(**rarity, reviewed=True)], [obs(**rarity, reviewed=True)], TODAY, 30)
    assert kinds(events) == [(FIRST_OF_YEAR, "palhar1"), (FIRST_IN_REGION, "palhar1")]
    assert memory.year_list["palhar1"] == "2026-10-10"
    assert memory.pending == []


def test_a_rejected_rarity_is_forgotten_with_its_days() -> None:
    memory = started(obs())
    remember(memory, [], [obs(species="palhar1", checklist="S900031")], TODAY, 30)
    assert memory.pending == ["palhar1/S900031"]

    remember(memory, [], [], date(2026, 11, 20), 30)
    assert memory.pending == []
    assert "palhar1" not in memory.year_list


def test_no_species_is_back_after_a_gap_in_the_polls() -> None:
    # Nothing polled for longer than back_days: every species would look back.
    memory = started(obs(observed="2026-08-01 10:00"), today=date(2026, 8, 2))

    events = remember(memory, [obs(checklist="S900009", observed="2026-10-11 07:30")], [], TODAY, 30)

    assert events == []
    assert memory.last_seen["eurbla"] == "2026-10-11"
    assert memory.polled == TODAY.isoformat()


def test_a_list_started_in_january_reaches_back_to_new_year() -> None:
    assert Memory.new(date(2027, 1, 5)).year_started == "2027-01-01", "the first poll reaches into December"
    assert Memory.new(date(2027, 3, 15)).year_started == "2027-02-13"


def test_a_sighting_already_in_next_year_waits_for_it() -> None:
    memory = started(obs(observed="2026-12-30 10:00"), today=date(2026, 12, 31))
    new_year = obs(species="hoocro1", checklist="S900070", observed="2027-01-01 00:30")

    assert remember(memory, [new_year], [], date(2026, 12, 31), 30) == []
    events = remember(memory, [new_year], [], date(2027, 1, 1), 30)

    assert kinds(events) == [(FIRST_OF_YEAR, "hoocro1")]
    assert memory.year_list == {"hoocro1": "2027-01-01"}


def test_a_species_with_a_new_code_is_the_same_species() -> None:
    # eBird's taxonomy update gives the hooded crow a new code. Its sightings come back under the new one.
    crow = {"name": "Hooded Crow", "scientific": "Corvus cornix"}
    memory = started(obs(species="hoocro1", checklist="S900080", **crow))

    events = remember(
        memory,
        [
            obs(species="hoocro2", checklist="S900080", **crow),
            obs(species="hoocro2", checklist="S900081", observed="2026-10-11 09:00", **crow),
        ],
        [],
        TODAY,
        30,
    )

    assert events == [], "not a first of the year, nor a first record in the region"
    assert memory.year_list == {"hoocro2": "2026-10-10"}
    assert memory.last_seen == {"hoocro2": "2026-10-11"}
    assert "hoocro2" in memory.region_species and "hoocro1" not in memory.region_species
    assert set(memory.seen) == {"hoocro2/S900080", "hoocro2/S900081"}


def test_a_split_keeps_the_memory_with_the_code_that_kept_the_name() -> None:
    # The old code retires. One new code keeps the scientific name and the memory, the other is a new species.
    memory = started(obs(species="hergul", name="Herring Gull", scientific="Larus argentatus", checklist="S900090"), region=("hergul",))

    events = remember(
        memory,
        [
            obs(species="euhgul1", name="European Herring Gull", scientific="Larus argentatus", checklist="S900091"),
            obs(species="amhgul1", name="American Herring Gull", scientific="Larus smithsonianus", checklist="S900092"),
        ],
        [],
        TODAY,
        30,
    )

    assert kinds(events) == [(FIRST_OF_YEAR, "amhgul1"), (FIRST_IN_REGION, "amhgul1")]
    assert set(memory.year_list) == {"euhgul1", "amhgul1"}
    assert memory.year_list["euhgul1"] == "2026-10-10"


def test_a_taxonomy_change_after_the_days_list_is_recognised_the_next_day() -> None:
    # The day's list was fetched before eBird switched, and a gull came under its new code later that day.
    memory = started(obs(species="hergul", scientific="Larus argentatus", checklist="S900093"), region=("hergul", "eurbla"))
    remember(memory, [obs(species="euhgul1", scientific="Larus argentatus", checklist="S900094")], [], TODAY, 30)
    assert memory.region_latest == ["hergul", "eurbla"], "the list fetched last stays as eBird sent it"

    # The next day's list shows the old code gone, so its new codes are not first records that day.
    memory.set_region_species("FI-99", ["amhgul1", "eurbla", "euhgul1"], date(2026, 10, 13))
    events = remember(memory, [obs(species="amhgul1", scientific="Larus smithsonianus", checklist="S900095")], [], date(2026, 10, 13), 30)
    assert kinds(events) == [(FIRST_OF_YEAR, "amhgul1")]


def test_a_renamed_species_keeps_its_earliest_and_latest_dates() -> None:
    memory = Memory.new(TODAY)
    memory.year_list = {"old1": "2026-04-02", "new1": "2026-05-10"}
    memory.last_seen = {"old1": "2026-10-01", "new1": "2026-09-01"}
    memory.rename("old1", "new1")
    assert memory.year_list == {"new1": "2026-04-02"}
    assert memory.last_seen == {"new1": "2026-10-01"}


def test_codes_without_a_scientific_name_are_listed_once() -> None:
    memory = Memory.new(TODAY)
    memory.year_list = {"a1": "2026-04-02", "b1": "2026-05-10"}
    memory.past_years["2025"] = {"since": "2025-01-01", "first_seen": {"c1": "2025-05-01"}}
    memory.scientific = {"a1": "Avis a", "b1": ""}
    assert memory.unnamed() == ["c1"], "an empty name was asked for already"


def test_a_notable_event_tells_a_new_rarity_from_one_seen_again() -> None:
    memory = started(obs())
    rarity = {"species": "palhar1", "name": "Pallid Harrier", "scientific": "Circus macrourus", "reviewed": True}

    [notable, *_] = remember(memory, [obs(checklist="S900100", **rarity)], [obs(checklist="S900100", **rarity)], TODAY, 30)
    assert (notable.kind, notable.first_in_region, notable.days_since_notable) == (NOTABLE, True, None)

    # The same bird on another checklist two days later: not a first record any more, and notable two days ago.
    later = {**rarity, "checklist": "S900101", "observed": "2026-10-12 08:00"}
    [notable] = remember(memory, [obs(**later)], [obs(**later)], date(2026, 10, 12), 30)
    assert (notable.first_in_region, notable.days_since_notable) == (False, 2)


def test_new_codes_on_the_region_list_are_not_new_species_the_day_they_appear() -> None:
    memory = Memory.new(TODAY)
    memory.set_region_species("FI-99", ["eurbla", "hoocro1"], TODAY)
    memory.set_region_species("FI-99", ["eurbla", "hoocro1", "gretit1"], date(2026, 10, 13))
    assert memory.region_species == ["eurbla", "hoocro1"], "an ordinary day compares against the day before"

    # A code left the list: eBird's taxonomy changed overnight.
    memory.set_region_species("FI-99", ["eurbla", "gretit1", "hoocro2"], date(2026, 10, 14))
    assert memory.region_species == ["eurbla", "gretit1", "hoocro1", "hoocro2"]


def test_a_memory_from_before_scientific_names_loads() -> None:
    stored = started(obs()).as_dict()
    del stored["scientific"]
    assert Memory.from_dict(stored).scientific == {}


def test_a_late_checklist_is_not_notable_before_it_was_seen() -> None:
    memory = started(obs())
    rarity = {"species": "palhar1", "name": "Pallid Harrier", "scientific": "Circus macrourus", "reviewed": True}
    remember(memory, [], [obs(checklist="S900110", observed="2026-10-12 08:00", **rarity)], TODAY, 30)

    [notable] = remember(memory, [], [obs(checklist="S900111", observed="2026-10-09 08:00", **rarity)], TODAY, 30)
    assert notable.days_since_notable == 0
    assert memory.notable_seen["palhar1"] == "2026-10-12", "the newest stays"


def test_a_rarity_seen_before_an_upgrade_is_not_new_after_it() -> None:
    # 1.1.0 kept no dates of notable sightings. The checklists it handled count once they come again.
    rarity = {"species": "palhar1", "name": "Pallid Harrier", "scientific": "Circus macrourus", "reviewed": True}
    memory = started(obs(checklist="S900120", **rarity))
    memory.notable_seen = {}
    remember(memory, [], [obs(checklist="S900120", **rarity)], TODAY, 30)

    events = remember(memory, [], [obs(checklist="S900121", observed="2026-10-12 08:00", **rarity)], TODAY, 30)
    assert next(event for event in events if event.kind == NOTABLE).days_since_notable == 2


def test_the_day_of_the_extra_call_carries_over_from_1_1_0() -> None:
    stored = Memory.new(TODAY).as_dict()
    del stored["extra_call_tried"]
    stored["region_tried"] = "2026-10-12"
    assert Memory.from_dict(stored).extra_call_tried == "2026-10-12"

    # The list was fetched today before 1.1.0 kept the day it tried: the day's extra call is spent all the same.
    stored["region_tried"], stored["region_fetched"] = None, "2026-10-14"
    assert Memory.from_dict(stored).extra_call_tried == "2026-10-14"
