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

    # Account-level sensors (ledger balances + invoices + contract info)
    for account_number in coordinator.accounts:
        account_data = coordinator.data.get("accounts", {}).get(account_number, {})
        
        # Add NEW contract information sensors FIRST (in order requested)
        properties_data = coordinator.data.get("account_properties", {}).get(account_number, {})
        if properties_data:
            entities.append(OctopusContractNumberSensor(coordinator, account_number))
            if properties_data.get("properties"):
                entities.append(OctopusAddressSensor(coordinator, account_number))
        
        # Add CUPS sensor if available
        meters_data = coordinator.data.get("property_meters", {}).get(account_number, {})
        if meters_data.get("electricitySupplyPoints"):
            entities.append(OctopusCupsSensor(coordinator, account_number))
        
        # Add contract details sensors if available
        agreement_data = coordinator.data.get("electricity_agreements", {}).get(account_number, {})
        if agreement_data.get("activeAgreement"):
            entities.append(OctopusContractTypeSensor(coordinator, account_number))
            entities.append(OctopusContractValidFromSensor(coordinator, account_number))
            entities.append(OctopusContractValidToSensor(coordinator, account_number))
        
        # Add existing ledger sensors
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
                # Add charger-specific sensors (order: dirección, contrato, estado, planificada, última carga)
                entities.extend([
                    # NEW: Reference sensors for contract info in charger device
                    OctopusChargerContractReferenceSensor(coordinator, account_number, device_id),
                    OctopusChargerAddressReferenceSensor(coordinator, account_number, device_id),
                    OctopusDeviceStateSensor(coordinator, account_number, device_id),
                    OctopusChargerPlannedDispatchesSensor(coordinator, device_id),
                    OctopusChargerLastEnergyAddedSensor(coordinator, device_id),
                    OctopusChargerLastSessionDurationSensor(coordinator, device_id),
                    OctopusChargerLastSessionCostSensor(coordinator, device_id),
                    # REMOVED: OctopusChargerPreferencesSensor - no aporta valor según usuario
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


# NEW SENSORS - Contract and Property Information

class OctopusContractNumberSensor(CoordinatorEntity, SensorEntity):
    """Sensor for contract number."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, account_number: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number
        
        is_single_account = len(coordinator.accounts) == 1
        self._attr_name = "Octopus Número de Contrato" if is_single_account else f"Octopus Número de Contrato ({account_number})"
        self._attr_unique_id = f"octopus_{account_number}_contract_number"
        self._attr_icon = "mdi:file-document-outline"

    @property
    def native_value(self) -> str | None:
        properties_data = self.coordinator.data.get("account_properties", {}).get(self._account_number, {})
        return properties_data.get("number")

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus Energy EV España",
            "manufacturer": "Lockevod",
            "model": "Spain",
        }


class OctopusAddressSensor(CoordinatorEntity, SensorEntity):
    """Sensor for property address."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, account_number: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number
        
        is_single_account = len(coordinator.accounts) == 1
        self._attr_name = "Octopus Dirección" if is_single_account else f"Octopus Dirección ({account_number})"
        self._attr_unique_id = f"octopus_{account_number}_address"
        self._attr_icon = "mdi:home"

    @property
    def native_value(self) -> str | None:
        properties_data = self.coordinator.data.get("account_properties", {}).get(self._account_number, {})
        if properties_data.get("properties"):
            return properties_data["properties"][0].get("address")
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus Energy EV España",
            "manufacturer": "Lockevod",
            "model": "Spain",
        }


class OctopusCupsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for electricity CUPS."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, account_number: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number
        
        is_single_account = len(coordinator.accounts) == 1
        self._attr_name = "Octopus CUPS Electricidad" if is_single_account else f"Octopus CUPS Electricidad ({account_number})"
        self._attr_unique_id = f"octopus_{account_number}_electricity_cups"
        self._attr_icon = "mdi:electric-switch"

    @property
    def native_value(self) -> str | None:
        meters_data = self.coordinator.data.get("property_meters", {}).get(self._account_number, {})
        electricity_points = meters_data.get("electricitySupplyPoints", [])
        if electricity_points:
            return electricity_points[0].get("cups")
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus Energy EV España",
            "manufacturer": "Lockevod",
            "model": "Spain",
        }


class OctopusContractTypeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for contract type."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, account_number: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number
        
        is_single_account = len(coordinator.accounts) == 1
        self._attr_name = "Octopus Tipo de Contrato" if is_single_account else f"Octopus Tipo de Contrato ({account_number})"
        self._attr_unique_id = f"octopus_{account_number}_contract_type"
        self._attr_icon = "mdi:file-contract"

    @property
    def native_value(self) -> str | None:
        agreement_data = self.coordinator.data.get("electricity_agreements", {}).get(self._account_number, {})
        active_agreement = agreement_data.get("activeAgreement")
        if active_agreement:
            return active_agreement.get("product", {}).get("displayName")
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus Energy EV España",
            "manufacturer": "Lockevod",
            "model": "Spain",
        }


class OctopusContractValidFromSensor(CoordinatorEntity, SensorEntity):
    """Sensor for contract valid from date."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, account_number: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number
        
        is_single_account = len(coordinator.accounts) == 1
        self._attr_name = "Octopus Contrato Válido Desde" if is_single_account else f"Octopus Contrato Válido Desde ({account_number})"
        self._attr_unique_id = f"octopus_{account_number}_contract_valid_from"
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:calendar-start"

    @property
    def native_value(self) -> str | None:
        agreement_data = self.coordinator.data.get("electricity_agreements", {}).get(self._account_number, {})
        active_agreement = agreement_data.get("activeAgreement")
        if active_agreement:
            valid_from = active_agreement.get("validFrom")
            if valid_from:
                try:
                    return datetime.fromisoformat(valid_from.replace('Z', '+00:00')).date()
                except ValueError:
                    pass
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus Energy EV España",
            "manufacturer": "Lockevod",
            "model": "Spain",
        }


class OctopusContractValidToSensor(CoordinatorEntity, SensorEntity):
    """Sensor for contract valid to date."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, account_number: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number
        
        is_single_account = len(coordinator.accounts) == 1
        self._attr_name = "Octopus Contrato Válido Hasta" if is_single_account else f"Octopus Contrato Válido Hasta ({account_number})"
        self._attr_unique_id = f"octopus_{account_number}_contract_valid_to"
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:calendar-end"

    @property
    def native_value(self) -> str | None:
        agreement_data = self.coordinator.data.get("electricity_agreements", {}).get(self._account_number, {})
        active_agreement = agreement_data.get("activeAgreement")
        if active_agreement:
            valid_to = active_agreement.get("validTo")
            if valid_to:
                try:
                    return datetime.fromisoformat(valid_to.replace('Z', '+00:00')).date()
                except ValueError:
                    pass
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus Energy EV España",
            "manufacturer": "Lockevod",
            "model": "Spain",
        }


# CHARGER REFERENCE SENSORS - Show contract info also in charger device

class OctopusChargerContractReferenceSensor(CoordinatorEntity, SensorEntity):
    """Reference sensor for contract number in charger device."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, account_number: str, device_id: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Cargador") if device else "Cargador"
        self._attr_name = f"{device_name} Número de Contrato"
        self._attr_unique_id = f"octopus_{device_id}_contract_number_ref"
        self._attr_icon = "mdi:file-document-outline"

    def _get_device_data(self) -> dict[str, Any] | None:
        """Get device data from coordinator."""
        try:
            devices = self.coordinator.data.get("devices", {}).get(self._account_number, [])
            for device in devices:
                if device.get("id") == self._device_id:
                    return device
        except (KeyError, TypeError, AttributeError):
            pass
        return None

    @property
    def native_value(self) -> str | None:
        properties_data = self.coordinator.data.get("account_properties", {}).get(self._account_number, {})
        return properties_data.get("number")

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information for charger."""
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)


class OctopusChargerAddressReferenceSensor(CoordinatorEntity, SensorEntity):
    """Reference sensor for address in charger device."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, account_number: str, device_id: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Cargador") if device else "Cargador"
        self._attr_name = f"{device_name} Dirección"
        self._attr_unique_id = f"octopus_{device_id}_address_ref"
        self._attr_icon = "mdi:home"

    def _get_device_data(self) -> dict[str, Any] | None:
        """Get device data from coordinator."""
        try:
            devices = self.coordinator.data.get("devices", {}).get(self._account_number, [])
            for device in devices:
                if device.get("id") == self._device_id:
                    return device
        except (KeyError, TypeError, AttributeError):
            pass
        return None

    @property
    def native_value(self) -> str | None:
        properties_data = self.coordinator.data.get("account_properties", {}).get(self._account_number, {})
        if properties_data.get("properties"):
            return properties_data["properties"][0].get("address")
        return None

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information for charger."""
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)


# EXISTING SENSORS - With some modifications

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
            "name": "Octopus Energy EV España",
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
    """Sensor for planned charging dispatches - FIXED."""

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
    def native_value(self) -> str:
        """Return planned dispatches info - FIXED to show meaningful message."""
        device = self._get_device_data()
        if not device:
            return "Dispositivo no encontrado"
        
        current_state = device.get("status", {}).get("currentState")
        dispatches = self.coordinator.data.get("planned_dispatches", {}).get(self._device_id, [])
        
        # Check if car is connected
        connected_states = ["SMART_CONTROL_CAPABLE", "BOOSTING", "SMART_CONTROL_IN_PROGRESS"]
        is_connected = current_state in connected_states
        
        if not is_connected:
            return "Coche no conectado"
        
        # Car is connected, show dispatch count
        dispatch_count = len(dispatches)
        if dispatch_count == 0:
            return "Sin sesiones programadas"
        elif dispatch_count == 1:
            return "1 sesión programada"
        else:
            return f"{dispatch_count} sesiones programadas"

    @property
    def available(self) -> bool:
        """Return if sensor is available - ALWAYS available."""
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        device = self._get_device_data()
        dispatches = self.coordinator.data.get("planned_dispatches", {}).get(self._device_id, [])
        
        attrs = {
            "device_id": self._device_id,
        }
        
        if device:
            current_state = device.get("status", {}).get("currentState")
            connected_states = ["SMART_CONTROL_CAPABLE", "BOOSTING", "SMART_CONTROL_IN_PROGRESS"]
            is_connected = current_state in connected_states
            
            attrs["is_connected"] = is_connected
            attrs["current_state"] = current_state
            attrs["dispatch_count"] = len(dispatches)
            
            if is_connected and dispatches:
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


class OctopusChargerLastEnergyAddedSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last charging session energy added - FIXED availability."""

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
        """Get last session data - FIXED to match API structure."""
        history_data = self.coordinator.data.get("charge_history", {}).get(self._device_id, [])
        if history_data and len(history_data) > 0:
            # history_data[0] is the device, get its charging sessions
            device_data = history_data[0]
            sessions = device_data.get("chargePointChargingSession", {}).get("edges", [])
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
        """ALWAYS available - show 0 if no data."""
        return True

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
            "name": "Octopus Energy EV España",
            "manufacturer": "Lockevod",
            "model": "Spain",
        }


class OctopusChargerLastSessionDurationSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last charging session duration - FIXED availability."""

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
        """Get last session data - FIXED to match API structure."""
        history_data = self.coordinator.data.get("charge_history", {}).get(self._device_id, [])
        if history_data and len(history_data) > 0:
            # history_data[0] is the device, get its charging sessions
            device_data = history_data[0]
            sessions = device_data.get("chargePointChargingSession", {}).get("edges", [])
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
        """ALWAYS available - show None if no data."""
        return True

    @property
    def device_info(self) -> dict[str, Any]:
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)


class OctopusChargerLastSessionCostSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last session cost - FIXED availability and cost handling."""

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
        """Get last session data - FIXED to match API structure.""" 
        history_data = self.coordinator.data.get("charge_history", {}).get(self._device_id, [])
        if history_data and len(history_data) > 0:
            # history_data[0] is the device, get its charging sessions
            device_data = history_data[0]
            sessions = device_data.get("chargePointChargingSession", {}).get("edges", [])
            if sessions:
                return sessions[0]["node"]
        return None

    @property
    def native_value(self) -> float:
        """Return cost - 0 if cost is null as user requested."""
        last_session = self._get_last_session()
        if last_session:
            cost_data = last_session.get("cost")
            if cost_data and cost_data.get("amount"):
                return float(cost_data["amount"])
        # Return 0 if cost is null (as user requested)
        return 0

    @property
    def available(self) -> bool:
        """ALWAYS available - show 0 if no data."""
        return True

    @property
    def device_info(self) -> dict[str, Any]:
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)