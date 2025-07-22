"""Select platform for Octopus Energy Spain - HORA OBJETIVO COMO DESPLEGABLE."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_MAX_PERCENTAGE, DAYS_OF_WEEK
from .coordinator import OctopusSpainDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Valid time options (04:00 to 11:00 in 30-minute steps)
VALID_TIME_OPTIONS = [
    "04:00", "04:30", "05:00", "05:30", "06:00", "06:30",
    "07:00", "07:30", "08:00", "08:30", "09:00", "09:30", 
    "10:00", "10:30", "11:00"
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Octopus Energy Spain select entities."""
    coordinator: OctopusSpainDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[SelectEntity] = []

    # Add time select entities for each charger
    for account_number, devices in coordinator.data.get("devices", {}).items():
        for device in devices:
            if device.get("__typename") == "SmartFlexChargePoint":
                device_id = device["id"]
                entities.append(
                    OctopusChargerTargetTimeSelect(coordinator, account_number, device_id)
                )

    async_add_entities(entities)


def _safe_device_info(device_id: str, device: dict[str, Any] | None) -> dict[str, Any]:
    """Safely create device info."""
    if not device:
        return {
            "identifiers": {(DOMAIN, device_id)},
            "name": "Dispositivo Desconocido",
            "manufacturer": "Lockevod",
            "model": "Desconocido",
        }
        
    return {
        "identifiers": {(DOMAIN, device_id)},
        "name": device.get("name", "Dispositivo Desconocido"),
        "manufacturer": "Lockevod",
        "model": f"{device.get('__typename', 'Desconocido')} ({device.get('provider', 'Desconocido')})",
        "sw_version": device.get("deviceType", "Desconocido"),
    }


class OctopusChargerTargetTimeSelect(CoordinatorEntity, SelectEntity):
    """Select entity for charger target time configuration - DROPDOWN."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        device_id: str,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._account_number = account_number
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Charger") if device else "Charger"
        self._attr_name = f"{device_name} Target Time"
        self._attr_unique_id = f"octopus_{device_id}_13_target_time"  # Updated from 10_
        self._attr_translation_key = "target_time"  # Use translation key
        self._attr_icon = "mdi:clock-time-four"
        self._attr_options = VALID_TIME_OPTIONS

    def _get_device_data(self) -> dict[str, Any] | None:
        """Get device data from coordinator."""
        try:
            devices = self.coordinator.data.get("devices", {}).get(self._account_number, [])
            for device in devices:
                if device.get("id") == self._device_id:
                    return device
        except (KeyError, TypeError, AttributeError):
            _LOGGER.warning("Failed to get device data for %s", self._device_id)
        return None

    def _get_preferences(self) -> dict[str, Any] | None:
        """Get device preferences."""
        try:
            preferences_data = self.coordinator.data.get("device_preferences", {}).get(self._device_id, {})
            # Check structure
            if isinstance(preferences_data, dict) and "preferences" in preferences_data:
                return preferences_data["preferences"]
            elif isinstance(preferences_data, dict) and "schedules" in preferences_data:
                return preferences_data
        except (KeyError, TypeError, AttributeError):
            pass
        return None

    @property
    def current_option(self) -> str | None:
        """Return the current target time."""
        preferences = self._get_preferences()
        if preferences:
            schedules = preferences.get("schedules", [])
            if schedules:
                time_str = schedules[0].get("time", "10:30")
                if time_str:
                    # Remove seconds if present and ensure format
                    time_clean = time_str[:5] if len(time_str) > 5 else time_str
                    # Check if it's in our valid options
                    if time_clean in VALID_TIME_OPTIONS:
                        return time_clean
                    else:
                        # Find closest valid time
                        return self._get_closest_valid_time(time_clean)
        return "10:30"  # Default time

    def _get_closest_valid_time(self, time_str: str) -> str:
        """Get the closest valid time from options."""
        try:
            hour, minute = time_str.split(":")
            hour = int(hour)
            minute = int(minute)
            
            # Round to nearest 30-minute step
            if minute < 15:
                minute = 0
            elif minute < 45:
                minute = 30
            else:
                minute = 0
                hour += 1
            
            # Clamp to valid range
            if hour < 4:
                hour, minute = 4, 0
            elif hour > 11:
                hour, minute = 11, 0
            
            result = f"{hour:02d}:{minute:02d}"
            return result if result in VALID_TIME_OPTIONS else "10:30"
            
        except (ValueError, IndexError):
            return "10:30"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        preferences = self._get_preferences()
        if preferences is None:
            _LOGGER.debug("Target time unavailable for %s: no preferences", self._device_id)
            return False
        return True

    async def async_select_option(self, option: str) -> None:
        """Set the target time from dropdown selection."""
        try:
            device = self._get_device_data()
            device_name = device.get("name", "Cargador") if device else "Cargador"
            
            # Validate option is in allowed list
            if option not in VALID_TIME_OPTIONS:
                _LOGGER.error("Invalid time option selected: %s", option)
                return
            
            _LOGGER.info("Setting target time for %s to %s", device_name, option)
            
            # Get current preferences to preserve max percentage
            preferences = self._get_preferences()
            current_max = DEFAULT_MAX_PERCENTAGE  # Default fallback
            
            if preferences:
                schedules = preferences.get("schedules", [])
                if schedules and len(schedules) > 0:
                    # Get the actual current max percentage, don't use default
                    existing_max = schedules[0].get("max")
                    if existing_max is not None:
                        current_max = float(existing_max)
                        _LOGGER.debug("Preserving existing max percentage: %s%%", current_max)
                    else:
                        _LOGGER.warning("No existing max percentage found in schedule, using default")
                else:
                    _LOGGER.warning("No schedules found in preferences, using default max percentage")
            else:
                _LOGGER.warning("No preferences found, using default max percentage")
            
            # Create new schedules for all days with preserved max percentage
            schedules = []
            for day in DAYS_OF_WEEK:
                schedules.append({
                    "dayOfWeek": day,
                    "time": option,
                    "max": float(current_max)
                })
            
            _LOGGER.debug("Updating preferences with time=%s, max=%s%%", option, current_max)
            
            # Update preferences
            await self.coordinator.api.set_smart_flex_device_preferences(
                device_id=self._device_id,
                mode="CHARGE",
                unit="PERCENTAGE",
                schedules=schedules
            )
            
            _LOGGER.info("Successfully updated target time for %s to %s", device_name, option)
            
            # Refresh data
            await asyncio.sleep(2)
            await self.coordinator.async_refresh_specific_device(self._device_id)
            
            # Send notification
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": f"⏰ {device_name}",
                    "message": f"Hora objetivo actualizada a {option}",
                    "notification_id": f"charger_target_time_{self._device_id}",
                },
            )
            
        except Exception as err:
            _LOGGER.error("Failed to set target time for device %s: %s", self._device_id, err)
            raise

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        preferences = self._get_preferences()
        attrs = {
            "device_id": self._device_id,
            "allowed_times": VALID_TIME_OPTIONS,
            "time_range": "04:00 - 11:00",
            "step_minutes": 30
        }
        
        if preferences:
            schedules = preferences.get("schedules", [])
            if schedules:
                attrs["schedules_count"] = len(schedules)
                attrs["applies_to_all_days"] = True
                
                # Show max percentage for reference
                max_percentage = schedules[0].get("max")
                if max_percentage:
                    attrs["max_charge_percentage"] = max_percentage
                    
                attrs["mode"] = preferences.get("mode", "CHARGE")
                attrs["unit"] = preferences.get("unit", "PERCENTAGE")
        else:
            attrs["unavailable_reason"] = "Preferencias no disponibles"
        
        return attrs