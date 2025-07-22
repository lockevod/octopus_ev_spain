"""Number platform for Octopus Energy Spain - SIMPLIFIED."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
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
    """Set up Octopus Energy Spain number entities."""
    coordinator: OctopusSpainDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[NumberEntity] = []

    # Add max percentage configuration for each charger
    for account_number, devices in coordinator.data.get("devices", {}).items():
        for device in devices:
            if device.get("__typename") == "SmartFlexChargePoint":
                device_id = device["id"]
                entities.append(
                    OctopusChargerMaxPercentageNumber(coordinator, account_number, device_id)
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


class OctopusChargerMaxPercentageNumber(CoordinatorEntity, NumberEntity):
    """Number entity for charger max percentage configuration."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        device_id: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._account_number = account_number
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Charger") if device else "Charger"
        self._attr_name = f"{device_name} Max Percentage"
        self._attr_unique_id = f"octopus_{device_id}_12_max_percentage"  # Updated from 09_
        self._attr_translation_key = "max_percentage"  # Use translation key
            
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_min_value = 10
        self._attr_native_max_value = 100
        self._attr_native_step = 5
        self._attr_icon = "mdi:battery-charging-90"

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
    def native_value(self) -> float | None:
        """Return the current max percentage."""
        preferences = self._get_preferences()
        if preferences:
            schedules = preferences.get("schedules", [])
            if schedules:
                max_value = schedules[0].get("max")
                return float(max_value) if max_value else DEFAULT_MAX_PERCENTAGE
        return DEFAULT_MAX_PERCENTAGE

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Max percentage should always be available if preferences exist
        preferences = self._get_preferences()
        if preferences is None:
            _LOGGER.debug("Max percentage unavailable for %s: no preferences", self._device_id)
            return False
        return True

    async def async_set_native_value(self, value: float) -> None:
        """Set the max percentage."""
        try:
            device = self._get_device_data()
            device_name = device.get("name", "Cargador") if device else "Cargador"
            
            _LOGGER.info("Setting max percentage for %s to %s%%", device_name, value)
            
            # Get current preferences to preserve target time
            preferences = self._get_preferences()
            current_time = "10:30"  # Default fallback
            
            if preferences:
                schedules = preferences.get("schedules", [])
                if schedules and len(schedules) > 0:
                    # Get the actual current time, don't use default
                    existing_time = schedules[0].get("time")
                    if existing_time:
                        # Clean the time format (remove seconds if present)
                        current_time = existing_time[:5] if len(existing_time) > 5 else existing_time
                        _LOGGER.debug("Preserving existing target time: %s", current_time)
                    else:
                        _LOGGER.warning("No existing time found in schedule, using default")
                else:
                    _LOGGER.warning("No schedules found in preferences, using default time")
            else:
                _LOGGER.warning("No preferences found, using default time")
            
            # Create new schedules with updated max percentage but preserved time
            schedules = []
            for day in DAYS_OF_WEEK:
                schedules.append({
                    "dayOfWeek": day,
                    "time": current_time,
                    "max": float(value)
                })
            
            _LOGGER.debug("Updating preferences with time=%s, max=%s%%", current_time, value)
            
            # Update preferences
            await self.coordinator.api.set_smart_flex_device_preferences(
                device_id=self._device_id,
                mode="CHARGE",
                unit="PERCENTAGE",
                schedules=schedules
            )
            
            _LOGGER.info("Successfully updated max percentage for %s to %s%%", device_name, value)
            
            # Refresh data
            await asyncio.sleep(2)
            await self.coordinator.async_refresh_specific_device(self._device_id)
            
            # FIXED: Send notification using persistent_notification.create
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": f"🔋 {device_name}",
                    "message": f"Porcentaje máximo actualizado a {value}%",
                    "notification_id": f"charger_max_percentage_{self._device_id}",
                },
            )
            
        except Exception as err:
            _LOGGER.error("Failed to set max percentage for device %s: %s", self._device_id, err)
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
                
                # Show target time for reference
                target_time = schedules[0].get("time")
                if target_time:
                    attrs["target_time"] = target_time
                    
                attrs["mode"] = preferences.get("mode", "CHARGE")
                attrs["unit"] = preferences.get("unit", "PERCENTAGE")
        else:
            attrs["unavailable_reason"] = "Preferencias no disponibles"
        
        return attrs