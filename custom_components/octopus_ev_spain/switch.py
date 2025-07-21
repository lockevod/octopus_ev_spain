"""Switch platform for Octopus Energy Spain - CORRECTED."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OctopusSpainDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Octopus Energy Spain switches."""
    coordinator: OctopusSpainDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[SwitchEntity] = []

    # Add boost charge switches for each device
    for account_number, devices in coordinator.data.get("devices", {}).items():
        for device in devices:
            # Only add switches for charge points
            if device.get("__typename") == "SmartFlexChargePoint":
                entities.append(OctopusBoostChargeSwitch(coordinator, account_number, device["id"]))

    async_add_entities(entities)


class OctopusBoostChargeSwitch(CoordinatorEntity, SwitchEntity):
    """Switch for controlling boost charging."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        device_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._account_number = account_number
        self._device_id = device_id
        
        device = self._get_device_data()
        if device:
            device_name = device.get("name", "Dispositivo Desconocido")
            self._attr_name = f"{device_name} Carga Rápida"
            self._attr_unique_id = f"octopus_{device_id}_boost_charge"
            self._attr_icon = "mdi:ev-station"

    def _get_device_data(self) -> dict[str, Any] | None:
        """Get device data from coordinator."""
        devices = self.coordinator.data.get("devices", {}).get(self._account_number, [])
        for device in devices:
            if device.get("id") == self._device_id:
                return device
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device = self._get_device_data()
        if not device:
            return {}
            
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": device.get("name", "Dispositivo Desconocido"),
            "manufacturer": "Octopus Energy",
            "model": f"{device.get('__typename', 'Desconocido')} ({device.get('provider', 'Desconocido')})",
            "sw_version": device.get("deviceType", "Desconocido"),
        }

    @property
    def is_on(self) -> bool | None:
        """Return if boost charging is on based on real data structure."""
        device = self._get_device_data()
        if not device:
            return None

        # Check if device is in BOOSTING state (this is the correct field from traces)
        current_state = device.get("status", {}).get("currentState")
        if current_state == "BOOSTING":
            return True

        # Also check for active charging sessions of type SMART that are still ongoing
        sessions = device.get("chargePointChargingSession", {}).get("edges", [])
        for session_edge in sessions:
            session = session_edge["node"]
            if (
                session.get("type") == "SMART" 
                and session.get("end") is None  # Active session (no end time)
            ):
                return True

        return False

    @property
    def available(self) -> bool:
        """Return if the switch is available."""
        device = self._get_device_data()
        if not device:
            return False

        # Check if device supports smart control (based on real states from traces)
        current_state = device.get("status", {}).get("currentState")
        available_states = [
            "SMART_CONTROL_CAPABLE", 
            "SMART_CONTROL_IN_PROGRESS", 
            "BOOSTING"
        ]
        
        return current_state in available_states

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start boost charging using corrected API."""
        try:
            await self.coordinator.api.start_boost_charge(self._device_id)
            # Wait a moment for the change to propagate
            await asyncio.sleep(2)
            await self.coordinator.async_refresh_specific_device(self._device_id)
            _LOGGER.info("Started boost charging for device %s", self._device_id)
        except Exception as err:
            _LOGGER.error("Failed to start boost charging for device %s: %s", self._device_id, err)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop boost charging using corrected API."""
        try:
            await self.coordinator.api.stop_boost_charge(self._device_id)
            # Wait a moment for the change to propagate
            await asyncio.sleep(2)
            await self.coordinator.async_refresh_specific_device(self._device_id)
            _LOGGER.info("Stopped boost charging for device %s", self._device_id)
        except Exception as err:
            _LOGGER.error("Failed to stop boost charging for device %s: %s", self._device_id, err)
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        device = self._get_device_data()
        if not device:
            return {}

        attrs = {
            "device_id": self._device_id,
            "account_number": self._account_number,
            "device_type": device.get("deviceType"),
            "provider": device.get("provider"),
            "current_state": device.get("status", {}).get("currentState"),
            "status": device.get("status", {}).get("current"),
            "is_suspended": device.get("status", {}).get("isSuspended"),
        }

        # Add active session info from real data structure
        sessions = device.get("chargePointChargingSession", {}).get("edges", [])
        active_sessions = [
            session["node"] for session in sessions 
            if session["node"].get("end") is None
        ]
        
        if active_sessions:
            latest_session = active_sessions[0]
            energy_data = latest_session.get("energyAdded", {})
            cost_data = latest_session.get("cost", {})
            
            attrs.update({
                "active_session_start": latest_session.get("start"),
                "active_session_type": latest_session.get("type"),
                "active_session_energy_added": energy_data.get("value") if energy_data else None,
                "active_session_energy_unit": energy_data.get("unit") if energy_data else None,
                "active_session_cost": cost_data.get("amount") if cost_data else None,
                "active_session_currency": cost_data.get("currency") if cost_data else None,
                "active_session_soc_change": latest_session.get("stateOfChargeChange"),
                "active_session_soc_final": latest_session.get("stateOfChargeFinal"),
                "active_session_problems": len(latest_session.get("problems", [])),
            })

        # Add preferences info
        preferences = device.get("preferences", {})
        if preferences:
            attrs.update({
                "charging_mode": preferences.get("mode"),
                "target_type": preferences.get("targetType"),
                "unit": preferences.get("unit"),
                "schedules_count": len(preferences.get("schedules", [])),
            })

        return attrs