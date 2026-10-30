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
    Taxon,
    binomial,
    is_species,
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


def test_the_first_poll_fills_the_lists_without_events_or_first_dates() -> None:
    memory = Memory.new(TODAY)
    events = remember(memory, [obs(), obs(species="hoocro1", checklist="S900002")], [obs(checklist="S900003")], TODAY, 30)

    assert events == []
    assert memory.initialized
    # eBird gives only the newest sighting of each species: when it was first seen this year isn't known.
    assert memory.year_list == {"eurbla": "", "hoocro1": ""}
    assert memory.last_seen == {"eurbla": "2026-10-10", "hoocro1": "2026-10-10"}
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


@pytest.mark.parametrize(
    "scientific",
    ["Larinae sp.", "Larus argentatus/smithsonianus", "Larus smithsonianus x fuscus"],
    ids=["spuh", "slash", "hybrid"],
)
def test_a_spuh_a_slash_or_a_hybrid_is_on_no_list(scientific: str) -> None:
    memory = started(obs())
    events = remember(memory, [obs(species="gull1", scientific=scientific, checklist="S900030")], [], TODAY, 30)
    assert events == [], "no first of the year, no first record"
    assert "gull1" not in memory.year_list


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
    assert memory.past_years == {"2026": {"since": "2026-12-01", "first_seen": {"eurbla": ""}}}


def test_a_late_december_checklist_goes_on_last_years_list() -> None:
    memory = started(obs(observed="2026-12-30 10:00"), today=date(2026, 12, 31))
    remember(memory, [], [], date(2027, 1, 1), 30)

    remember(memory, [obs(species="gretit1", checklist="S900060", observed="2026-12-31 15:00")], [], date(2027, 1, 2), 30)

    assert memory.past_years["2026"]["first_seen"] == {"eurbla": "", "gretit1": "2026-12-31"}
    assert memory.year_list == {}


def test_a_new_year_after_a_gap_starts_where_its_first_poll_reaches() -> None:
    memory = started(obs(observed="2026-12-18 10:00"), today=date(2026, 12, 20))

    remember(memory, [obs(species="hoocro1", checklist="S900051", observed="2027-02-10 09:00")], [], date(2027, 2, 15), 30)

    assert memory.year_started == "2027-01-16", "the list can't know what was seen before the poll's 30 days"


def test_a_late_checklist_moves_a_first_sighting_earlier_without_an_event() -> None:
    memory = started()
    remember(memory, [obs(observed="2026-10-11 10:00")], [], TODAY, 30)

    events = remember(memory, [obs(checklist="S900052", observed="2026-10-02 10:00")], [], TODAY, 30)

    assert events == []
    assert memory.year_list["eurbla"] == "2026-10-02"
    assert memory.last_seen["eurbla"] == "2026-10-11"


def test_a_species_seen_before_the_installation_keeps_no_date() -> None:
    memory = started(obs(observed="2026-10-11 10:00"))
    remember(memory, [obs(checklist="S900053", observed="2026-10-02 10:00")], [], TODAY, 30)
    assert memory.year_list["eurbla"] == ""


def test_a_late_december_checklist_moves_last_years_first_sighting_earlier() -> None:
    memory = started(today=date(2026, 12, 29))
    remember(memory, [obs(observed="2026-12-30 10:00")], [], date(2026, 12, 31), 30)
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
    assert memory.year_list == {"hoocro2": ""}
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
    assert memory.year_list == {"euhgul1": "", "amhgul1": "2026-10-10"}


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


def test_codes_not_looked_up_are_listed_once() -> None:
    memory = Memory.new(TODAY)
    memory.year_list = {"a1": "2026-04-02", "b1": "2026-05-10"}
    memory.last_seen = {"d1": "2026-05-10"}
    memory.past_years["2025"] = {"since": "2025-01-01", "first_seen": {"c1": "2025-05-01"}}
    memory.scientific = {"a1": "Avis a", "b1": "Avis b"}
    memory.counts_as = {"a1": "a1"}
    assert memory.unknown() == ["b1", "c1", "d1"], "a scientific name from a sighting is not the taxonomy"


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


SPARROW = {"scientific": "Zonotrichia leucophrys"}
SPECIES = {"species": "whcspa", "name": "White-crowned Sparrow", **SPARROW}
GROUP = {"species": "gwcspa", "name": "White-crowned Sparrow (Gambel's)", **SPARROW}
# The taxonomy gives a group's scientific name with its subspecies, its sightings without.
GAMBELII = "Zonotrichia leucophrys gambelii"


def test_a_subspecies_group_seen_after_its_species_is_not_a_new_species() -> None:
    memory = started(region=("whcspa", "gwcspa"))
    species = obs(checklist="S900130", observed="2026-10-05 10:00", **SPECIES)
    remember(memory, [species], [], TODAY, 30)

    # Not yet looked up: its scientific name is the species'.
    events = remember(memory, [species, obs(checklist="S900131", observed="2026-10-11 10:00", **GROUP)], [], TODAY, 30)

    assert events == []
    assert memory.year_list == {"whcspa": "2026-10-05"}
    assert memory.last_seen["whcspa"] == "2026-10-11"


def test_a_subspecies_group_seen_first_is_its_species_first_of_the_year() -> None:
    memory = started(region=("whcspa", "gwcspa"))
    group = obs(checklist="S900132", observed="2026-10-04 10:00", **GROUP)
    [event] = remember(memory, [group], [], TODAY, 30)
    assert (event.kind, event.observation.species, event.listed_as) == (FIRST_OF_YEAR, "gwcspa", "gwcspa")
    assert remember(memory, [group, obs(checklist="S900133", observed="2026-10-11 10:00", **SPECIES)], [], TODAY, 30) == []

    # The taxonomy names the species: the group's date moves to it, and it goes by the group's name until it is looked up.
    memory.learn(["gwcspa"], {"gwcspa": Taxon(GAMBELII, "White-crowned Sparrow (Gambel's)", "whcspa")})
    assert memory.year_list == {"whcspa": "2026-10-04"}
    assert memory.unknown() == ["whcspa"]
    memory.learn(["whcspa"], {"whcspa": Taxon("Zonotrichia leucophrys", "White-crowned Sparrow", "whcspa")})
    assert memory.names["whcspa"] == "White-crowned Sparrow"

    # Once looked up, a group counts as its species by its code, also on a new year's list.
    [event] = remember(memory, [obs(checklist="S900134", observed="2027-01-01 10:00", **GROUP)], [], date(2027, 1, 1), 30)
    assert (event.kind, event.listed_as) == (FIRST_OF_YEAR, "whcspa")
    assert memory.year_list == {"whcspa": "2027-01-01"}


def test_a_group_taken_for_its_species_new_code_is_put_back_by_the_taxonomy() -> None:
    # The species was last seen over 30 days ago, so the group's code looks like a new code eBird gave it.
    memory = started(region=("whcspa", "gwcspa"))
    remember(memory, [obs(checklist="S900135", observed="2026-08-20 10:00", **SPECIES)], [], date(2026, 8, 20), 30)
    memory.learn(["whcspa"], {"whcspa": Taxon("Zonotrichia leucophrys", "White-crowned Sparrow", "whcspa")})
    assert remember(memory, [obs(checklist="S900136", observed="2026-10-11 10:00", **GROUP)], [], TODAY, 30) == []
    assert memory.year_list == {"gwcspa": "2026-08-20"}

    memory.learn(memory.unknown(), {"gwcspa": Taxon(GAMBELII, "White-crowned Sparrow (Gambel's)", "whcspa")})
    assert memory.year_list == {"whcspa": "2026-08-20"}
    assert memory.last_seen == {"whcspa": "2026-10-11"}
    assert memory.unknown() == ["whcspa"], "looked up again for its name"


def test_two_codes_already_on_the_list_merge_once_looked_up() -> None:
    memory = started()
    memory.year_list = {"y00678": "2026-10-13", "crecar1": "2026-10-11", "eurbla": ""}
    memory.last_seen = {"y00678": "2026-10-13", "crecar1": "2026-10-17"}
    memory.learn(
        ["crecar1", "y00678", "eurbla"],
        {
            "crecar1": Taxon("Caracara plancus", "Crested Caracara (Northern)", "y00678"),
            "y00678": Taxon("Caracara plancus", "Crested Caracara", "y00678"),
        },
    )
    assert memory.year_list == {"y00678": "2026-10-11", "eurbla": ""}, "the earlier first, and a code eBird doesn't know stays"
    assert memory.last_seen == {"y00678": "2026-10-17"}
    assert memory.unknown() == []


def test_a_species_seen_before_the_installation_stays_so_when_merged() -> None:
    memory = Memory.new(TODAY)
    memory.year_list = {"whcspa": "2026-10-20", "gwcspa": ""}
    memory.learn(["gwcspa"], {"gwcspa": Taxon(GAMBELII, "White-crowned Sparrow (Gambel's)", "whcspa")})
    assert memory.year_list == {"whcspa": ""}


def test_a_hybrid_looked_up_leaves_the_lists() -> None:
    memory = Memory.new(TODAY)
    memory.year_list = {"x00450": "2026-10-06"}
    memory.past_years["2025"] = {"since": "2025-01-01", "first_seen": {"x00450": "2025-06-01"}}
    memory.learn(["x00450"], {"x00450": Taxon("Ammospiza nelsoni x caudacuta", "Nelson's x Saltmarsh Sparrow", "")})
    assert memory.year_list == {}
    assert memory.past_years["2025"]["first_seen"] == {}
    events = remember(memory, [obs(species="x00450", scientific="Ammospiza nelsoni x caudacuta", checklist="S900140")], [], TODAY, 30)
    assert memory.year_list == {}
    assert events == []


def test_the_backfill_is_forgotten_up_to_the_day_of_installation() -> None:
    # Installed on 12 October with 1.0.0: the first poll dated each species by its newest sighting.
    memory = Memory.new(date(2026, 10, 12))
    memory.year_list = {
        "eurbla": "2026-10-11",
        "hoocro1": "2026-10-12",
        "gretit1": "2026-10-13",
        "x01134": "2026-10-20",
    }
    memory.past_years["2025"] = {"since": "2025-01-01", "first_seen": {"eurbla": "2025-04-01"}}
    memory.forget_backfill(date(2026, 10, 12))
    assert memory.year_list == {"eurbla": "", "hoocro1": "", "gretit1": "2026-10-13", "x01134": "2026-10-20"}
    assert memory.past_years["2025"]["first_seen"] == {"eurbla": ""}


def test_last_year_with_species_from_before_the_installation() -> None:
    memory = last_year("2026-01-01", eurbla="", hoocro1="2026-04-10")
    assert memory.last_year_first_seen("eurbla") is None
    assert memory.days_vs_last_year("eurbla", date(2027, 4, 21)) is None
    assert memory.expected(date(2027, 5, 1)) == [("hoocro1", date(2026, 4, 10))], "no date, nothing to expect by"


@pytest.mark.parametrize("polls", [1, 2], ids=["one poll", "two polls"])
@pytest.mark.parametrize("species_looked_up", [False, True], ids=["species new", "species looked up"])
@pytest.mark.parametrize("group_looked_up", [False, True], ids=["group new", "group looked up"])
@pytest.mark.parametrize("group_first", [True, False], ids=["group first", "species first"])
def test_a_group_and_its_species_are_one_species_on_the_list(
    group_first: bool, group_looked_up: bool, species_looked_up: bool, polls: int
) -> None:
    # A species is its binomial: codes with the same one on a year list are one species, looked up or not.
    memory = started(region=("whcspa", "gwcspa"))
    if species_looked_up:
        memory.learn(["whcspa"], {"whcspa": Taxon(SPARROW["scientific"], "White-crowned Sparrow", "whcspa")})
    if group_looked_up:
        memory.learn(["gwcspa"], {"gwcspa": Taxon(GAMBELII, "White-crowned Sparrow (Gambel's)", "whcspa")})
    times = ("2026-10-10 08:00", "2026-10-11 09:00") if group_first else ("2026-10-11 09:00", "2026-10-10 08:00")
    group = obs(checklist="S900150", observed=times[0], **GROUP)
    species = obs(checklist="S900151", observed=times[1], **SPECIES)

    if polls == 1:
        events = remember(memory, [group, species], [], TODAY, 30)
    else:
        # eBird's recent observations still carry the first one in the second poll.
        first, second = (group, species) if group_first else (species, group)
        events = remember(memory, [first], [], TODAY, 30) + remember(memory, [first, second], [], TODAY, 30)

    listed = "gwcspa" if group_first and not group_looked_up else "whcspa"
    # Only the year list. A species looked up but not seen in the first poll, as when it was last seen over 30 days
    # ago, makes a group's first appearance look like its new code: the accepted case of
    # test_a_group_taken_for_its_species_new_code_is_put_back_by_the_taxonomy, with its first record in the region.
    events = [event for event in events if event.kind == FIRST_OF_YEAR]
    assert kinds(events) == [(FIRST_OF_YEAR, "gwcspa" if group_first else "whcspa")]
    assert events[0].listed_as == listed
    assert memory.year_list == {listed: "2026-10-10"}
    assert memory.last_seen == {listed: "2026-10-11"}
    # Every code seen is looked up, so a group listed under its species' code still merges into it.
    assert "gwcspa" in memory.unknown() or group_looked_up


def test_a_late_december_group_goes_on_last_years_list_as_its_species() -> None:
    memory = started(region=("whcspa", "gwcspa"), today=date(2026, 12, 29))
    remember(memory, [obs(checklist="S900155", observed="2026-12-30 10:00", **SPECIES)], [], date(2026, 12, 30), 30)
    remember(memory, [], [], date(2027, 1, 1), 30)

    late = obs(checklist="S900156", observed="2026-12-28 10:00", **GROUP)
    species = obs(checklist="S900155", observed="2026-12-30 10:00", **SPECIES)
    assert remember(memory, [species, late], [], date(2027, 1, 2), 30) == []
    assert memory.past_years["2026"]["first_seen"] == {"whcspa": "2026-12-28"}
    assert memory.year_list == {}


def test_a_group_looked_up_still_matches_its_species_and_another_group_by_name() -> None:
    memory = started(region=("whcspa", "gwcspa", "nwcspa"))
    group = obs(checklist="S900160", observed="2026-10-04 10:00", **GROUP)
    remember(memory, [group], [], TODAY, 30)
    memory.learn(["gwcspa"], {"gwcspa": Taxon(GAMBELII, "White-crowned Sparrow (Gambel's)", "whcspa")})
    assert memory.scientific["gwcspa"] == SPARROW["scientific"], "the sightings' name is kept"
    assert memory.year_list == {"whcspa": "2026-10-04"}

    # Before the species itself is looked up: another group of it, and the species.
    other = obs(species="nwcspa", name="White-crowned Sparrow (Nuttall's)", checklist="S900161", observed="2026-10-10 10:00", **SPARROW)
    species = obs(checklist="S900162", observed="2026-10-11 10:00", **SPECIES)
    assert remember(memory, [group, other, species], [], TODAY, 30) == []
    assert memory.year_list == {"whcspa": "2026-10-04"}


@pytest.mark.parametrize("species_first", [True, False], ids=["species remembered first", "group remembered first"])
def test_a_species_with_a_group_is_followed_to_its_new_code(species_first: bool) -> None:
    # Both looked up. eBird's taxonomy update then gives the species a new code, and only it is seen.
    memory = started(region=("whcspa", "gwcspa"))
    species = obs(checklist="S900175", observed="2026-10-02 09:00", **SPECIES)
    group = obs(checklist="S900176", observed="2026-10-02 10:00", **GROUP)
    remember(memory, [species, group] if species_first else [group, species], [], date(2026, 10, 2), 30)
    memory.learn(
        ["gwcspa", "whcspa"],
        {
            "gwcspa": Taxon(GAMBELII, "White-crowned Sparrow (Gambel's)", "whcspa"),
            "whcspa": Taxon(SPARROW["scientific"], "White-crowned Sparrow", "whcspa"),
        },
    )

    renamed = obs(species="whcspa1", name="White-crowned Sparrow", checklist="S900177", observed="2026-10-11 10:00", **SPARROW)
    events = remember(memory, [renamed], [], TODAY, 30)

    assert events == [], "not a first of the year, nor a first record in the region"
    assert memory.year_list == {"whcspa1": "2026-10-02"}
    assert memory.last_seen == {"whcspa1": "2026-10-11"}
    assert memory.counts_as["gwcspa"] == "whcspa1", "the group counts as the new code"
    assert "whcspa" not in memory.counts_as


@pytest.mark.parametrize(
    ("scientific", "listed"),
    [
        ("Larinae sp.", False),
        ("Larus argentatus/smithsonianus", False),
        ("Larus smithsonianus x fuscus", False),
        ("Avis old", True),
        ("", True),
        (None, True),
    ],
    ids=["spuh", "slash", "hybrid", "species", "no name", "never named"],
)
def test_a_code_ebird_no_longer_knows(scientific: str | None, listed: bool) -> None:
    memory = Memory.new(TODAY)
    memory.year_list = {"old1": "2026-04-02"}
    memory.last_seen = {"old1": "2026-10-01", "old2": "2026-09-01"}
    memory.past_years["2025"] = {"since": "2025-01-01", "first_seen": {"old1": "2025-05-01"}}
    if scientific is not None:
        memory.scientific = {"old1": scientific, "old2": scientific}
    memory.learn(["old1", "old2"], {})
    assert ("old1" in memory.year_list, "old1" in memory.past_years["2025"]["first_seen"]) == (listed, listed)
    assert memory.counts_as == {"old1": "old1" if listed else "", "old2": "old2" if listed else ""}
    assert memory.last_seen == {"old1": "2026-10-01", "old2": "2026-09-01"}, "last seen as itself, as a looked-up hybrid is"
    assert memory.unknown() == [], "not asked again"


def test_a_group_named_by_an_old_taxonomy_lookup_still_matches_by_its_binomial() -> None:
    # 1.1 asked the taxonomy for the scientific names of codes it had kept without them: a group's has its subspecies.
    stored = Memory.new(TODAY).as_dict()
    stored["scientific"] = {"gwcspa": GAMBELII, "eurbla": "Turdus merula"}
    stored["past_years"] = {"2025": {"since": "2025-01-01", "first_seen": {"gwcspa": "2025-05-01"}}}
    memory = Memory.from_dict(stored)
    memory.initialized = True
    memory.learn(["gwcspa"], {"gwcspa": Taxon(GAMBELII, "White-crowned Sparrow (Gambel's)", "whcspa")})

    other = obs(species="nwcspa", name="White-crowned Sparrow (Nuttall's)", checklist="S900180", observed="2026-10-11 10:00", **SPARROW)
    events = remember(memory, [obs(checklist="S900181", observed="2026-10-10 10:00", **GROUP), other], [], TODAY, 30)

    # One species. The species itself wasn't seen, so the other group is taken for its new code until it is looked up,
    # as in test_a_group_taken_for_its_species_new_code_is_put_back_by_the_taxonomy.
    assert [event.kind for event in events] == [FIRST_OF_YEAR]
    assert len(memory.year_list) == 1
    memory.learn(memory.unknown(), {"nwcspa": Taxon("Zonotrichia leucophrys nuttalli", "White-crowned Sparrow (Nuttall's)", "whcspa")})
    assert memory.year_list == {"whcspa": "2026-10-10"}
    assert memory.past_years["2025"]["first_seen"] == {"whcspa": "2025-05-01"}


# The species, groups, form, intergrade, hybrid and bracketed group are eBird's names as its taxonomy gives them
# (checked on 2026-10-30). The spuhs and slashes are made-up names in the forms the integration has always read.
@pytest.mark.parametrize(
    ("scientific", "species"),
    [
        ("Zonotrichia leucophrys", "Zonotrichia leucophrys"),
        ("Zonotrichia leucophrys gambelii", "Zonotrichia leucophrys"),
        ("Motacilla alba alba/dukhunensis", "Motacilla alba"),
        ("Acanthis flammea flammea/rostrata", "Acanthis flammea"),
        ("Junco hyemalis [oreganus Group] x mearnsi", "Junco hyemalis"),
        ("Ammospiza nelsoni x caudacuta", None),
        ("Larinae sp.", None),
        ("Larus argentatus/smithsonianus", None),
        ("Junco hyemalis [oreganus Group]", "Junco hyemalis"),
        ("Larus argentatus/Chroicocephalus ridibundus", None),
        ("Anser/Branta sp.", None),
    ],
    ids=[
        "species",
        "group",
        "slashed group",
        "form",
        "intergrade",
        "hybrid",
        "spuh",
        "slash",
        "bracketed group",
        "slash across genera",
        "genus slash spuh",
    ],
)
def test_the_species_a_name_falls_under(scientific: str, species: str | None) -> None:
    assert is_species(scientific) == (species is not None)
    assert binomial(scientific) == (species or scientific), "a name that is no species is kept whole"


REDPOLL = {"scientific": "Acanthis flammea"}


def test_a_species_known_only_from_its_form_matches_its_next_form() -> None:
    memory = started(region=("redpol1",))
    form = obs(species="comred", name="Common Redpoll (flammea/rostrata)", checklist="S900190", observed="2026-10-04 10:00", **REDPOLL)
    remember(memory, [form], [], TODAY, 30)
    memory.learn(["comred"], {"comred": Taxon("Acanthis flammea flammea/rostrata", "Common Redpoll (flammea/rostrata)", "redpol1")})
    assert memory.scientific["redpol1"] == "Acanthis flammea"

    # One species, no first of the year or in the region. The species itself isn't seen, so the other form is taken for
    # its new code until it is looked up, the accepted case.
    other = obs(species="comred2", name="Common Redpoll (cabaret)", checklist="S900191", observed="2026-10-11 10:00", **REDPOLL)
    assert remember(memory, [form, other], [], TODAY, 30) == []
    assert len(memory.year_list) == 1
    memory.learn(memory.unknown(), {"comred2": Taxon("Acanthis flammea cabaret", "Common Redpoll (cabaret)", "redpol1")})
    assert memory.year_list == {"redpol1": "2026-10-04"}


def test_groups_follow_their_species_back_from_a_code_taken_for_its_new_one() -> None:
    # Two looked-up codes of a wagtail. A third code is taken for the species' new code while the species isn't seen
    # (the accepted case), and its lookup moves everything back, the other group's counts_as too.
    wagtail = {"scientific": "Motacilla flava"}
    memory = started(region=("eaywag1",))
    remember(
        memory,
        [
            obs(species="eaywag1", name="Western Yellow Wagtail", checklist="S900200", observed="2026-06-01 09:00", **wagtail),
            obs(species="weywag2", name="Western Yellow Wagtail (thunbergi)", checklist="S900201", observed="2026-06-01 10:00", **wagtail),
        ],
        [],
        date(2026, 6, 1),
        30,
    )
    memory.learn(
        ["eaywag1", "weywag2"],
        {
            "eaywag1": Taxon("Motacilla flava", "Western Yellow Wagtail", "eaywag1"),
            "weywag2": Taxon("Motacilla flava thunbergi", "Western Yellow Wagtail (thunbergi)", "eaywag1"),
        },
    )
    third = obs(species="weywag16", name="Western Yellow Wagtail (flava)", checklist="S900202", observed="2026-07-15 10:00", **wagtail)
    remember(memory, [third], [], date(2026, 7, 15), 30)
    memory.learn(memory.unknown(), {"weywag16": Taxon("Motacilla flava flava", "Western Yellow Wagtail (flava)", "eaywag1")})

    assert memory.year_list == {"eaywag1": "2026-06-01"}
    assert memory.counts_as["weywag2"] == "eaywag1"


@pytest.mark.parametrize("known_as", ["seen", "looked up", "looked up under an old genus"])
def test_a_group_of_a_species_in_the_region_is_no_first_record(known_as: str) -> None:
    # eBird's region list has the species' code, never its groups' (checked at a busy area on 2026-10-30).
    memory = started(region=("whcspa",))
    species = obs(checklist="S900210", observed="2026-10-01 10:00", **SPECIES)
    if known_as == "seen":
        remember(memory, [species], [], date(2026, 10, 1), 30)
    else:
        memory.learn(["gwcspa"], {"gwcspa": Taxon(GAMBELII, "White-crowned Sparrow (Gambel's)", "whcspa")})
    if known_as == "looked up under an old genus":
        # Only the taxonomy links them: the species' binomial isn't the group's.
        memory.scientific["whcspa"] = "Oldgenus leucophrys"

    group = obs(checklist="S900211", observed="2026-10-11 10:00", **GROUP)
    events = remember(memory, [species, group] if known_as == "seen" else [group], [], TODAY, 30)

    assert FIRST_IN_REGION not in [event.kind for event in events]


@pytest.mark.parametrize("polls", [1, 2], ids=["one poll", "two polls"])
@pytest.mark.parametrize("group_looked_up", [False, True], ids=["group new", "group looked up"])
@pytest.mark.parametrize("group_first", [True, False], ids=["group first", "species first"])
def test_a_species_new_to_the_region_is_announced_once_with_its_group(group_first: bool, group_looked_up: bool, polls: int) -> None:
    memory = started(region=("eurbla",))
    if group_looked_up:
        memory.learn(["gwcspa"], {"gwcspa": Taxon(GAMBELII, "White-crowned Sparrow (Gambel's)", "whcspa")})
    group = obs(checklist="S900213", observed="2026-10-10 10:00" if group_first else "2026-10-11 10:00", **GROUP)
    species = obs(checklist="S900214", observed="2026-10-11 10:00" if group_first else "2026-10-10 10:00", **SPECIES)
    first, second = (group, species) if group_first else (species, group)
    if polls == 1:
        events = remember(memory, [first, second], [], TODAY, 30)
    else:
        events = remember(memory, [first], [], TODAY, 30) + remember(memory, [first, second], [], TODAY, 30)
    assert [event.observation.species for event in events if event.kind == FIRST_IN_REGION] == [first.species]


def test_a_code_the_taxonomy_counts_as_no_species_is_no_first_record() -> None:
    # A name like a species', but the taxonomy counts the code as none.
    memory = started(region=("eurbla",))
    memory.learn(["oddcod1"], {"oddcod1": Taxon("Avis oddcod1", "Odd code", "")})
    events = remember(memory, [obs(species="oddcod1", scientific="Avis oddcod1", checklist="S900215")], [], TODAY, 30)
    assert events == []
    assert memory.year_list == {}


def test_a_group_of_a_species_never_recorded_in_the_region_is_a_first_record() -> None:
    memory = started(region=("eurbla",))
    [*_, event] = remember(memory, [obs(checklist="S900212", **GROUP)], [], TODAY, 30)
    assert (event.kind, event.observation.species) == (FIRST_IN_REGION, "gwcspa")


@pytest.mark.parametrize("looked_up", ["before", "before, one poll", "between the polls"])
@pytest.mark.parametrize("group_first", [True, False], ids=["group first", "species first"])
def test_a_species_announced_with_its_group_stays_announced_under_a_new_genus(group_first: bool, looked_up: str) -> None:
    # eBird's taxonomy update changes the species' genus between the two sightings, but keeps its codes. The group is
    # looked up before its first sighting, or as usual in a later day's extra call.
    memory = started(region=("eurbla",))
    gambelii = {"gwcspa": Taxon(GAMBELII, "White-crowned Sparrow (Gambel's)", "whcspa")}
    if looked_up.startswith("before"):
        memory.learn(["gwcspa"], gambelii)
    renamed = {"scientific": "Newgenus leucophrys"}
    first = obs(checklist="S900216", observed="2026-10-10 10:00", **(GROUP if group_first else SPECIES))
    later = {**(SPECIES if group_first else GROUP), **renamed}
    second = obs(checklist="S900217", observed="2026-10-11 10:00", **later)

    if looked_up == "before, one poll":
        events = remember(memory, [first, second], [], TODAY, 30)
    else:
        events = remember(memory, [first], [], TODAY, 30)
        if looked_up == "between the polls":
            memory.learn(["gwcspa"], gambelii)
        events += remember(memory, [second], [], TODAY, 30)

    assert [event.observation.species for event in events if event.kind == FIRST_IN_REGION] == [first.species]
