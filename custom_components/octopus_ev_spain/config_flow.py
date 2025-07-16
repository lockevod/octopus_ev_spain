"""Config flow for Octopus Energy Spain integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import OctopusSpainAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_EMAIL): str,
    vol.Required(CONF_PASSWORD): str,
})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Octopus Energy Spain."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await self._validate_input(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Create unique ID based on email
                await self.async_set_unique_id(user_input[CONF_EMAIL])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=f"Octopus Energy ({info['email']})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _validate_input(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Validate the user input allows us to connect."""
        api = OctopusSpainAPI(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])

        try:
            login_success = await api.login()
            if not login_success:
                raise InvalidAuth
                
            # Try to get viewer info to verify the API works
            viewer_info = await api.get_viewer_info()
            if not viewer_info:
                raise CannotConnect
                
        except Exception as err:
            _LOGGER.error("Error validating Octopus Energy Spain credentials: %s", err)
            if "authentication" in str(err).lower() or "unauthorized" in str(err).lower():
                raise InvalidAuth from err
            raise CannotConnect from err

        return {
            "email": viewer_info.get("email", user_input[CONF_EMAIL]),
            "name": viewer_info.get("preferredName") or viewer_info.get("givenName", ""),
            "accounts_count": len(viewer_info.get("accounts", [])),
        }


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""