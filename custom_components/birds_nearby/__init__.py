"""Birds Nearby: bird sightings from eBird within a radius of a point.

One config entry is one area. Its memory of what has been seen (the year list, when each
species was last seen, the observations already handled) is kept in the entry's own storage.
"""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import BirdsConfigEntry, BirdsCoordinator, memory_store

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: BirdsConfigEntry) -> bool:
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
    await memory_store(hass, entry.entry_id).async_remove()
