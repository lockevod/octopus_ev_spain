"""Switch platform for Octopus Energy Spain - SIMPLIFIED."""
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

    # Add boost charge switches for each charger
    for account_number, devices in coordinator.data.get("devices", {}).items():
        for device in devices:
            if device.get("__typename") == "SmartFlexChargePoint":
                entities.append(OctopusBoostChargeSwitch(coordinator, account_number, device["id"]))

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
        device_name = device.get("name", "Dispositivo Desconocido") if device else "Dispositivo Desconocido"
        self._attr_name = f"{device_name} Carga Rápida"
        self._attr_unique_id = f"octopus_{device_id}_boost_charge"
        self._attr_icon = "mdi:ev-station"

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

    def _get_current_state(self) -> str | None:
        """Get current device state."""
        try:
            device = self._get_device_data()
            if device:
                return device.get("status", {}).get("currentState")
        except (KeyError, TypeError, AttributeError):
            pass
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)

    @property
    def is_on(self) -> bool | None:
        """Return if boost charging is on."""
        current_state = self._get_current_state()
        return current_state == "BOOSTING"

    @property
    def available(self) -> bool:
        """Return if the switch is available."""
        current_state = self._get_current_state()
        
        # Switch is available when car is connected
        connected_states = [
            "SMART_CONTROL_CAPABLE",     # Connected, ready
            "SMART_CONTROL_IN_PROGRESS", # Charging in scheduled session 
            "BOOSTING"                   # Already boosting
        ]
        
        is_available = current_state in connected_states
        
        if not is_available:
            _LOGGER.debug("Boost switch unavailable for device %s: state is %s", self._device_id, current_state)
        
        return is_available

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start boost charging."""
        current_state = self._get_current_state()
        device = self._get_device_data()
        device_name = device.get("name", "Unknown") if device else "Unknown"
        
        _LOGGER.info("Starting boost charge for %s (current state: %s)", device_name, current_state)
        
        # Check if we can start boost charging
        if current_state == "BOOSTING":
            _LOGGER.warning("Boost charging already active for %s", device_name)
            return
            
        if current_state == "SMART_CONTROL_NOT_AVAILABLE":
            _LOGGER.error("Cannot start boost charging - car not connected to %s", device_name)
            raise Exception("Coche no conectado - no se puede iniciar carga rápida")
        
        try:
            await self.coordinator.api.start_boost_charge(self._device_id)
            _LOGGER.info("Started boost charging for %s", device_name)
            
            # Wait for change to propagate, then refresh
            await asyncio.sleep(3)
            await self.coordinator.async_refresh_specific_device(self._device_id)
            
        except Exception as err:
            _LOGGER.error("Failed to start boost charging for %s: %s", device_name, err)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop boost charging."""
        current_state = self._get_current_state()
        device = self._get_device_data()
        device_name = device.get("name", "Unknown") if device else "Unknown"
        
        _LOGGER.info("Stopping boost charge for %s (current state: %s)", device_name, current_state)
        
        # Check if boost is actually running
        if current_state != "BOOSTING":
            _LOGGER.warning("Boost charging not active for %s (state: %s)", device_name, current_state)
            return
        
        try:
            await self.coordinator.api.stop_boost_charge(self._device_id)
            _LOGGER.info("Stopped boost charging for %s", device_name)
            
            # Wait for change to propagate, then refresh
            await asyncio.sleep(3)
            await self.coordinator.async_refresh_specific_device(self._device_id)
            
        except Exception as err:
            _LOGGER.error("Failed to stop boost charging for %s: %s", device_name, err)
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        device = self._get_device_data()
        current_state = self._get_current_state()
        
        attrs = {
            "device_id": self._device_id,
            "account_number": self._account_number,
            "raw_state": current_state,
        }

        if device:
            attrs.update({
                "device_type": device.get("deviceType"),
                "provider": device.get("provider"),
                "property_id": device.get("propertyId"),
            })

        # Add state explanation in Spanish
        state_explanations = {
            "SMART_CONTROL_NOT_AVAILABLE": "Coche desconectado",
            "SMART_CONTROL_CAPABLE": "Conectado, listo para cargar",
            "BOOSTING": "Carga rápida activa",
            "SMART_CONTROL_IN_PROGRESS": "Carga programada en curso"
        }
        
        attrs["state_explanation"] = state_explanations.get(current_state, "Estado desconocido")
        
        # Add connection status
        attrs["is_connected"] = current_state in [
            "SMART_CONTROL_CAPABLE", 
            "BOOSTING", 
            "SMART_CONTROL_IN_PROGRESS"
        ]
        
        # Add capabilities based on current state
        if current_state == "SMART_CONTROL_NOT_AVAILABLE":
            attrs["can_start_boost"] = False
            attrs["can_stop_boost"] = False
            attrs["reason"] = "Coche no conectado"
        elif current_state == "SMART_CONTROL_CAPABLE":
            attrs["can_start_boost"] = True
            attrs["can_stop_boost"] = False
            attrs["reason"] = "Listo para iniciar carga"
        elif current_state == "BOOSTING":
            attrs["can_start_boost"] = False
            attrs["can_stop_boost"] = True
            attrs["reason"] = "Carga rápida en progreso"
        elif current_state == "SMART_CONTROL_IN_PROGRESS":
            attrs["can_start_boost"] = True  # Can switch to boost from scheduled charging
            attrs["can_stop_boost"] = False
            attrs["reason"] = "Puede cambiar a carga rápida"
        else:
            attrs["can_start_boost"] = False
            attrs["can_stop_boost"] = False
            attrs["reason"] = "Estado desconocido"

        # Add planned dispatches info
        try:
            dispatches_count = self.coordinator.get_planned_dispatches_count(self._device_id)
            attrs["planned_sessions"] = dispatches_count
            if attrs["is_connected"] and dispatches_count == 0:
                attrs["reason"] += " (sin sesiones programadas)"
        except (KeyError, TypeError, AttributeError):
            attrs["planned_sessions"] = 0

        return attrs