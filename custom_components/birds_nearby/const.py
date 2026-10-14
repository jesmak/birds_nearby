"""Constants for the Birds Nearby integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "birds_nearby"

ATTRIBUTION: Final = "Data provided by eBird.org (https://ebird.org)"

EBIRD_URL: Final = "https://api.ebird.org/v2"

# Wikimedia asks every client for a descriptive User-Agent with a way to reach its author.
USER_AGENT: Final = "BirdsNearby/1.1.2 (https://github.com/jesmak/birds_nearby; Home Assistant integration)"

# Config entry data.
CONF_API_KEY: Final = "api_key"
CONF_LOCATION: Final = "location"
CONF_RADIUS_KM: Final = "radius_km"

# Options.
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_RECENT_DAYS: Final = "recent_days"
CONF_BACK_DAYS: Final = "back_days"
CONF_REGION: Final = "region"

DEFAULT_NAME: Final = "Birds Nearby"
DEFAULT_RADIUS_KM: Final = 25
# eBird's own limit for searches around a point.
MAX_RADIUS_KM: Final = 50

# eBird gets a handful of checklists a day in a typical region, so polling more often
# mostly fetches the same answer again. Never below 15 minutes: a key used too hard is suspended.
DEFAULT_SCAN_MINUTES: Final = 60
MIN_SCAN_MINUTES: Final = 15
MAX_SCAN_MINUTES: Final = 1440

DEFAULT_RECENT_DAYS: Final = 7
DEFAULT_BACK_DAYS: Final = 30
MIN_BACK_DAYS: Final = 7
MAX_BACK_DAYS: Final = 365

# The furthest back eBird's API reaches.
WINDOW_DAYS: Final = 30

# The region's species list is fetched once a day.
REGION_REFRESH: Final = timedelta(days=1)

# Coordinates sent to eBird are rounded to this many decimals, about a kilometre.
REQUEST_DECIMALS: Final = 2

# Events fired on the event bus.
EVENT_NOTABLE: Final = f"{DOMAIN}_notable"
EVENT_FIRST_OF_YEAR: Final = f"{DOMAIN}_first_of_year"
EVENT_BACK: Final = f"{DOMAIN}_back"
EVENT_FIRST_IN_REGION: Final = f"{DOMAIN}_first_in_region"

MAP_FEED_VERSION: Final = 1
