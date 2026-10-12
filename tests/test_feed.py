"""The map feed: places, their titles and popups."""

from __future__ import annotations

from custom_components.birds_nearby.feed import features, from_centre, short_time
from custom_components.birds_nearby.pictures import Picture
from custom_components.birds_nearby.sightings import parse_observations

from .conftest import LATITUDE, LONGITUDE, observation


def test_species_at_the_same_place_are_one_point() -> None:
    observations = parse_observations(
        [
            observation(),
            observation(
                species="gretit1", name="Great Tit", checklist="S900003", observed="2026-10-11 09:00", count=None
            ),
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
    picture = Picture(
        "https://upload.wikimedia.org/x.jpg", "https://commons.wikimedia.org/wiki/File:X.jpg", "A. Author", "CC BY 4.0"
    )

    result = features(observations, {"hoocro1/S900002"}, {"gretit1": picture}, (LATITUDE, LONGITUDE), "fi")
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

    personal = by_id["location:L900002"]
    assert personal["geometry"]["coordinates"] == [25.6411, 60.9702], "drawn where it was reported"
    # Its own name is whatever the observer typed, so it is titled by where it is instead.
    assert personal["properties"]["name"] == "1,5 km lounaaseen"
    assert personal["properties"]["subtitle"] == "1 lajia · 10.10."
    assert personal["properties"]["details"] == [
        # One day: the date is in the subtitle and the row shows only the time.
        {"label": "Hooded Crow", "value": "2 yksilöä · 08.15 · huomionarvoinen, ei vielä tarkastettu"}
    ]
    assert personal["properties"]["color"] == "#d84315", "a place with a notable sighting stands out"
    assert len(result) == 2


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
    from custom_components.birds_nearby.feed import caption

    author = "This picture was realized by A. Photographer by using a long lens on a tripod in the rain"
    picture = Picture("https://upload.wikimedia.org/x.jpg", "", author, "CC BY-SA 2.5")

    shortened = caption("mustarastas", picture)

    assert shortened.startswith("mustarastas · This picture was realized")
    assert shortened.endswith("…, CC BY-SA 2.5")
    assert len(shortened.split(" · ", 1)[1].rsplit(", ", 1)[0]) <= 60
    assert picture.credit == f"{author}, CC BY-SA 2.5", "the full credit is kept for the sensors and events"
    assert caption("varis", Picture("https://x", "", "", "Public domain")) == "varis · Public domain"


def test_counts_in_each_language() -> None:
    from custom_components.birds_nearby.feed import TEXTS, _row

    [one] = parse_observations([observation(count=1, observed="2026-10-11")])
    [many] = parse_observations([observation(count=140)])
    assert _row(one, False, None, True, TEXTS["fi"], "fi") == {"label": "Eurasian Blackbird", "value": "1 yksilö"}
    assert _row(many, False, None, True, TEXTS["en"], "en")["value"] == "140 birds · 08:15"
