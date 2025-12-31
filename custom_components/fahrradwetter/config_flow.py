"""Config flow for Fahrradwetter integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import (
    DOMAIN,
    CONF_LOCAL_TEMP_ENTITY,
    CONF_LOCAL_WIND_ENTITY,
    CONF_LOCAL_RAIN_ENTITY,
)

_LOGGER = logging.getLogger(__name__)


class FahrradwetterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Fahrradwetter."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Initial step – local sensors only (safe baseline)."""

        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                errors[CONF_LOCAL_TEMP_ENTITY] = "required"
            else:
                # ✅ Lat/Lon automatisch aus HA übernehmen
                user_input["latitude"] = self.hass.config.latitude
                user_input["longitude"] = self.hass.config.longitude

                _LOGGER.debug(
                    "Fahrradwetter configured with HA location: %s / %s",
                    self.hass.config.latitude,
                    self.hass.config.longitude,
                )

                return self.async_create_entry(
                    title="Fahrradwetter",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_LOCAL_TEMP_ENTITY): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_LOCAL_WIND_ENTITY): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_LOCAL_RAIN_ENTITY): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )