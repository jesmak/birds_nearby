# Birds Nearby

A Home Assistant integration for bird sightings within a radius of your home: the notable ones, your year list and
first sightings of the year, and the sightings on a map. Sightings come from [eBird](https://ebird.org), species
pictures from Wikipedia and Wikimedia Commons.

> **Status: planning.** Nothing to install yet. This README is the project plan: what the integration will do, where
> its data comes from and how it treats the services it uses.

This is an unofficial integration, not affiliated with or endorsed by eBird or the Cornell Lab of Ornithology.

## What it will do

- **Notable nearby:** eBird's notable observations within the radius, meaning what eBird's regional filters and
  reviewers consider rare or out of season there. A sensor with the count and the list as attributes. Records not yet
  reviewed are marked as such.
- **Recent nearby:** the species seen within the radius in recent days, with the newest sighting of each.
- **Year list:** every species seen within the radius this year, as a sensor with long-term statistics.
- **First of the year:** an event when a species appears that isn't on this year's list yet.
- **Back after a while:** an event when a species that hasn't been seen within the radius for a set number of days
  appears again.
- **A map feed** for [ha-map-card](https://github.com/nathan-gs/ha-map-card) through
  [ha-map-card-plugin-map-feed](https://github.com/jesmak/ha-map-card-plugin-map-feed): notable sightings and the
  newest sighting of each species as points, with the species name, count, date and a picture.
- **Species names in Home Assistant's language**, where eBird has them, otherwise in English.

The integration fires events rather than notifications, so you decide in your own automations what deserves a beep.

### What it can't do

eBird's API looks back 30 days at most, so anything that needs a longer memory is counted from the day the
integration is set up. The year list and first sightings of the year start at installation, and the first year is
incomplete. On first setup the lists are filled from the last 30 days without firing any events.

The radius is at most 50 km, which is eBird's limit. Birds only.

## Data sources

### eBird

Sightings come from the [eBird API 2.0](https://documenter.getpostman.com/view/664302/S1ENwy59), using your own
API key.

- **Two requests per update:** recent observations and notable observations near your home. Every 30 minutes by
  default, never more often than every 15 minutes. That's about 100 requests a day.
- **Your location is rounded** to two decimals (about 1 km) before it is sent.
- **No observer names.** Only eBird's simple detail level is requested, which leaves them out.
- **Private locations stay approximate.** A sighting at a private location (often someone's garden) is shown on the
  map as a grid square, not as an exact point. Public hotspots are shown exactly.
- **Nothing is published or passed on.** The data stays in your own Home Assistant.
- **eBird is credited** with a link wherever its data is shown.

### Pictures

Each species' picture is the lead image of its English Wikipedia article, found through the eBird taxon ID on
Wikidata. Its author and licence come from Wikimedia Commons and are shown with the picture. Commons hosts only
freely licensed files. A picture is looked up once per species and cached.

## Getting an eBird API key

Every user needs an eBird API key of their own. eBird reviews requests by hand, so getting one can take a while.
Requests are made through eBird Data Access on the eBird website, signed in with your eBird account.

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

## License

MIT. The eBird data the integration shows is subject to eBird's terms, and each picture to its own licence on
Wikimedia Commons.
