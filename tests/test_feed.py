"""The map feed: places, their titles and popups."""

from __future__ import annotations

from datetime import datetime

from custom_components.birds_nearby.feed import TEXTS, _row, caption, clock, features, from_centre, opacity, short_time
from custom_components.birds_nearby.pictures import Picture, SpeciesInfo
from custom_components.birds_nearby.sightings import parse_observations

from .conftest import LATITUDE, LONGITUDE, observation


def test_species_at_the_same_place_are_one_point() -> None:
    observations = parse_observations(
        [
            observation(),
            observation(species="gretit1", name="Great Tit", checklist="S900003", observed="2026-10-11 09:00", count=None),
            observation(
                species="hoocro1",
                name="Hooded Crow",
                checklist="S900002",
                location="L900002",
                location_name="Backyard, Example Street 1",
                personal=True,
                latitude=60.9702,
                longitude=25.6411,
            ),
        ]
    )
    picture = Picture("https://upload.wikimedia.org/x.jpg", "https://commons.wikimedia.org/wiki/File:X.jpg", "A. Author", "CC BY 4.0")

    species = {"gretit1": SpeciesInfo(picture, "LC"), "hoocro1": SpeciesInfo(None, "VU")}

    result = features(observations, {"hoocro1/S900002"}, species, (LATITUDE, LONGITUDE), "fi", 7, datetime(2026, 10, 11, 18, 0))
    by_id = {feature["id"]: feature for feature in result}

    bay = by_id["location:L900001"]["properties"]
    assert by_id["location:L900001"]["geometry"]["coordinates"] == [25.6623, 60.9811]
    assert bay["name"] == "Example Bay"
    assert bay["badge"] == "2"
    assert bay["subtitle"] == "2 lajia · 0,2 km koilliseen"
    # Two days at the same place: each row has its own date. A species only noted as present has no count.
    assert bay["details"] == [
        {
            "label": "Great Tit",
            "value": "11.10. 09.00",
            "image": {"url": picture.url, "caption": "Great Tit · A. Author, CC BY 4.0"},
        },
        {"label": "Eurasian Blackbird", "value": "2 yksilöä · 10.10. 08.15"},
    ]
    assert "images" not in bay, "pictures are on the rows"
    assert bay["color"] == "#2e7d32"
    assert bay["opacity"] == 1.0, "a sighting today"
    assert bay["link"] == {"url": "https://ebird.org/hotspot/L900001", "label": "Havaintopaikka eBirdissä"}

    personal = by_id["location:L900002"]
    assert personal["geometry"]["coordinates"] == [25.6411, 60.9702], "drawn where it was reported"
    # Its own name is whatever the observer typed, so it is titled by where it is instead.
    assert personal["properties"]["name"] == "1,5 km lounaaseen"
    assert personal["properties"]["subtitle"] == "1 lajia · 10.10."
    assert personal["properties"]["details"] == [
        # One day: the date is in the subtitle and the row shows only the time.
        {"label": "Hooded Crow", "value": "2 yksilöä · 08.15 · huomionarvoinen, ei vielä tarkastettu · VU"}
    ]
    assert personal["properties"]["opacity"] == 0.9, "yesterday, of seven recent days"
    assert "link" not in personal["properties"], "a personal location has no public page"
    assert personal["properties"]["color"] == "#d84315", "a place with a notable sighting stands out"
    assert len(result) == 2


def test_places_fade_over_the_recent_days() -> None:
    now = datetime(2026, 10, 11, 0, 5)
    # Days, not hours: a checklist from late yesterday is a day old just after midnight.
    assert opacity(datetime(2026, 10, 11, 0, 1), now, 7) == 1.0
    assert opacity(datetime(2026, 10, 10, 23, 50), now, 7) == 0.9
    assert opacity(datetime(2026, 10, 5, 8, 0), now, 7) == 0.4
    assert opacity(datetime(2026, 9, 20, 8, 0), now, 7) == 0.4
    assert opacity(datetime(2026, 10, 9, 8, 0), now, 1) == 1.0, "nothing to fade over"


def test_distance_and_direction_from_the_centre() -> None:
    centre = (60.0, 25.0)
    assert from_centre(centre, 60.05, 25.0, "fi") == "5,6 km pohjoiseen"
    assert from_centre(centre, 60.0, 24.9, "en") == "5.6 km west"
    assert from_centre(centre, 59.97, 25.06, "fi") == "4,7 km kaakkoon"
    assert from_centre(centre, 60.0002, 25.0001, "fi") == "Alueen keskellä"


def test_times_in_each_language() -> None:
    [parsed] = parse_observations([observation(observed="2026-10-11 14:05")])
    [date_only] = parse_observations([observation(observed="2026-10-11")])
    assert short_time(parsed.observed, "fi") == "11.10. 14.05"
    assert short_time(parsed.observed, "en") == "11.10. 14:05"
    assert short_time(date_only.observed, "en") == "11.10."


def test_a_long_author_is_shortened_in_the_popup_only() -> None:
    author = "This picture was realized by A. Photographer by using a long lens on a tripod in the rain"
    picture = Picture("https://upload.wikimedia.org/x.jpg", "", author, "CC BY-SA 2.5")

    shortened = caption("mustarastas", picture)

    assert shortened.startswith("mustarastas · This picture was realized")
    assert shortened.endswith("…, CC BY-SA 2.5")
    assert len(shortened.split(" · ", 1)[1].rsplit(", ", 1)[0]) <= 60
    assert picture.credit == f"{author}, CC BY-SA 2.5", "the full credit is kept for the sensors and events"
    assert caption("varis", Picture("https://x", "", "", "Public domain")) == "varis · Public domain"


def test_counts_in_each_language() -> None:
    [one] = parse_observations([observation(count=1, observed="2026-10-11")])
    [many] = parse_observations([observation(count=140)])
    assert _row(one, False, None, True, TEXTS["fi"], "fi") == {"label": "Eurasian Blackbird", "value": "1 yksilö"}
    assert _row(many, False, None, True, TEXTS["en"], "en")["value"] == "140 birds · 08:15"


def test_only_threatened_statuses_are_shown_on_the_map() -> None:
    [one] = parse_observations([observation(count=1)])
    for status, shown in (
        ("LC", "1 bird · 08:15"),
        ("DD", "1 bird · 08:15"),
        ("NT", "1 bird · 08:15 · NT"),
        (None, "1 bird · 08:15"),
    ):
        assert _row(one, False, SpeciesInfo(None, status), True, TEXTS["en"], "en")["value"] == shown


def test_other_languages_get_the_english_formats() -> None:
    [parsed] = parse_observations([observation(observed="2026-10-11 14:05")])
    assert from_centre((60.0, 25.0), 60.05, 25.0, "de") == "5.6 km north"
    assert clock(parsed.observed, "de") == "14:05"
