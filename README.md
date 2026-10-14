# Birds Nearby for Home Assistant

A Home Assistant integration for bird sightings within a radius of your home, with the notable ones, your year list
and first sightings of the year, and the sightings on a map. Sightings come from [eBird](https://ebird.org), species
pictures from Wikipedia and Wikimedia Commons.

[![GitHub Release][releases-shield]][releases] [![GitHub Release Date][release-date-shield]][releases]

[![HACS][hacs-shield]][hacs] [![Home Assistant][home-assistant-shield]][home-assistant] [![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield] [![GitHub Activity][commits-shield]][commits] [![Open bugs][bugs-shield]][bugs] [![Open enhancements][enhancements-shield]][enhancements]

This is an unofficial integration, not affiliated with or endorsed by eBird or the Cornell Lab of Ornithology. Every
user requests and enters an eBird API key of their own, and is bound by eBird's terms for it. If eBird objects to
the integration, it will be withdrawn.

## Support

Hey dude! Help me out for a couple of :beers: or a :coffee:!

[![coffee](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)](https://www.buymeacoffee.com/jesmak)

## What is it?

- **Notable nearby:** eBird's notable observations within the radius, meaning what eBird's regional filters and
  reviewers consider rare or out of season there. Records not yet reviewed are marked as such.
- **Recent nearby:** the species seen within the radius in the last few days, with the newest sighting of each.
- **Year list:** every species seen within the radius this year, as a sensor with long term statistics. From the
  second year, each species' first date last year, and the species seen by this date last year but not yet this
  year.
- **Events** for a notable sighting, a species' first sighting of the year, a species back after a while, and the
  first record of a species in your county or region. You decide in your own automations what deserves a
  notification.
- **A map feed** for [ha-map-card](https://github.com/nathan-gs/ha-map-card) through
  [ha-map-card-plugin-map-feed](https://github.com/jesmak/ha-map-card-plugin-map-feed): a point for each place birds
  were seen, listing the species with their counts, dates and pictures. Older places fade.
- **Species names in Home Assistant's language**, where eBird has them, otherwise in English.

### What it can't do

eBird's API looks back 30 days at most, so anything that needs a longer memory is counted from the day the
integration is set up. The year list and first sightings of the year start at installation, and the first year is
incomplete. The first update fills the lists from the last 30 days without firing any events. First sightings are
compared with last year's only once a year's list has run from 1 January.

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

## Settings

Adding the integration asks for a name, your eBird API key and the area, which is a point on the map, your home by
default, and a radius around it. The key is checked with eBird before it is saved. Add the integration again for
another area, such as a summer cottage.

| Name         | Type     | Description                                                     | Default      |
| ------------ | -------- | --------------------------------------------------------------- | ------------ |
| Name         | string   | The name of the area's device, and of its sensors               | Birds Nearby |
| eBird API key| password | Your own key                                                    |              |
| Area         | location | The centre and the radius, 1–50 km                               | Home, 25 km  |

If eBird stops accepting the key, Home Assistant asks for a new one.

### Options

| Name                     | Description                                                                                    | Default |
| ------------------------ | ---------------------------------------------------------------------------------------------- | ------- |
| Update interval          | Minutes between updates, at least 15                                                           | 60      |
| Recent days              | How many of the latest days the recent sensor and the map show, 1–30                           | 7       |
| Back after               | A species unseen for this many days fires an event when it is seen again, 7–365               | 30      |
| Region for first records | The eBird county or region a sighting is compared with, such as `US-NY-109` or `FI-02`. Empty turns first records off | From the nearest hotspot |

When the area is added, the region is taken from the nearest eBird hotspot. That is its county where eBird has
counties, otherwise its state or region (Finland has no counties in eBird, so a Finnish area gets a region such as
`FI-02`). Change it for a home near a border.

## Sensors

| Sensor                                | State                                                          | Attributes                                                           |
| ------------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------- |
| `sensor.birds_nearby_notable`         | Species among eBird's notable observations of the last 30 days | `sightings`: each notable observation, with `valid` and `reviewed`   |
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

The year list's `species` has each species' `first_seen` this year and `last_year`, the day it was first seen last
year. `last_year_since` is the day last year's list started, which is later than 1 January in the year the
integration was set up. `expected` lists the species seen by this date last year but not yet this year, each with
its `last_year` date, the earliest first.

The attributes are left out of the recorder, so only the counts are kept in the history. The year list keeps long
term statistics, so a chart of it shows the list growing through the year and starting over in January.

## Events

| Event                          | Fired when                                                                  |
| ------------------------------ | --------------------------------------------------------------------------- |
| `birds_nearby_notable`         | A notable observation the integration hasn't seen before                    |
| `birds_nearby_first_of_year`   | A species not yet on this year's list                                       |
| `birds_nearby_back`            | A species unseen for the set number of days. `days_unseen` says how long    |
| `birds_nearby_first_in_region` | A species never recorded in the region before. `region` names it            |

The event data is a sighting as above, with `entry_id`, `notable` and `reviewed`. A first of the year also has
`last_year`, the day the species was first seen last year, and `days_vs_last_year`, how many days later it is this
year (negative when earlier). `days_vs_last_year` is empty when last year's list didn't run from 1 January, since
a first date then is often only the day the list started. A sighting is new to the
integration when its species and checklist are, since eBird gives no time a record was added. Records reach the API
only within 30 days of the sighting.

The first record in a region is compared with the region's species list from the day before, so the sighting itself
can't hide it. Spuhs ("gull sp."), slashes and hybrids are never first records.

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
            {{ trigger.event.data.days_vs_last_year | abs }} days
            {{ 'later' if trigger.event.data.days_vs_last_year > 0 else 'earlier' }} than last year
            {%- endif %}
          data:
            image: "{{ trigger.event.data.picture }}"
```

## The map

The map sensor is a map feed in the [Map Feed format](https://github.com/jesmak/ha-map-card-plugin-map-feed/blob/main/docs/map-feed-format.md).
Draw it with ha-map-card and the map feed plugin:

```yaml
type: custom:map-card
title: Birds nearby
plugins:
  - name: Birds
    hacs:
      module: ha-map-card-plugin-map-feed
      file: ha-map-card-plugin-map-feed.js
    options:
      entity: sensor.birds_nearby_sighting_places
      show_area: true
```

Each place birds were seen in the recent days is one point, its badge the number of species. The popup lists the
species, newest first, with how many birds were counted and when, each with a small picture that opens large when
tapped. When every species at a place was seen on the same day, the date is shown once, under the title. A place
with a notable sighting is drawn in orange, its notable species listed first. A species near threatened or worse on
the IUCN Red List has its category after it (`NT`, `VU`, `EN`, `CR` or `EW`).

A place fades with the age of its newest sighting. It is drawn in full with a sighting today, and fainter each day
until the last of the recent days. A hotspot's popup ends with a link to its page on eBird. Fading and the link need version
1.2 of the map feed plugin, and the pictures 1.1. Older versions leave them out.

Every place is drawn where it was reported. A hotspot, a public place shared by eBird's observers, is titled with its
name, with its distance and direction from the area's centre below it. A personal location, one an observer pinned
for themselves, is titled with its distance and direction instead ("3.2 km southwest"). Its own name is whatever
the observer typed, often an address, so it isn't shown.

## Getting an eBird API key

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

## Data

### eBird

Sightings come from the [eBird API 2.0](https://documenter.getpostman.com/view/664302/S1ENwy59), using your own
API key.

- **Two requests per update:** recent observations and notable observations within the area. Every 60 minutes by
  default, never more often than every 15 minutes. That's about 50 requests a day, plus one a day for the list of
  species ever recorded in your county or region.
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

## License

MIT. The eBird data the integration shows is subject to eBird's terms, and each picture to its own licence on
Wikimedia Commons.

[releases-shield]: https://img.shields.io/github/release/jesmak/birds_nearby.svg?style=for-the-badge
[release-date-shield]: https://img.shields.io/github/release-date/jesmak/birds_nearby?style=for-the-badge
[releases]: https://github.com/jesmak/birds_nearby/releases
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://hacs.xyz/docs/faq/custom_repositories/
[home-assistant-shield]: https://img.shields.io/badge/Home%20Assistant-UI%20setup-green.svg?style=for-the-badge
[home-assistant]: https://www.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/jesmak/birds_nearby.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/maintenance/yes/2026.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/jesmak/birds_nearby.svg?style=for-the-badge
[commits]: https://github.com/jesmak/birds_nearby/commits/main
[bugs-shield]: https://img.shields.io/github/issues/jesmak/birds_nearby/bug?style=for-the-badge&label=bugs&color=red
[bugs]: https://github.com/jesmak/birds_nearby/labels/bug
[enhancements-shield]: https://img.shields.io/github/issues/jesmak/birds_nearby/enhancement?style=for-the-badge&label=enhancements&color=blue
[enhancements]: https://github.com/jesmak/birds_nearby/labels/enhancement
