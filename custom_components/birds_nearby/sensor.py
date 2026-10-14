"""The sensors of an area: notable sightings, recent species, the year list and the map feed."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTRIBUTION, DOMAIN, MAP_FEED_VERSION
from .coordinator import BirdsConfigEntry, BirdsCoordinator
from .feed import features


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BirdsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([NotableSensor(coordinator), RecentSensor(coordinator), YearListSensor(coordinator), MapFeedSensor(coordinator)])


class BirdsSensor(CoordinatorEntity[BirdsCoordinator], SensorEntity):
    """What the sensors of an area share."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    # The lists change with every new sighting and can be long: only the counts go to the database.
    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(self, coordinator: BirdsCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="eBird",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://ebird.org",
        )


class NotableSensor(BirdsSensor):
    """The species among eBird's notable observations of the last 30 days, each sighting in the attributes."""

    _attr_icon = "mdi:bird"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BirdsCoordinator) -> None:
        super().__init__(coordinator, "notable")

    @property
    def native_value(self) -> int:
        return len({observation.species for observation in self.coordinator.data.notable})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "sightings": [
                {**self.coordinator.sighting(observation), "valid": observation.valid, "reviewed": observation.reviewed}
                for observation in self.coordinator.data.notable
            ]
        }


class RecentSensor(BirdsSensor):
    """The species seen in the recent days, with the newest sighting of each."""

    _attr_icon = "mdi:binoculars"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BirdsCoordinator) -> None:
        super().__init__(coordinator, "recent")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.recent)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "days": self.coordinator.recent_days,
            "species": [self.coordinator.sighting(observation) for observation in self.coordinator.data.recent],
        }


class YearListSensor(BirdsSensor):
    """Every species seen in the area this year, counted from installation in the first year."""

    _attr_icon = "mdi:format-list-checks"
    # Long term statistics draw the year list growing, and its drop back to zero each January.
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BirdsCoordinator) -> None:
        super().__init__(coordinator, "year_list")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.memory.year_list)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        memory = self.coordinator.memory
        newest_first = sorted(memory.year_list.items(), key=lambda item: item[1], reverse=True)
        last_year = memory.last_year
        return {
            "year": memory.year,
            "since": date.fromisoformat(memory.year_started),
            "species": [
                {
                    "species_code": code,
                    "name": memory.names.get(code, code),
                    "first_seen": date.fromisoformat(first),
                    "last_year": memory.last_year_first_seen(code),
                }
                for code, first in newest_first
            ],
            "last_year_since": date.fromisoformat(last_year["since"]) if last_year else None,
            "expected": [
                {"species_code": code, "name": memory.names.get(code, code), "last_year": first}
                for code, first in memory.expected(dt_util.now().date())
            ],
        }


class MapFeedSensor(BirdsSensor):
    """The sightings as a map feed for ha-map-card-plugin-map-feed: a point for each place birds were seen."""

    _attr_icon = "mdi:map-marker-multiple"

    def __init__(self, coordinator: BirdsCoordinator) -> None:
        super().__init__(coordinator, "map")
        # Built once per update, for both the state and the attributes.
        self._feed: list[dict[str, Any]] | None = None

    def _handle_coordinator_update(self) -> None:
        self._feed = None
        super()._handle_coordinator_update()

    def _features(self) -> list[dict[str, Any]]:
        if self._feed is None:
            self._feed = self._build_features()
        return self._feed

    def _build_features(self) -> list[dict[str, Any]]:
        data = self.coordinator.data
        # The notable sightings of the same recent days, so the map shows one span of time.
        notable = [item for item in data.notable if item.observed.date() >= data.since]
        return features(
            [*notable, *data.recent],
            {item.key for item in data.notable},
            self.coordinator.species,
            (self.coordinator.latitude, self.coordinator.longitude),
            self.coordinator.language,
            self.coordinator.recent_days,
            dt_util.now(),
        )

    @property
    def native_value(self) -> int:
        return sum(1 for feature in self._features() if feature["geometry"]["type"] == "Point")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        coordinator = self.coordinator
        return {
            "map_feed_version": MAP_FEED_VERSION,
            "area": {"center": [coordinator.latitude, coordinator.longitude], "radius_km": coordinator.radius_km},
            "updated": coordinator.data.updated.isoformat(timespec="seconds"),
            "geojson": {"type": "FeatureCollection", "features": self._features()},
        }
