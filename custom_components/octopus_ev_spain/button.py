"""Button platform for Octopus Energy Spain - CORRECTED."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
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
    """Set up Octopus Energy Spain buttons."""
    coordinator: OctopusSpainDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[ButtonEntity] = []

    # Add action buttons for each device
    for account_number, devices in coordinator.data.get("devices", {}).items():
        for device in devices:
            # Only add buttons for charge points
            if device.get("__typename") == "SmartFlexChargePoint":
                device_id = device["id"]
                entities.extend([
                    OctopusStartBoostButton(coordinator, account_number, device_id),
                    OctopusStopBoostButton(coordinator, account_number, device_id),
                    OctopusRefreshDeviceButton(coordinator, account_number, device_id),
                ])

    async_add_entities(entities)


class OctopusDeviceButton(CoordinatorEntity, ButtonEntity):
    """Base class for Octopus device buttons."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        device_id: str,
        button_type: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._account_number = account_number
        self._device_id = device_id
        self._button_type = button_type
        
        device = self._get_device_data()
        if device:
            device_name = device.get("name", "Dispositivo Desconocido")
            
            button_names = {
                "start_boost": "Iniciar Carga Rápida",
                "stop_boost": "Detener Carga Rápida", 
                "refresh_data": "Actualizar Datos"
            }
            
            button_name = button_names.get(button_type, button_type.replace('_', ' ').title())
            self._attr_name = f"{device_name} {button_name}"
            self._attr_unique_id = f"octopus_{device_id}_{button_type}"

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


class OctopusStartBoostButton(OctopusDeviceButton):
    """Button to start boost charging."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        device_id: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, account_number, device_id, "start_boost")
        self._attr_icon = "mdi:flash"

    @property
    def available(self) -> bool:
        """Return if the button is available."""
        device = self._get_device_data()
        if not device:
            return False

        # Only available if device is capable and not already boosting
        current_state = device.get("status", {}).get("currentState")
        available_states = ["SMART_CONTROL_CAPABLE", "SMART_CONTROL_IN_PROGRESS"]
        return current_state in available_states

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.coordinator.api.start_boost_charge(self._device_id)
            _LOGGER.info("Started boost charging for device %s", self._device_id)
            
            # Wait a moment for the change to propagate
            await asyncio.sleep(2)
            await self.coordinator.async_refresh_specific_device(self._device_id)
            
        except Exception as err:
            _LOGGER.error("Failed to start boost charging for device %s: %s", self._device_id, err)
            raise


class OctopusStopBoostButton(OctopusDeviceButton):
    """Button to stop boost charging."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        device_id: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, account_number, device_id, "stop_boost")
        self._attr_icon = "mdi:stop"

    @property
    def available(self) -> bool:
        """Return if the button is available."""
        device = self._get_device_data()
        if not device:
            return False

        # Only available if device is currently boosting
        current_state = device.get("status", {}).get("currentState")
        return current_state == "BOOSTING"

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.coordinator.api.stop_boost_charge(self._device_id)
            _LOGGER.info("Stopped boost charging for device %s", self._device_id)
            
            # Wait a moment for the change to propagate
            await asyncio.sleep(2)
            await self.coordinator.async_refresh_specific_device(self._device_id)
            
        except Exception as err:
            _LOGGER.error("Failed to stop boost charging for device %s: %s", self._device_id, err)
            raise


class OctopusRefreshDeviceButton(OctopusDeviceButton):
    """Button to refresh device data."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        device_id: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, account_number, device_id, "refresh_data")
        self._attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.coordinator.async_refresh_specific_device(self._device_id)
            _LOGGER.info("Refreshed data for device %s", self._device_id)
        except Exception as err:
            _LOGGER.error("Failed to refresh data for device %s: %s", self._device_id, err)
            raise