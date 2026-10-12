"""Config flow: an area and the user's own eBird API key, a new key when eBird refuses it, and the options."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
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
    WINDOW_DAYS,
)
from .exceptions import EbirdAuthError, EbirdError

_LOGGER = logging.getLogger(__name__)

KEY_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

# eBird's region codes: a country (FI), its first level (FI-02) or a county (US-NY-109).
REGION_PATTERN = re.compile(r"^[A-Z]{2}(-[A-Z0-9]{1,3}){0,2}$")


def _number(minimum: int, maximum: int) -> NumberSelector:
    return NumberSelector(NumberSelectorConfig(min=minimum, max=maximum, step=1, mode=NumberSelectorMode.BOX))


class BirdsConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """An area around a point, home by default, and the user's eBird API key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            location = user_input[CONF_LOCATION]
            latitude, longitude = float(location["latitude"]), float(location["longitude"])
            radius_km = round(float(location.get("radius", DEFAULT_RADIUS_KM * 1000)) / 1000)
            if not 1 <= radius_km <= MAX_RADIUS_KM:
                errors[CONF_LOCATION] = "radius_out_of_range"
            else:
                await self.async_set_unique_id(f"{latitude:.2f}_{longitude:.2f}")
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
                vol.Required(
                    CONF_LOCATION,
                    default={
                        "latitude": self.hass.config.latitude,
                        "longitude": self.hass.config.longitude,
                        "radius": DEFAULT_RADIUS_KM * 1000,
                    },
                ): LocationSelector(LocationSelectorConfig(radius=True)),
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


class BirdsOptionsFlow(OptionsFlow):
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
        return self.async_show_form(
            step_id="init", data_schema=self.add_suggested_values_to_schema(schema, current), errors=errors
        )
