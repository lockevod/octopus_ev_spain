"""Button platform for Octopus Energy Spain - SIMPLIFIED."""
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

    # Add utility button for each charger - ONLY ONE REFRESH BUTTON
    for account_number, devices in coordinator.data.get("devices", {}).items():
        for device in devices:
            if device.get("__typename") == "SmartFlexChargePoint":
                device_id = device["id"]
                # Solo añadir un botón de refresco por cargador
                entities.append(
                    OctopusRefreshChargerButton(coordinator, account_number, device_id)
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
        device_name = device.get("name", "Dispositivo Desconocido") if device else "Dispositivo Desconocido"
        
        button_names = {
            "refresh_charger": "Actualizar y Verificar Estado",
        }
        
        button_name = button_names.get(button_type, button_type.replace('_', ' ').title())
        self._attr_name = f"{device_name} {button_name}"
        self._attr_unique_id = f"octopus_{device_id}_{button_type}"

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

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)


class OctopusRefreshChargerButton(OctopusDeviceButton):
    """Button to refresh charger data and check status - UNIFIED."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        device_id: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, account_number, device_id, "refresh_charger")
        self._attr_icon = "mdi:refresh-circle"

    async def async_press(self) -> None:
        """Handle the button press - refresh and check status."""
        try:
            device = self._get_device_data()
            device_name = device.get("name", "Cargador EV") if device else "Cargador EV"
            
            _LOGGER.info("Manual refresh and status check for %s", device_name)
            
            # Get current state before refresh
            current_state = device.get("status", {}).get("currentState") if device else None
            
            # Refresh the device data
            await self.coordinator.async_refresh_specific_device(self._device_id)
            
            # Get new state after refresh
            updated_device = self._get_device_data()
            new_state = updated_device.get("status", {}).get("currentState") if updated_device else None
            
            # Create status message
            state_translations = {
                "SMART_CONTROL_NOT_AVAILABLE": "Desconectado",
                "SMART_CONTROL_CAPABLE": "Conectado",
                "BOOSTING": "Carga Rápida",
                "SMART_CONTROL_IN_PROGRESS": "Carga Programada"
            }
            
            current_translated = state_translations.get(current_state, current_state or "Desconocido")
            new_translated = state_translations.get(new_state, new_state or "Desconocido")
            
            # Determine icon based on new state
            icon = "🔌"
            if new_state == "BOOSTING":
                icon = "⚡"
            elif new_state == "SMART_CONTROL_IN_PROGRESS":
                icon = "🔄"
            elif new_state == "SMART_CONTROL_NOT_AVAILABLE":
                icon = "❌"
            elif new_state == "SMART_CONTROL_CAPABLE":
                icon = "✅"
            
            # Create notification message
            if current_state != new_state:
                message = f"Estado cambió: {current_translated} → {new_translated}"
                notification_id = f"charger_status_change_{self._device_id}"
            else:
                message = f"Estado verificado: {new_translated}"
                notification_id = f"charger_status_check_{self._device_id}"
            
            # Add planned dispatches info if connected
            if new_state in ["SMART_CONTROL_CAPABLE", "BOOSTING", "SMART_CONTROL_IN_PROGRESS"]:
                try:
                    dispatches_count = self.coordinator.get_planned_dispatches_count(self._device_id)
                    if dispatches_count > 0:
                        message += f" | {dispatches_count} sesiones programadas"
                    else:
                        message += " | Sin sesiones programadas"
                except (KeyError, TypeError, AttributeError):
                    message += " | Sin información de sesiones"
            
            # Send persistent notification
            await self.hass.services.async_call(
                "notify",
                "persistent_notification",
                {
                    "title": f"{icon} {device_name}",
                    "message": message,
                    "notification_id": notification_id,
                },
            )
            
            # Fire custom event for automations
            planned_dispatches_count = 0
            try:
                planned_dispatches_count = self.coordinator.get_planned_dispatches_count(self._device_id)
            except (KeyError, TypeError, AttributeError):
                pass
            
            self.hass.bus.async_fire("octopus_charger_refreshed", {
                "device_id": self._device_id,
                "device_name": device_name,
                "old_state": current_state,
                "new_state": new_state,
                "state_changed": current_state != new_state,
                "old_state_translated": current_translated,
                "new_state_translated": new_translated,
                "is_connected": new_state in ["SMART_CONTROL_CAPABLE", "BOOSTING", "SMART_CONTROL_IN_PROGRESS"],
                "planned_dispatches_count": planned_dispatches_count,
            })
            
            _LOGGER.info("Refresh and status check completed for %s: %s → %s", 
                        device_name, current_state, new_state)
            
        except Exception as err:
            _LOGGER.error("Failed to refresh and check status for device %s: %s", self._device_id, err)
            
            # Send error notification
            device = self._get_device_data()
            device_name = device.get("name", "Cargador EV") if device else "Cargador EV"
            
            await self.hass.services.async_call(
                "notify",
                "persistent_notification",
                {
                    "title": f"❌ {device_name}",
                    "message": f"Error al actualizar: {str(err)}",
                    "notification_id": f"charger_refresh_error_{self._device_id}",
                },
            )
            raise