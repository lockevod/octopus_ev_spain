"""Octopus Energy Spain integration for Home Assistant."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import OctopusSpainAPI
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .coordinator import OctopusSpainDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Octopus Energy Spain from a config entry."""
    _LOGGER.info("Setting up Octopus Energy Spain integration")
    
    # Get credentials from config entry
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    
    # Create API client
    api = OctopusSpainAPI(email, password)
    
    # Create coordinator
    coordinator = OctopusSpainDataUpdateCoordinator(
        hass,
        _LOGGER,
        api,
        DEFAULT_SCAN_INTERVAL,
    )
    
    # Initial data fetch
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        _LOGGER.error("Authentication failed during initial setup")
        return False
    except Exception as err:
        _LOGGER.error("Error during initial data fetch: %s", err)
        return False
    
    # Store coordinator in hass data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("Octopus Energy Spain integration setup completed successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Octopus Energy Spain integration")
    
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # If no more entries, remove domain data
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    
    _LOGGER.info("Octopus Energy Spain integration unloaded successfully")
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.info("Reloading Octopus Energy Spain integration")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)