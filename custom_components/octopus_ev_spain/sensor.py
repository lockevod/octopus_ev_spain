"""Sensor platform for Octopus Energy Spain - SIMPLIFIED for new structure."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CURRENCY_EURO,
    UnitOfEnergy,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ELECTRICITY_LEDGER, SOLAR_WALLET_LEDGER, GAS_LEDGER, LEDGER_NAMES
from .coordinator import OctopusSpainDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Octopus Energy Spain sensors."""
    coordinator: OctopusSpainDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[SensorEntity] = []

    # Account-level sensors (ledger balances + invoices)
    for account_number in coordinator.accounts:
        account_data = coordinator.data.get("accounts", {}).get(account_number, {})
        
        # Add ledger sensors
        for ledger in account_data.get("ledgers", []):
            entities.append(OctopusLedgerSensor(coordinator, account_number, ledger))
        
        # Add invoice sensor (from original repo)
        billing_data = coordinator.data.get("billing_info", {}).get(account_number, {})
        if billing_data.get("last_invoice") is not None:
            entities.append(OctopusInvoiceSensor(coordinator, account_number))

    # Device sensors
    for account_number, devices in coordinator.data.get("devices", {}).items():
        for device in devices:
            device_id = device["id"]
            device_type = device.get("__typename")
            
            if device_type == "SmartFlexChargePoint":
                # Add charger-specific sensors
                entities.extend([
                    OctopusDeviceStateSensor(coordinator, account_number, device_id),
                    OctopusChargerPlannedDispatchesSensor(coordinator, device_id),
                    OctopusChargerLastEnergyAddedSensor(coordinator, device_id),
                    OctopusChargerLastSessionDurationSensor(coordinator, device_id),
                    OctopusChargerLastSessionCostSensor(coordinator, device_id),
                    OctopusChargerPreferencesSensor(coordinator, device_id),
                ])

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


class OctopusLedgerSensor(CoordinatorEntity, SensorEntity):
    """Sensor for account ledger balances."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        ledger: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_number = account_number
        self._ledger = ledger
        self._ledger_type = ledger["ledgerType"]
        
        # Use friendly names from constants
        ledger_name = LEDGER_NAMES.get(self._ledger_type, self._ledger_type.replace("_", " ").title())
        self._attr_name = f"Octopus {ledger_name} Saldo"
        self._attr_unique_id = f"octopus_{account_number}_{self._ledger_type.lower()}_balance"
        self._attr_native_unit_of_measurement = CURRENCY_EURO
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:wallet"

    @property
    def native_value(self) -> float | None:
        """Return the balance value."""
        account_data = self.coordinator.data.get("accounts", {}).get(self._account_number, {})
        for ledger in account_data.get("ledgers", []):
            if ledger["ledgerType"] == self._ledger_type:
                # Balance is in cents, convert to euros
                return float(ledger["balance"]) / 100
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        account_data = self.coordinator.data.get("accounts", {}).get(self._account_number, {})
        for ledger in account_data.get("ledgers", []):
            if ledger["ledgerType"] == self._ledger_type:
                return {
                    "ledger_number": ledger.get("number"),
                    "accepts_payments": ledger.get("acceptsPayments"),
                    "account_number": self._account_number,
                    "ledger_type": self._ledger_type,
                }
        return {}

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus Energy EV",
            "manufacturer": "Lockevod",
            "model": "Spain",
        }


class OctopusDeviceStateSensor(CoordinatorEntity, SensorEntity):
    """Sensor for device current state."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_number = account_number
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Dispositivo Desconocido") if device else "Dispositivo Desconocido"
        self._attr_name = f"{device_name} Estado"
        self._attr_unique_id = f"octopus_{device_id}_current_state"
        self._attr_icon = "mdi:state-machine"

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
    def native_value(self) -> str | None:
        """Return the current state."""
        device = self._get_device_data()
        if device:
            current_state = device.get("status", {}).get("currentState")
            
            # Translate states to Spanish
            state_translations = {
                "SMART_CONTROL_NOT_AVAILABLE": "Desconectado",
                "SMART_CONTROL_CAPABLE": "Conectado",
                "BOOSTING": "Carga Rápida",
                "SMART_CONTROL_IN_PROGRESS": "Carga Programada"
            }
            
            return state_translations.get(current_state, current_state)
        return "Desconocido"

    @property
    def available(self) -> bool:
        """Return if sensor is available."""
        device = self._get_device_data()
        return device is not None and device.get("status") is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        device = self._get_device_data()
        
        attrs = {
            "device_id": self._device_id,
            "account_number": self._account_number,
        }
        
        if device:
            attrs.update({
                "device_type": device.get("deviceType"),
                "provider": device.get("provider"),
                "property_id": device.get("propertyId"),
            })
            
            raw_state = device.get("status", {}).get("currentState")
            attrs["raw_state"] = raw_state
            
            # Add connection status
            attrs["is_connected"] = raw_state in [
                "SMART_CONTROL_CAPABLE", 
                "BOOSTING", 
                "SMART_CONTROL_IN_PROGRESS"
            ]

        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)


class OctopusChargerPlannedDispatchesSensor(CoordinatorEntity, SensorEntity):
    """Sensor for planned charging dispatches."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Cargador") if device else "Cargador"
        self._attr_name = f"{device_name} Sesiones Programadas"
        self._attr_unique_id = f"octopus_{device_id}_planned_dispatches"
        self._attr_icon = "mdi:calendar-clock"

    def _get_device_data(self) -> dict[str, Any] | None:
        """Get device data from coordinator."""
        try:
            for devices in self.coordinator.data.get("devices", {}).values():
                for device in devices:
                    if device.get("id") == self._device_id:
                        return device
        except (KeyError, TypeError, AttributeError):
            pass
        return None

    @property
    def native_value(self) -> int:
        """Return number of planned dispatches."""
        dispatches = self.coordinator.data.get("planned_dispatches", {}).get(self._device_id, [])
        return len(dispatches)

    @property
    def available(self) -> bool:
        """Return if sensor is available - only when car is connected."""
        device = self._get_device_data()
        if not device:
            return False
        
        current_state = device.get("status", {}).get("currentState")
        connected_states = ["SMART_CONTROL_CAPABLE", "BOOSTING", "SMART_CONTROL_IN_PROGRESS"]
        return current_state in connected_states

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        dispatches = self.coordinator.data.get("planned_dispatches", {}).get(self._device_id, [])
        
        attrs = {
            "device_id": self._device_id,
        }
        
        if not self.available:
            attrs["unavailable_reason"] = "Coche desconectado - información no disponible"
            return attrs
        
        if dispatches:
            # Add formatted dispatch info
            formatted_dispatches = []
            for dispatch in dispatches:
                start_time = dispatch.get("start")
                end_time = dispatch.get("end")
                dispatch_type = dispatch.get("type")
                
                if start_time and end_time:
                    try:
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        
                        formatted_dispatches.append({
                            "start": start_dt.strftime("%Y-%m-%d %H:%M"),
                            "end": end_dt.strftime("%Y-%m-%d %H:%M"),
                            "duration_hours": round((end_dt - start_dt).total_seconds() / 3600, 1),
                            "type": dispatch_type
                        })
                    except ValueError:
                        formatted_dispatches.append({
                            "start": start_time,
                            "end": end_time,
                            "type": dispatch_type
                        })
            
            attrs["dispatches"] = formatted_dispatches
            
            # Add next dispatch info
            if formatted_dispatches:
                next_dispatch = formatted_dispatches[0]
                attrs["next_dispatch_start"] = next_dispatch["start"]
                attrs["next_dispatch_end"] = next_dispatch["end"]
                if "duration_hours" in next_dispatch:
                    attrs["next_dispatch_duration_hours"] = next_dispatch["duration_hours"]

        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)


class OctopusChargerPreferencesSensor(CoordinatorEntity, SensorEntity):
    """Sensor for charger preferences."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Cargador") if device else "Cargador"
        self._attr_name = f"{device_name} Configuración"
        self._attr_unique_id = f"octopus_{device_id}_preferences"
        self._attr_icon = "mdi:cog"

    def _get_device_data(self) -> dict[str, Any] | None:
        """Get device data from coordinator."""
        try:
            for devices in self.coordinator.data.get("devices", {}).values():
                for device in devices:
                    if device.get("id") == self._device_id:
                        return device
        except (KeyError, TypeError, AttributeError):
            pass
        return None

    def _get_preferences(self) -> dict[str, Any] | None:
        """Get device preferences."""
        try:
            preferences_data = self.coordinator.data.get("device_preferences", {}).get(self._device_id, {})
            if isinstance(preferences_data, dict) and "preferences" in preferences_data:
                return preferences_data["preferences"]
            elif isinstance(preferences_data, dict) and "schedules" in preferences_data:
                return preferences_data
        except (KeyError, TypeError, AttributeError):
            pass
        return None

    @property
    def native_value(self) -> str | None:
        """Return charging mode."""
        preferences = self._get_preferences()
        if preferences:
            return preferences.get("mode", "Desconocido")
        return "No configurado"

    @property
    def available(self) -> bool:
        """Return if sensor is available."""
        preferences = self._get_preferences()
        return preferences is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        preferences = self._get_preferences()
        attrs = {"device_id": self._device_id}
        
        if not preferences:
            attrs["unavailable_reason"] = "Preferencias no disponibles"
            return attrs
        
        attrs.update({
            "target_type": preferences.get("targetType"),
            "unit": preferences.get("unit"),
            "mode": preferences.get("mode"),
        })
        
        schedules = preferences.get("schedules", [])
        if schedules:
            attrs["schedules_count"] = len(schedules)
            
            # Get max charge level (should be same for all days)
            max_charges = [s.get("max") for s in schedules if s.get("max")]
            if max_charges:
                attrs["max_charge_percentage"] = max_charges[0]
            
            # Get target time (should be same for all days)
            times = [s.get("time") for s in schedules if s.get("time")]
            if times:
                attrs["target_time"] = times[0]

        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)


class OctopusChargerLastEnergyAddedSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last charging session energy added."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Cargador") if device else "Cargador"
        self._attr_name = f"{device_name} Última Energía Añadida"
        self._attr_unique_id = f"octopus_{device_id}_last_energy_added"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:lightning-bolt"

    def _get_device_data(self) -> dict[str, Any] | None:
        for devices in self.coordinator.data.get("devices", {}).values():
            for device in devices:
                if device.get("id") == self._device_id:
                    return device
        return None

    def _get_last_session(self) -> dict[str, Any] | None:
        history_data = self.coordinator.data.get("charge_history", {}).get(self._device_id, [])
        if history_data and len(history_data) > 0:
            sessions = history_data[0].get("chargePointChargingSession", {}).get("edges", [])
            if sessions:
                return sessions[0]["node"]
        return None

    @property
    def native_value(self) -> float | None:
        last_session = self._get_last_session()
        if last_session:
            energy_data = last_session.get("energyAdded", {})
            value = energy_data.get("value")
            if value:
                return float(value)
        return None

    @property
    def available(self) -> bool:
        return self._get_last_session() is not None

    @property
    def device_info(self) -> dict[str, Any]:
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)


class OctopusInvoiceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last invoice - FROM ORIGINAL REPO."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_number = account_number
        
        # Handle single vs multiple accounts naming
        is_single_account = len(coordinator.accounts) == 1
        self._attr_name = "Última Factura Octopus" if is_single_account else f"Última Factura Octopus ({account_number})"
        self._attr_unique_id = f"octopus_{account_number}_last_invoice"
        self._attr_native_unit_of_measurement = CURRENCY_EURO
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:currency-eur"

    @property
    def native_value(self) -> float | None:
        """Return the invoice amount."""
        billing_data = self.coordinator.data.get("billing_info", {}).get(self._account_number, {})
        last_invoice = billing_data.get("last_invoice")
        
        if last_invoice and last_invoice.get("amount") is not None:
            return float(last_invoice["amount"])
        return None

    @property
    def available(self) -> bool:
        """Return if sensor is available."""
        billing_data = self.coordinator.data.get("billing_info", {}).get(self._account_number, {})
        return billing_data.get("last_invoice") is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        billing_data = self.coordinator.data.get("billing_info", {}).get(self._account_number, {})
        last_invoice = billing_data.get("last_invoice")
        
        attrs = {
            "account_number": self._account_number,
        }
        
        if last_invoice:
            # Following original repo attribute names
            if last_invoice.get("start"):
                attrs["Inicio"] = last_invoice["start"]
            if last_invoice.get("end"):
                attrs["Fin"] = last_invoice["end"]
            if last_invoice.get("issued"):
                attrs["Emitida"] = last_invoice["issued"]
        
        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus Energy EVEspaña",
            "manufacturer": "Lockevod",
            "model": "Spain",
        }


class OctopusChargerLastSessionDurationSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last charging session duration."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Cargador") if device else "Cargador"
        self._attr_name = f"{device_name} Duración Última Sesión"
        self._attr_unique_id = f"octopus_{device_id}_last_session_duration"
        self._attr_native_unit_of_measurement = UnitOfTime.HOURS
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:timer"

    def _get_device_data(self) -> dict[str, Any] | None:
        for devices in self.coordinator.data.get("devices", {}).values():
            for device in devices:
                if device.get("id") == self._device_id:
                    return device
        return None

    def _get_last_session(self) -> dict[str, Any] | None:
        history_data = self.coordinator.data.get("charge_history", {}).get(self._device_id, [])
        if history_data and len(history_data) > 0:
            sessions = history_data[0].get("chargePointChargingSession", {}).get("edges", [])
            if sessions:
                return sessions[0]["node"]
        return None

    @property
    def native_value(self) -> float | None:
        last_session = self._get_last_session()
        if last_session:
            start_time = last_session.get("start")
            end_time = last_session.get("end")
            
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration = (end_dt - start_dt).total_seconds() / 3600
                    return round(duration, 1)
                except ValueError:
                    pass
        return None

    @property
    def available(self) -> bool:
        last_session = self._get_last_session()
        if not last_session:
            return False
        return last_session.get("start") and last_session.get("end")

    @property
    def device_info(self) -> dict[str, Any]:
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)


class OctopusChargerLastSessionCostSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last session cost."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Cargador") if device else "Cargador"
        self._attr_name = f"{device_name} Coste Última Sesión"
        self._attr_unique_id = f"octopus_{device_id}_last_session_cost"
        self._attr_native_unit_of_measurement = CURRENCY_EURO
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_icon = "mdi:currency-eur"

    def _get_device_data(self) -> dict[str, Any] | None:
        for devices in self.coordinator.data.get("devices", {}).values():
            for device in devices:
                if device.get("id") == self._device_id:
                    return device
        return None

    def _get_last_session(self) -> dict[str, Any] | None:
        history_data = self.coordinator.data.get("charge_history", {}).get(self._device_id, [])
        if history_data and len(history_data) > 0:
            sessions = history_data[0].get("chargePointChargingSession", {}).get("edges", [])
            if sessions:
                return sessions[0]["node"]
        return None

    @property
    def native_value(self) -> float | None:
        last_session = self._get_last_session()
        if last_session:
            cost_data = last_session.get("cost")
            if cost_data and cost_data.get("amount"):
                return float(cost_data["amount"])
        return None

    @property
    def available(self) -> bool:
        last_session = self._get_last_session()
        if not last_session:
            return False
        cost_data = last_session.get("cost")
        return cost_data is not None and cost_data.get("amount") is not None

    @property
    def device_info(self) -> dict[str, Any]:
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)