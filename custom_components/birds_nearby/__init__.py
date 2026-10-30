"""Birds Nearby: bird sightings from eBird within a radius of a point.

One config entry is one area. Its memory of what has been seen (the year list, when each
species was last seen, the observations already handled) is kept in the entry's own storage.
The Birds Nearby card comes with the integration, which serves it and adds it to the dashboards' resources.
"""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .card import async_add_card_resource, async_remove_card_resource, async_serve_card
from .const import DOMAIN
from .coordinator import BirdsConfigEntry, BirdsCoordinator, MemoryStore

PLATFORMS = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    await async_serve_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BirdsConfigEntry) -> bool:
    # Before eBird is asked, so the card is there to show it not answering.
    await async_add_card_resource(hass)
    coordinator = BirdsCoordinator(hass, entry)
    await coordinator.async_load()
    # Not the first refresh that fails setup: Home Assistant would retry setup within seconds, and keep calling
    # eBird every few minutes while it's down. The sensors are unavailable until the next update succeeds instead.
    await coordinator.async_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_save)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BirdsConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: BirdsConfigEntry) -> None:
    await MemoryStore(hass, entry).async_remove()
    await async_remove_card_resource(hass, entry)
