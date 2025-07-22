"""The Octopus Energy Spain integration - SIMPLIFIED."""
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
    SERVICE_SET_PREFERENCES,
    ATTR_DEVICE_ID,
    ATTR_NOTIFY,
    ATTR_MAX_PERCENTAGE,
    ATTR_TARGET_TIME,
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

SET_PREFERENCES_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_ID): cv.string,
    vol.Optional(ATTR_MAX_PERCENTAGE, default=95): vol.All(vol.Coerce(float), vol.Range(min=10, max=100)),
    vol.Optional(ATTR_TARGET_TIME, default="10:30"): cv.string,
})


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
            
        # Verify API works by getting viewer info
        viewer_info = await api.get_viewer_info()
        _LOGGER.info("Connected to Octopus Energy Spain for user: %s", viewer_info.get("email"))
        
        if not viewer_info.get("accounts"):
            raise ConfigEntryNotReady("No accounts found")
            
    except Exception as err:
        _LOGGER.error("Error connecting to Octopus Energy Spain API: %s", err)
        raise ConfigEntryNotReady from err

    # Create data update coordinator - SIMPLIFIED with single interval
    coordinator = OctopusSpainDataUpdateCoordinator(
        hass,
        _LOGGER,
        api,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )
    
    # Store entry_id for device registration
    coordinator.entry_id = entry.entry_id

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("Initial data loaded for %d accounts", len(coordinator.accounts))

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Set up all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass, coordinator)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
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
            _LOGGER.info("Started boost charging for device %s", device_id)
            
            # Wait and refresh
            await asyncio.sleep(3)
            await coordinator.async_refresh_specific_device(device_id)
            
        except Exception as err:
            _LOGGER.error("Failed to start boost charging for device %s: %s", device_id, err)
            raise

    async def async_stop_boost_charge(call: ServiceCall) -> None:
        """Stop boost charging."""
        device_id = call.data[ATTR_DEVICE_ID]
        
        try:
            await coordinator.api.stop_boost_charge(device_id)
            _LOGGER.info("Stopped boost charging for device %s", device_id)
            
            # Wait and refresh
            await asyncio.sleep(3)
            await coordinator.async_refresh_specific_device(device_id)
            
        except Exception as err:
            _LOGGER.error("Failed to stop boost charging for device %s: %s", device_id, err)
            raise

    async def async_refresh_charger(call: ServiceCall) -> None:
        """Refresh the single EV charger data."""
        try:
            charger_device_id = await _get_single_charger_id(coordinator)
            if not charger_device_id:
                _LOGGER.warning("No EV charger found, doing full refresh")
                await coordinator.async_request_refresh()
                return
                
            await coordinator.async_refresh_specific_device(charger_device_id)
            _LOGGER.info("Charger %s data refreshed successfully", charger_device_id)
            
        except Exception as err:
            _LOGGER.error("Failed to refresh charger data: %s", err)
            raise

    async def async_check_charger(call: ServiceCall) -> None:
        """Check charger status and notify of changes."""
        notify = call.data.get(ATTR_NOTIFY, True)
        
        try:
            charger_device_id = await _get_single_charger_id(coordinator)
            if not charger_device_id:
                _LOGGER.warning("No EV charger found in account")
                return
            
            # Get current state before refresh
            current_device = await coordinator.async_get_device_data(charger_device_id)
            current_state = current_device.get("status", {}).get("currentState") if current_device else None
            device_name = current_device.get("name", "EV Charger") if current_device else "EV Charger"
            
            # Refresh the charger
            await coordinator.async_refresh_specific_device(charger_device_id)
            
            # Get new state after refresh
            new_device = await coordinator.async_get_device_data(charger_device_id)
            new_state = new_device.get("status", {}).get("currentState") if new_device else None
            
            # Log the change
            _LOGGER.info("Charger check: %s | State: %s → %s", device_name, current_state, new_state)
            
            # Notify if there are changes and notifications enabled
            if notify and current_state != new_state:
                state_translations = {
                    "SMART_CONTROL_NOT_AVAILABLE": "Desconectado",
                    "SMART_CONTROL_CAPABLE": "Conectado",
                    "BOOSTING": "Carga Rápida",
                    "SMART_CONTROL_IN_PROGRESS": "Carga Programada"
                }
                
                old_translated = state_translations.get(current_state, current_state or "Desconocido")
                new_translated = state_translations.get(new_state, new_state or "Desconocido")
                
                message = f"Estado cambió: {old_translated} → {new_translated}"
                
                # Add planned dispatches info
                dispatches_count = coordinator.get_planned_dispatches_count(charger_device_id)
                if new_state in ["SMART_CONTROL_CAPABLE", "BOOSTING", "SMART_CONTROL_IN_PROGRESS"]:
                    message += f" | {dispatches_count} sesiones programadas"
                
                # Determine icon
                icon = "🔌"
                if new_state == "BOOSTING":
                    icon = "⚡"
                elif new_state == "SMART_CONTROL_IN_PROGRESS":
                    icon = "🔄"
                elif new_state == "SMART_CONTROL_NOT_AVAILABLE":
                    icon = "❌"
                elif new_state == "SMART_CONTROL_CAPABLE":
                    icon = "✅"
                
                # FIXED: Use persistent_notification.create instead of notify.persistent_notification
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": f"{icon} {device_name}",
                        "message": message,
                        "notification_id": f"charger_status_{charger_device_id}",
                    },
                )
                
            # Fire custom event for automations
            hass.bus.async_fire("octopus_charger_checked", {
                "device_id": charger_device_id,
                "device_name": device_name,
                "old_state": current_state,
                "new_state": new_state,
                "state_changed": current_state != new_state,
                "is_connected": new_state in ["SMART_CONTROL_CAPABLE", "BOOSTING", "SMART_CONTROL_IN_PROGRESS"],
                "planned_dispatches_count": coordinator.get_planned_dispatches_count(charger_device_id),
            })
                
        except Exception as err:
            _LOGGER.error("Failed to check charger status: %s", err)
            raise

    async def async_car_connected(call: ServiceCall) -> None:
        """Handle car connection event."""
        try:
            _LOGGER.info("Car connection detected - refreshing charger status")
            await async_refresh_charger(call)
            
            # Wait for connection to stabilize
            await asyncio.sleep(10)
            await async_check_charger(ServiceCall("octopus_ev_spain", "check_charger", {ATTR_NOTIFY: True}))
            
            hass.bus.async_fire("octopus_car_connected")
            
        except Exception as err:
            _LOGGER.error("Failed to handle car connection: %s", err)
            raise

    async def async_car_disconnected(call: ServiceCall) -> None:
        """Handle car disconnection event."""
        try:
            _LOGGER.info("Car disconnection detected - refreshing charger status")
            await async_refresh_charger(call)
            hass.bus.async_fire("octopus_car_disconnected")
            
        except Exception as err:
            _LOGGER.error("Failed to handle car disconnection: %s", err)
            raise

    async def async_set_preferences(call: ServiceCall) -> None:
        """Set charger preferences."""
        device_id = call.data[ATTR_DEVICE_ID]
        max_percentage = call.data.get(ATTR_MAX_PERCENTAGE, 95)
        target_time = call.data.get(ATTR_TARGET_TIME, "10:30")
        
        try:
            # Create schedules for all days of the week
            days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
            schedules = []
            
            for day in days:
                schedules.append({
                    "dayOfWeek": day,
                    "time": target_time,
                    "max": float(max_percentage)
                })
            
            # Set preferences
            await coordinator.api.set_smart_flex_device_preferences(
                device_id=device_id,
                mode="CHARGE",
                unit="PERCENTAGE", 
                schedules=schedules
            )
            
            _LOGGER.info("Updated preferences for device %s: %s%% at %s", device_id, max_percentage, target_time)
            
            # Refresh device data
            await asyncio.sleep(2)
            await coordinator.async_refresh_specific_device(device_id)
            
            # Get device name for notification
            device_data = await coordinator.async_get_device_data(device_id)
            device_name = device_data.get("name", "Cargador EV") if device_data else "Cargador EV"
            
            # FIXED: Use persistent_notification.create
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": f"⚙️ {device_name}",
                    "message": f"Preferencias actualizadas: {max_percentage}% a las {target_time}",
                    "notification_id": f"charger_preferences_{device_id}",
                },
            )
            
            hass.bus.async_fire("octopus_preferences_updated", {
                "device_id": device_id,
                "device_name": device_name,
                "max_percentage": max_percentage,
                "target_time": target_time,
            })
            
        except Exception as err:
            _LOGGER.error("Failed to set preferences for device %s: %s", device_id, err)
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

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PREFERENCES,
        async_set_preferences,
        schema=SET_PREFERENCES_SCHEMA,
    )