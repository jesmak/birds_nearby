"""Config flow: an area and the user's own eBird API key, a new key when eBird refuses it, a changed area, and the options."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    LocationSelector,
    LocationSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import EbirdClient
from .const import (
    CONF_API_KEY,
    CONF_BACK_DAYS,
    CONF_LOCATION,
    CONF_RADIUS_KM,
    CONF_RECENT_DAYS,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    DEFAULT_BACK_DAYS,
    DEFAULT_NAME,
    DEFAULT_RADIUS_KM,
    DEFAULT_RECENT_DAYS,
    DEFAULT_SCAN_MINUTES,
    DOMAIN,
    MAX_BACK_DAYS,
    MAX_RADIUS_KM,
    MAX_SCAN_MINUTES,
    MIN_BACK_DAYS,
    MIN_SCAN_MINUTES,
    REQUEST_DECIMALS,
    WINDOW_DAYS,
)
from .exceptions import EbirdAuthError, EbirdError

_LOGGER = logging.getLogger(__name__)

KEY_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

# eBird's region codes: a country (FI), its first level (FI-02) or a county (US-NY-109).
REGION_PATTERN = re.compile(r"^[A-Z]{2}(-[A-Z0-9]{1,3}){0,2}$")


def _number(minimum: int, maximum: int) -> NumberSelector:
    return NumberSelector(NumberSelectorConfig(min=minimum, max=maximum, step=1, mode=NumberSelectorMode.BOX))


def _area(location: dict[str, Any]) -> tuple[float, float, int]:
    """The centre and the radius in kilometres, from the map selector's value."""
    radius_km = round(float(location.get("radius", DEFAULT_RADIUS_KM * 1000)) / 1000)
    return float(location["latitude"]), float(location["longitude"]), radius_km


def _area_field(latitude: float, longitude: float, radius_km: int) -> dict[vol.Required, LocationSelector]:
    default = {"latitude": latitude, "longitude": longitude, "radius": radius_km * 1000}
    return {vol.Required(CONF_LOCATION, default=default): LocationSelector(LocationSelectorConfig(radius=True))}


def _unique_id(latitude: float, longitude: float) -> str:
    """The centre as it is sent to eBird: two areas with the same one would ask for the same sightings."""
    return f"{latitude:.{REQUEST_DECIMALS}f}_{longitude:.{REQUEST_DECIMALS}f}"


class BirdsConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """An area around a point, home by default, and the user's eBird API key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            latitude, longitude, radius_km = _area(user_input[CONF_LOCATION])
            if not 1 <= radius_km <= MAX_RADIUS_KM:
                errors[CONF_LOCATION] = "radius_out_of_range"
            else:
                await self.async_set_unique_id(_unique_id(latitude, longitude))
                self._abort_if_unique_id_configured()
                region, error = await self._check_key(user_input[CONF_API_KEY], latitude, longitude)
                if error:
                    errors["base"] = error
                else:
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data={
                            CONF_API_KEY: user_input[CONF_API_KEY],
                            "latitude": latitude,
                            "longitude": longitude,
                            CONF_RADIUS_KM: radius_km,
                        },
                        options={
                            CONF_SCAN_INTERVAL: DEFAULT_SCAN_MINUTES,
                            CONF_RECENT_DAYS: DEFAULT_RECENT_DAYS,
                            CONF_BACK_DAYS: DEFAULT_BACK_DAYS,
                            CONF_REGION: region or "",
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_API_KEY): KEY_SELECTOR,
                **_area_field(self.hass.config.latitude, self.hass.config.longitude, DEFAULT_RADIUS_KM),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input) if user_input else schema,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """eBird refused the key: ask for a new one."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            _, error = await self._check_key(user_input[CONF_API_KEY], entry.data["latitude"], entry.data["longitude"])
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_API_KEY: user_input[CONF_API_KEY]})

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): KEY_SELECTOR}),
            description_placeholders={"name": entry.title},
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Another centre or radius for the area. Its memory stays, and the coordinator takes the next poll without events.

        A moved centre gets its region for first records picked again, as the old one may be another county's.
        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            latitude, longitude, radius_km = _area(user_input[CONF_LOCATION])
            unique_id = _unique_id(latitude, longitude)
            other = self.hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, unique_id)
            if not 1 <= radius_km <= MAX_RADIUS_KM:
                errors[CONF_LOCATION] = "radius_out_of_range"
            elif other and other.entry_id != entry.entry_id:
                return self.async_abort(reason="already_configured")
            else:
                changes: dict[str, Any] = {
                    "unique_id": unique_id,
                    "data_updates": {"latitude": latitude, "longitude": longitude, CONF_RADIUS_KM: radius_km},
                }
                error = None
                if unique_id != _unique_id(entry.data["latitude"], entry.data["longitude"]):
                    region, error = await self._check_key(entry.data[CONF_API_KEY], latitude, longitude)
                    changes["options"] = {**entry.options, CONF_REGION: region or ""}
                if error:
                    errors["base"] = error
                else:
                    return self.async_update_reload_and_abort(entry, **changes, reload_even_if_entry_is_unchanged=False)

        current = user_input[CONF_LOCATION] if user_input else None
        area = _area(current) if current else (entry.data["latitude"], entry.data["longitude"], entry.data[CONF_RADIUS_KM])
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(_area_field(*area)),
            description_placeholders={"name": entry.title},
            errors=errors,
        )

    async def _check_key(self, api_key: str, latitude: float, longitude: float) -> tuple[str | None, str | None]:
        """The region of the nearest hotspot, and an error when the key doesn't work. One cheap call does both."""
        try:
            return await EbirdClient(self.hass, api_key).nearest_region(latitude, longitude), None
        except EbirdAuthError:
            return None, "invalid_auth"
        except EbirdError as err:
            _LOGGER.warning("Couldn't check the eBird API key: %s", err)
            return None, "cannot_connect"

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BirdsOptionsFlow:
        return BirdsOptionsFlow()


class BirdsOptionsFlow(OptionsFlowWithReload):
    """How often to poll, what counts as recent and as a while, and the region for first records."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            region = user_input.get(CONF_REGION, "").strip().upper()
            if region and not REGION_PATTERN.match(region):
                errors[CONF_REGION] = "invalid_region"
            else:
                return self.async_create_entry(
                    data={
                        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                        CONF_RECENT_DAYS: int(user_input[CONF_RECENT_DAYS]),
                        CONF_BACK_DAYS: int(user_input[CONF_BACK_DAYS]),
                        CONF_REGION: region,
                    }
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL): _number(MIN_SCAN_MINUTES, MAX_SCAN_MINUTES),
                vol.Required(CONF_RECENT_DAYS): _number(1, WINDOW_DAYS),
                vol.Required(CONF_BACK_DAYS): _number(MIN_BACK_DAYS, MAX_BACK_DAYS),
                vol.Optional(CONF_REGION): TextSelector(),
            }
        )
        current = {
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_MINUTES,
            CONF_RECENT_DAYS: DEFAULT_RECENT_DAYS,
            CONF_BACK_DAYS: DEFAULT_BACK_DAYS,
            **self.config_entry.options,
            **(user_input or {}),
        }
        return self.async_show_form(step_id="init", data_schema=self.add_suggested_values_to_schema(schema, current), errors=errors)
