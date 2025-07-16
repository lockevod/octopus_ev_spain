"""The Octopus Energy Spain integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .api import OctopusSpainAPI
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_EMAIL,
    CONF_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
    SERVICE_START_BOOST,
    SERVICE_STOP_BOOST,
    SERVICE_REFRESH_CHARGER,
    SERVICE_CHECK_CHARGER,
    SERVICE_CAR_CONNECTED,
    SERVICE_CAR_DISCONNECTED,
    ATTR_DEVICE_ID,
    ATTR_NOTIFY,
)
from .coordinator import OctopusSpainDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schemas
START_BOOST_SERVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): cv.string,
})

STOP_BOOST_SERVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): cv.string,
})

REFRESH_CHARGER_SCHEMA = vol.Schema({})

CHECK_CHARGER_SCHEMA = vol.Schema({
    vol.Optional(ATTR_NOTIFY, default=True): cv.boolean,
})

CAR_CONNECTION_SCHEMA = vol.Schema({})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Octopus Energy Spain from a config entry."""
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    
    api = OctopusSpainAPI(email, password)
    
    try:
        # Test the connection
        login_success = await api.login()
        if not login_success:
            raise ConfigEntryAuthFailed("Invalid authentication")
            
        # Get accounts to verify API works
        viewer_info = await api.get_viewer_info()
        if not viewer_info.get("accounts"):
            raise ConfigEntryNotReady("No accounts found")
            
    except Exception as err:
        _LOGGER.error("Error connecting to Octopus Energy Spain API: %s", err)
        raise ConfigEntryNotReady from err

    # Create data update coordinator
    coordinator = OctopusSpainDataUpdateCoordinator(
        hass,
        _LOGGER,
        api,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Set up all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass, coordinator)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _get_single_charger_id(coordinator: OctopusSpainDataUpdateCoordinator) -> str | None:
    """Get the ID of the single EV charger in the account."""
    try:
        for account_number, account_devices in coordinator.data.get("devices", {}).items():
            for device in account_devices:
                if device.get("__typename") == "SmartFlexChargePoint":
                    device_id = device.get("id")
                    device_name = device.get("name", "Unknown")
                    _LOGGER.debug("Found EV charger: %s (ID: %s)", device_name, device_id)
                    return device_id
        
        _LOGGER.warning("No SmartFlexChargePoint found in any account")
        return None
        
    except Exception as err:
        _LOGGER.error("Error getting charger device ID: %s", err)
        return None


async def _async_register_services(hass: HomeAssistant, coordinator: OctopusSpainDataUpdateCoordinator) -> None:
    """Register services."""
    
    async def async_start_boost_charge(call: ServiceCall) -> None:
        """Start boost charging."""
        device_id = call.data[ATTR_DEVICE_ID]
        
        try:
            await coordinator.api.start_boost_charge(device_id)
            await coordinator.async_request_refresh()
            _LOGGER.info("Started boost charging for device %s", device_id)
        except Exception as err:
            _LOGGER.error("Failed to start boost charging for device %s: %s", device_id, err)
            raise

    async def async_stop_boost_charge(call: ServiceCall) -> None:
        """Stop boost charging."""
        device_id = call.data[ATTR_DEVICE_ID]
        
        try:
            await coordinator.api.stop_boost_charge(device_id)
            await coordinator.async_request_refresh()
            _LOGGER.info("Stopped boost charging for device %s", device_id)
        except Exception as err:
            _LOGGER.error("Failed to stop boost charging for device %s: %s", device_id, err)
            raise

    async def async_refresh_charger(call: ServiceCall) -> None:
        """Refresh the single EV charger data."""
        try:
            charger_device_id = await _get_single_charger_id(coordinator)
            if not charger_device_id:
                _LOGGER.warning("No EV charger found in account")
                return
                
            await coordinator.async_refresh_specific_device(charger_device_id)
            _LOGGER.info("Charger %s data refreshed successfully", charger_device_id)
        except Exception as err:
            _LOGGER.error("Failed to refresh charger data: %s", err)
            raise

    async def async_check_charger(call: ServiceCall) -> None:
        """Check charger status and optionally notify of changes."""
        notify = call.data.get(ATTR_NOTIFY, True)
        
        try:
            charger_device_id = await _get_single_charger_id(coordinator)
            if not charger_device_id:
                _LOGGER.warning("No EV charger found in account")
                return
            
            # Get current state
            current_device = await coordinator.async_get_device_data(charger_device_id)
            current_state = current_device.get("status", {}).get("currentState") if current_device else None
            current_status = current_device.get("status", {}).get("current") if current_device else None
            device_name = current_device.get("name", "EV Charger") if current_device else "EV Charger"
            
            # Refresh the charger
            await coordinator.async_refresh_specific_device(charger_device_id)
            
            # Get new state
            updated_device = await coordinator.async_get_device_data(charger_device_id)
            new_state = updated_device.get("status", {}).get("currentState") if updated_device else None
            new_status = updated_device.get("status", {}).get("current") if updated_device else None
            
            # Log the change
            _LOGGER.info("Charger check: %s | Status: %s → %s | State: %s → %s", 
                        device_name, current_status, new_status, current_state, new_state)
            
            # Notify if there are important changes
            if notify and (current_state != new_state or current_status != new_status):
                state_msg = f"State: {current_state} → {new_state}" if current_state != new_state else ""
                status_msg = f"Status: {current_status} → {new_status}" if current_status != new_status else ""
                
                message_parts = [msg for msg in [state_msg, status_msg] if msg]
                message = " | ".join(message_parts) if message_parts else "Status updated"
                
                # Determine icon based on state
                icon = "🔌"
                if new_state == "BOOSTING":
                    icon = "⚡"
                elif new_state == "SMART_CONTROL_IN_PROGRESS":
                    icon = "🔄"
                elif new_state == "SMART_CONTROL_NOT_AVAILABLE":
                    icon = "❌"
                
                hass.async_create_task(
                    hass.services.async_call(
                        "notify",
                        "persistent_notification",
                        {
                            "title": f"{icon} {device_name}",
                            "message": message,
                            "notification_id": f"charger_status_{charger_device_id}",
                        },
                    )
                )
                
            # Fire custom events for advanced automations
            hass.bus.async_fire("octopus_charger_checked", {
                "device_id": charger_device_id,
                "device_name": device_name,
                "old_state": current_state,
                "new_state": new_state,
                "old_status": current_status,
                "new_status": new_status,
                "state_changed": current_state != new_state,
                "status_changed": current_status != new_status,
            })
                
        except Exception as err:
            _LOGGER.error("Failed to check charger status: %s", err)
            raise

    async def async_car_connected(call: ServiceCall) -> None:
        """Handle car connection event."""
        try:
            _LOGGER.info("Car connection detected - refreshing charger status")
            
            # Immediate refresh
            await async_refresh_charger(call)
            
            # Wait a bit for connection to stabilize
            await asyncio.sleep(10)
            
            # Second check with notification
            await async_check_charger(ServiceCall("octopus_ev_spain", "check_charger", {ATTR_NOTIFY: True}))
            
            # Fire event for automations
            hass.bus.async_fire("octopus_car_connected")
            
        except Exception as err:
            _LOGGER.error("Failed to handle car connection: %s", err)
            raise

    async def async_car_disconnected(call: ServiceCall) -> None:
        """Handle car disconnection event."""
        try:
            _LOGGER.info("Car disconnection detected - refreshing charger status")
            
            # Immediate refresh
            await async_refresh_charger(call)
            
            # Fire event for automations
            hass.bus.async_fire("octopus_car_disconnected")
            
        except Exception as err:
            _LOGGER.error("Failed to handle car disconnection: %s", err)
            raise

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_BOOST,
        async_start_boost_charge,
        schema=START_BOOST_SERVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_BOOST,
        async_stop_boost_charge,
        schema=STOP_BOOST_SERVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_CHARGER,
        async_refresh_charger,
        schema=REFRESH_CHARGER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_CHARGER,
        async_check_charger,
        schema=CHECK_CHARGER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CAR_CONNECTED,
        async_car_connected,
        schema=CAR_CONNECTION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CAR_DISCONNECTED, 
        async_car_disconnected,
        schema=CAR_CONNECTION_SCHEMA,
    )
