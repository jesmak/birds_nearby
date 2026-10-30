# Birds Nearby for Home Assistant

A Home Assistant integration for bird sightings within an area you choose, with the notable ones, your year list and
first sightings of the year, and the sightings on a map.

[![GitHub Release][releases-shield]][releases] [![GitHub Release Date][release-date-shield]][releases] [![HACS][hacs-shield]][hacs] [![License][license-shield]](LICENSE)

<img src="https://raw.githubusercontent.com/jesmak/birds_nearby/main/docs/images/dashboard-light.png#gh-light-mode-only" width="1280" alt="A dashboard around Tampere, with a map of eight places where birds were seen, older ones fainter, and the list of them beside it, the place with a notable sighting open to its six species with their pictures and tags. Beside it the year list and recent species counts, and lists of the notable sighting, the newest species of the year compared with last year and the species seen by this date last year but not yet">
<img src="https://raw.githubusercontent.com/jesmak/birds_nearby/main/docs/images/dashboard-dark.png#gh-dark-mode-only" width="1280" alt="A dashboard around Tampere, with a map of eight places where birds were seen, older ones fainter, and the list of them beside it, the place with a notable sighting open to its six species with their pictures and tags. Beside it the year list and recent species counts, and lists of the notable sighting, the newest species of the year compared with last year and the species seen by this date last year but not yet">

The sightings in the picture are made up. The species pictures are from Wikimedia Commons. The Citrine Wagtail is by
Ron Knight (CC BY 2.0), the Sedge Warbler by Charles J. Sharp (CC BY-SA 4.0), the Common Tern by MPF (CC BY-SA 4.0),
the Horned Grebe by Ekaterina Chernetsova (CC BY 2.0), the Great Crested Grebe by JJ Harrison (CC BY-SA 3.0) and the
Black-headed Gull by Hans Hillewaert (CC BY-SA 3.0).

## What is it?

Birds Nearby follows the bird sightings that birdwatchers report to [eBird](https://ebird.org) within a radius of a
point you choose, usually your home. It shows the species seen there in the last few days, and the notable ones,
meaning what eBird's regional filters and reviewers consider rare or out of season there. It keeps a year list of its
own and remembers earlier years, so from the second year each species' first sighting can be compared with last
year's, and you can see which species were here by this date last year but haven't been seen yet.

When something new turns up, it fires an event. That can be a notable sighting, a species' first sighting of the year, a
species back after a while, or the first record of a species in your county or region. Your own automations decide what
deserves a notification, and every event says how far away and in which direction the bird was seen.

The sightings are also a map feed for [map-feed-card](https://github.com/jesmak/map-feed-card). Each place birds were
seen is a point on the map, its details listing the species with their counts, times and pictures from Wikipedia. Species names follow
Home Assistant's language where eBird has them, otherwise they are in English.

### What it can't do

eBird's API looks back 30 days at most, so anything that needs a longer memory is counted from the day the
integration is set up. The first update fills the lists from the last 30 days without firing any events, and the
first year is incomplete. eBird gives only the newest sighting of each species, so the species already seen then are
on the year list without the day they were first seen. First sightings are compared with last year's only once a
year's list has run from 1 January.

When eBird updates its taxonomy, usually in October, some species get new codes. A species whose scientific name
stays the same is followed to its new code, with its year list date and history. One that also gets a new scientific
name, as after some splits, looks like a new species, and its first sighting under the new name is a first of the
year.

A subspecies group, such as Gambel's White-crowned Sparrow, counts as its species on the year list, as in eBird, and
so does a form or an intergrade that eBird counts as its species.
Spuhs ("gull sp."), slashes and hybrids count as no species, so they are on no year list and fire no first of the
year. A group seen before its species is the species' first of the year, under the group's name. Which species a
group belongs to comes from eBird's taxonomy, asked for every species new to the integration using the day's extra
call instead of the region's list, never two days in a row. Until then a group and its species count as one, since
they share a scientific name.

The radius is at most 50 km, which is eBird's limit. Birds only.

## Installation

You need an eBird API key first. See [Getting an eBird API key](#getting-an-ebird-api-key).

### With HACS

1. Add this repository to HACS custom repositories with type **Integration**
2. Search for Birds Nearby in HACS and download it
3. Restart Home Assistant
4. Add the integration in Settings › Devices & services

### Manual

1. Download the source code from the latest release
2. Copy the `custom_components/birds_nearby` folder to your Home Assistant installation's `config/custom_components`
   folder
3. Restart Home Assistant
4. Add the integration in Settings › Devices & services

### Getting an eBird API key

Every user needs an eBird API key of their own. Sign in with your eBird account, go to
[eBird Data Access](https://ebird.org/data/download) and request access to the API with the form below.

eBird's [data terms](https://www.birds.cornell.edu/home/ebird-data-access-terms-of-use/) let you use the data only
for the purpose you state in the request, so describe your use as it is. For a private person using this
integration at home, something like this:

- **Organization:** None
- **Project title:** Home Assistant: birds near my home
- **Project type:** General
- **Use cases:** Personal use
- **Licensing checkbox** (use exceeds limits or is commercial): leave it unticked.
- **Description:**

  > I use the open-source Home Assistant integration Birds Nearby (https://github.com/jesmak/birds_nearby) to see
  > recent and notable bird observations near my home in my own Home Assistant. This is personal, non-commercial use.
  > The data is shown only to me and my household and is not published or shared.

Don't share your key with anyone. eBird's [API terms](https://www.birds.cornell.edu/home/ebird-api-terms-of-use/)
make you responsible for everything done with it.

## Settings

Adding the integration asks for a name, your eBird API key and the area, which is a point on the map, your home by
default, and a radius around it. The key is checked with eBird before it is saved. Add the integration again for
another area, such as a summer cottage.

| Name          | Type     | Description                                       | Default      |
| ------------- | -------- | ------------------------------------------------- | ------------ |
| Name          | string   | The name of the area's device, and of its sensors | Birds Nearby |
| eBird API key | password | Your own key                                      |              |
| Area          | location | The centre and the radius, 1–50 km                | Home, 25 km  |

If eBird stops accepting the key, Home Assistant asks for a new one.

### Options

| Name                     | Type   | Description                                                                                                           | Default                  |
| ------------------------ | ------ | --------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| Update interval          | number | Minutes between updates, at least 15                                                                                  | 60                       |
| Recent days              | number | How many of the latest days the recent sensor and the map show, 1–30                                                  | 7                        |
| Back after               | number | A species unseen for this many days fires an event when it is seen again, 7–365                                       | 30                       |
| Region for first records | string | The eBird county or region a sighting is compared with, such as `US-NY-109` or `FI-02`. Empty turns first records off | From the nearest hotspot |

When the area is added, the region is taken from the nearest eBird hotspot. That is its county where eBird has
counties, otherwise its state or region (Finland has no counties in eBird, so a Finnish area gets a region such as
`FI-02`). Change it for a home near a border.

## Sensors

| Sensor                                | State                                                          | Attributes                                                           |
| ------------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------- |
| `sensor.birds_nearby_notable`         | Species among eBird's notable observations of the last 30 days | `sightings`: the newest notable sighting of each species (below)     |
| `sensor.birds_nearby_recent`          | Species seen in the recent days                                | `days`, and `species`: the newest sighting of each                   |
| `sensor.birds_nearby_year_list`       | Species seen this year                                         | `year`, `since`, `species`, `last_year_since` and `expected` (below) |
| `sensor.birds_nearby_sighting_places` | Places on the map                                              | The map feed                                                         |

The IDs come from the name given to the area and follow Home Assistant's language. In Finnish the year list is
`sensor.birds_nearby_vuosilista`. Use the ones your sensors have.

A sighting in the attributes has `species_code`, `name`, `scientific_name`, `count` (empty when the observer only
noted the species as present), `observed` (in the local time of the place), `location` (the hotspot's name, empty
for a personal location), `hotspot`, `distance_km` and `bearing` (from the area's centre, the bearing in degrees
clockwise from north), `direction` (the bearing as a word in Home Assistant's language, such as `southwest`),
`iucn_status` (the species' IUCN Red List category, such as `VU`), `url` (the species' page on eBird), and `picture`
and `picture_credit` once its picture has been found. `bearing` and `direction` are empty at the centre itself, and
`iucn_status` when Wikidata has no category for the species.

A notable sighting also has `reports`, how many checklists reported the species as notable in the last 30 days,
`valid` (false when eBird's reviewers rejected it) and `reviewed`.

The year list's `species` has each species' `first_seen` this year and `last_year`, the day it was first seen last
year, newest first. `first_seen` is empty for a species already seen when the integration was set up, and those come
last. `last_year_since` is the day last year's list started, which is later than 1 January in the year the
integration was set up. `expected` lists the species seen by this date last year but not yet this year, each with
its `last_year` date, the earliest first.

The attributes are left out of the recorder, so only the counts are kept in the history. The year list keeps long
term statistics, so a chart of it shows the list growing through the year and starting over in January.

## Events

| Event                          | Fired when                                                               |
| ------------------------------ | ------------------------------------------------------------------------ |
| `birds_nearby_notable`         | A notable observation the integration hasn't seen before                 |
| `birds_nearby_first_of_year`   | A species not yet on this year's list                                    |
| `birds_nearby_back`            | A species unseen for the set number of days. `days_unseen` says how long |
| `birds_nearby_first_in_region` | A species never recorded in the region before. `region` names it         |

The event data is a sighting as above, with `entry_id`, `notable` (whether it is among eBird's notable observations,
whatever the event) and `reviewed`. A notable sighting also has `first_in_region`, true when the same sighting is a
first record in the region and fires that event too, and `days_since_notable`, the days since the species was last among
the notable observations, empty when it hasn't been in the last month. The notable event fires for every new checklist
of a rarity, and these let an automation notify only once. A first of the year also has `last_year`, the day the species
was first seen last year, and `days_vs_last_year`, how many days later it is this year (negative when earlier).
`days_vs_last_year` is empty when last year's list didn't run from 1 January, since a first date then is often only the
day the list started. A sighting is new to the integration when its species and checklist are, since eBird gives no time
a record was added. Records reach the API only within 30 days of the sighting.

A notable sighting not yet reviewed fires `birds_nearby_notable` at once, with `reviewed` false. It goes on the year
list, and can be a first of the year or a first record in the region, only once eBird's reviewers have accepted it.
A report they reject is forgotten.

After a gap in the updates longer than "Back after", such as Home Assistant being off or eBird refusing the key, no
species counts as back on the first update, since any of them would look like it.

The first record in a region is compared with the region's species list from the day before, so the sighting itself
can't hide it. Spuhs ("gull sp."), slashes and hybrids are never first records. A subspecies group is one only when its
species is new to the region, since eBird's list has species, not their groups.

## The map

The map sensor is a map feed in the [Map Feed format](https://github.com/jesmak/map-feed-card/blob/main/docs/map-feed-format.md).
Draw it with [map-feed-card](https://github.com/jesmak/map-feed-card), as in the [examples](#the-sightings-on-a-map).

Each place birds were seen in the recent days is one point, its badge the number of species. Its details list the
species, newest first, with how many birds were counted and when, each with a small picture that opens large when
tapped. When every species at a place was seen on the same day, the date is shown once, under the title. A place
with a notable sighting is drawn in orange, its notable species listed first and tagged in the same orange. A species
near threatened or worse on the IUCN Red List is tagged with its category (`NT`, `VU`, `EN`, `CR` or `EW`), or has it
after its count when it is notable as well. The card's legend says what green and orange mean.

A place fades with the age of its newest sighting. It is drawn in full with a sighting today, and fainter each day
until the last of the recent days. A hotspot's details end with a link to its page on eBird.

In the card's list, the places can be sorted by their distance from the area's centre, nearest first, or by their
newest sighting. A hotspot's row shows its distance on the right.

Every place is drawn where it was reported. A hotspot, a public place shared by eBird's observers, is titled with its
name, with its distance and direction from the area's centre below it. A personal location, one an observer pinned
for themselves, is titled with its distance and direction instead ("3.2 km southwest"). Its own name is whatever
the observer typed, often an address, so it isn't shown.

## Examples

### A rarity nearby

```yaml
automation:
  - alias: A rarity nearby
    triggers:
      - trigger: event
        event_type: birds_nearby_notable
    actions:
      - action: notify.mobile_app_phone
        data:
          title: "{{ trigger.event.data.name }}"
          message: >
            {{ trigger.event.data.count or 'Some' }} at
            {{ trigger.event.data.location or 'a personal location' }}
            {{ '' if trigger.event.data.reviewed else '(not yet reviewed)' }}
            {{ trigger.event.data.distance_km }} km {{ trigger.event.data.direction or '' }}
```

### The first of the year close by, compared with last year

The phone notification shows the bird's picture.

```yaml
automation:
  - alias: First of the year, close by
    triggers:
      - trigger: event
        event_type: birds_nearby_first_of_year
    conditions:
      - condition: template
        value_template: "{{ trigger.event.data.distance_km < 5 }}"
    actions:
      - action: notify.mobile_app_phone
        data:
          title: "{{ trigger.event.data.name }}"
          message: >
            First this year
            {%- if trigger.event.data.days_vs_last_year is not none %},
            {{ trigger.event.data.days_vs_last_year | abs }}
            {{ 'day' if trigger.event.data.days_vs_last_year | abs == 1 else 'days' }}
            {{ 'later' if trigger.event.data.days_vs_last_year > 0 else 'earlier' }} than last year
            {%- endif %}
          data:
            image: "{{ trigger.event.data.picture }}"
```

### The sightings on a map

```yaml
type: custom:map-feed-card
title: Birds nearby
list: true
entities:
  - entity: sensor.birds_nearby_sighting_places
    show_area: true
```

## Upgrading from 1.2

Nothing is required. The year list's species up to the day the integration was set up lose their dates, which were
the newest sighting of each species in the 30 days before it, not the first. Over the next days the species in the
memory are looked up in eBird's taxonomy. Spuhs, slashes and hybrids then leave the year lists, and a subspecies
group listed beside its species merges into it. An automation reading `first_seen` should allow it to be empty.

## Upgrading from 1.1

The same as from 1.2, and the following. Show the sightings with [map-feed-card](https://github.com/jesmak/map-feed-card), which
replaces ha-map-card and its map feed plugin. The map feed's format is unchanged, so a map that reads it keeps
working.

The notable sensor's `sightings` lists each species once, its newest notable sighting, with `reports` saying how
many checklists reported it. A template that counted the list's items as reports should read `reports` instead.
Entity IDs, the year lists and everything else the integration remembers carry over.

## Data

This is an unofficial integration, not affiliated with or endorsed by eBird or the Cornell Lab of Ornithology. Every
user requests and enters an eBird API key of their own, and is bound by eBird's terms for it.

### eBird

Sightings come from the [eBird API 2.0](https://documenter.getpostman.com/view/664302/S1ENwy59), using your own
API key.

- **Two requests per update:** recent observations and notable observations within the area. Every 60 minutes by
  default and at least 15 minutes apart. An update asked for by hand or by an automation within 14 minutes of the
  last one shows the same data again without asking eBird. Starting Home Assistant and saving the options update at
  once. At the default interval that's about 50 requests a day, plus one a day for the list of species ever recorded in your county or region, or
  instead of it every other day, while species new to the integration are waiting, for their taxonomy. When eBird
  can't be reached, the sensors are unavailable until the next update, which comes at the usual interval.
- **Your location is rounded** to two decimals (about 1 km) before it is sent.
- **No observer names.** Only eBird's simple detail level is requested, which leaves them out.
- **Personal locations' names are never shown**, since they are often addresses.
- **Nothing is published or passed on.** The data stays in your own Home Assistant.
- **eBird is credited** in every sensor's attribution.

### Pictures

Each species' picture is the lead image of its English Wikipedia article, found through the eBird taxon ID on
Wikidata (or the scientific name, when eBird has renamed a code and Wikidata hasn't caught up). Its author and
licence come from Wikimedia Commons and are shown with the picture. Only files on Commons are used, and Commons
hosts only freely licensed files. A picture is looked up once per species, in the background, and kept. A species
without one is looked up again after Home Assistant restarts.

The IUCN Red List category comes from the same Wikidata item (property P141), the current assessment where it has
several. Wikidata's data is CC0.

## Translating

The integration's texts are in `custom_components/birds_nearby/translations/`, one JSON file per language, named by
its language code, such as `en.json` and `fi.json`. To add a language, copy `en.json` to the new language's code and
translate the values. The map popup's texts and the compass directions are in `TEXTS` and `DIRECTIONS` in
`custom_components/birds_nearby/feed.py`. Species names come from eBird in Home Assistant's language.

## Development

Requires Python 3.14.

```
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
.venv/bin/ruff check .
```

Test data is made up. eBird's terms don't allow passing its data on, so real responses are never copied into the
tests.

| Path                           | What it contains                                                              |
| ------------------------------ | ----------------------------------------------------------------------------- |
| `__init__.py`                  | Setup                                                                         |
| `config_flow.py`               | Adding an area, a new key, the options                                        |
| `api.py`                       | eBird's API                                                                   |
| `sightings.py`                 | Reading observations, the memory, and what counts as new                      |
| `pictures.py`                  | Finding a species' status and picture through Wikidata, Wikipedia and Commons |
| `coordinator.py`               | Updating, keeping the memory, firing events                                   |
| `feed.py`                      | The map feed                                                                  |
| `sensor.py`                    | The sensors                                                                   |
| `translations/<language>.json` | Home Assistant UI texts                                                       |

## Support

Hey dude! Help me out for a couple of :beers: or a :coffee:!

[![coffee](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)](https://www.buymeacoffee.com/jesmak)

## License

MIT. The eBird data the integration shows is subject to eBird's terms, and each picture to its own licence on
Wikimedia Commons.

[releases-shield]: https://img.shields.io/github/release/jesmak/birds_nearby.svg?style=for-the-badge
[release-date-shield]: https://img.shields.io/github/release-date/jesmak/birds_nearby?style=for-the-badge
[releases]: https://github.com/jesmak/birds_nearby/releases
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://hacs.xyz/docs/faq/custom_repositories/
[license-shield]: https://img.shields.io/github/license/jesmak/birds_nearby.svg?style=for-the-badge
