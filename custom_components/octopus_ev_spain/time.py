"""Time platform for Octopus Energy Spain - SIMPLIFIED."""
from __future__ import annotations

import asyncio
import logging
from datetime import time
from typing import Any

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_MAX_PERCENTAGE, DAYS_OF_WEEK
from .coordinator import OctopusSpainDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Octopus Energy Spain time entities."""
    coordinator: OctopusSpainDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[TimeEntity] = []

    # Add time configuration entities for each charger
    for account_number, devices in coordinator.data.get("devices", {}).items():
        for device in devices:
            if device.get("__typename") == "SmartFlexChargePoint":
                device_id = device["id"]
                entities.append(
                    OctopusChargerTargetTimeEntity(coordinator, account_number, device_id)
                )

    async_add_entities(entities)


def _safe_device_info(device_id: str, device: dict[str, Any] | None) -> dict[str, Any]:
    """Safely create device info."""
    if not device:
        return {
            "identifiers": {(DOMAIN, device_id)},
            "name": "Dispositivo Desconocido",
            "manufacturer": "Octopus Energy",
            "model": "Desconocido",
        }
        
    return {
        "identifiers": {(DOMAIN, device_id)},
        "name": device.get("name", "Dispositivo Desconocido"),
        "manufacturer": "Octopus Energy",
        "model": f"{device.get('__typename', 'Desconocido')} ({device.get('provider', 'Desconocido')})",
        "sw_version": device.get("deviceType", "Desconocido"),
    }


class OctopusChargerTargetTimeEntity(CoordinatorEntity, TimeEntity):
    """Time entity for charger target time configuration."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        device_id: str,
    ) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator)
        self._account_number = account_number
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Cargador") if device else "Cargador"
        self._attr_name = f"{device_name} Hora Objetivo"
        self._attr_unique_id = f"octopus_{device_id}_target_time"
        self._attr_icon = "mdi:clock-time-four"

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
    def native_value(self) -> time | None:
        """Return the current target time."""
        preferences = self._get_preferences()
        if preferences:
            schedules = preferences.get("schedules", [])
            if schedules:
                time_str = schedules[0].get("time", "10:30")
                if time_str:
                    try:
                        # Handle both "10:30" and "10:30:00" formats
                        time_parts = time_str.split(":")
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])
                        return time(hour, minute)
                    except (ValueError, IndexError):
                        _LOGGER.warning("Invalid time format: %s", time_str)
        return time(10, 30)  # Default time

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Time configuration should always be available if preferences exist
        preferences = self._get_preferences()
        if preferences is None:
            _LOGGER.debug("Target time unavailable for %s: no preferences", self._device_id)
            return False
        return True

    async def async_set_value(self, value: time) -> None:
        """Set the target time."""
        try:
            device = self._get_device_data()
            device_name = device.get("name", "Cargador") if device else "Cargador"
            
            new_time = f"{value.hour:02d}:{value.minute:02d}"
            _LOGGER.info("Setting target time for %s to %s", device_name, new_time)
            
            # Get current preferences to preserve max percentage
            preferences = self._get_preferences()
            current_max = DEFAULT_MAX_PERCENTAGE
            
            if preferences:
                schedules = preferences.get("schedules", [])
                if schedules:
                    current_max = schedules[0].get("max", DEFAULT_MAX_PERCENTAGE)
            
            # Create new schedules for all days
            schedules = []
            for day in DAYS_OF_WEEK:
                schedules.append({
                    "dayOfWeek": day,
                    "time": new_time,
                    "max": float(current_max)
                })
            
            # Update preferences
            await self.coordinator.api.set_smart_flex_device_preferences(
                device_id=self._device_id,
                mode="CHARGE",
                unit="PERCENTAGE",
                schedules=schedules
            )
            
            _LOGGER.info("Successfully updated target time for %s to %s", device_name, new_time)
            
            # Refresh data
            await asyncio.sleep(2)
            await self.coordinator.async_refresh_specific_device(self._device_id)
            
            # Send notification
            await self.hass.services.async_call(
                "notify",
                "persistent_notification",
                {
                    "title": f"⏰ {device_name}",
                    "message": f"Hora objetivo actualizada a {new_time}",
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
        attrs = {"device_id": self._device_id}
        
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