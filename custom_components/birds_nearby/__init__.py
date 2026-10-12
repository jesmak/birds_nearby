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
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    return True


async def async_update_listener(hass: HomeAssistant, entry: BirdsConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: BirdsConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: BirdsConfigEntry) -> None:
    await memory_store(hass, entry.entry_id).async_remove()
