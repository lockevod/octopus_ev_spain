"""Sensor platform for Octopus Energy Spain - CORRECTED based on real data structure."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CURRENCY_EURO,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ELECTRICITY_LEDGER, SOLAR_WALLET_LEDGER, GAS_LEDGER
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

    # Account-level sensors
    for account_number in coordinator.accounts:
        account_data = coordinator.data.get("accounts", {}).get(account_number, {})
        
        # Add ledger sensors (balance sensors)
        for ledger in account_data.get("ledgers", []):
            entities.append(OctopusLedgerSensor(coordinator, account_number, ledger))

        # Add account info sensors
        entities.extend([
            OctopusAccountSensor(coordinator, account_number, "properties_count"),
            OctopusAccountSensor(coordinator, account_number, "address"),
        ])

    # Device sensors
    for account_number, devices in coordinator.data.get("devices", {}).items():
        for device in devices:
            device_id = device["id"]
            
            # Add device status sensors
            entities.extend([
                OctopusDeviceSensor(coordinator, account_number, device_id, "status"),
                OctopusDeviceSensor(coordinator, account_number, device_id, "current_state"),
                OctopusDeviceSensor(coordinator, account_number, device_id, "charging_sessions_count"),
                OctopusDeviceSensor(coordinator, account_number, device_id, "last_energy_added"),
                OctopusDeviceSensor(coordinator, account_number, device_id, "last_session_cost"),
                OctopusDeviceSensor(coordinator, account_number, device_id, "last_soc_final"),
                OctopusDeviceSensor(coordinator, account_number, device_id, "charging_mode"),
                OctopusDeviceSensor(coordinator, account_number, device_id, "scheduled_charges"),
            ])

    # Property measurements sensors
    for property_id, measurements_data in coordinator.data.get("measurements", {}).items():
        entities.extend([
            OctopusPropertySensor(coordinator, property_id, "daily_consumption"),
            OctopusPropertySensor(coordinator, property_id, "total_measurements"),
        ])

    async_add_entities(entities)


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
        
        # Create friendly names
        ledger_names = {
            "SPAIN_ELECTRICITY_LEDGER": "Electricidad",
            "SPAIN_GAS_LEDGER": "Gas", 
            "SOLAR_WALLET_LEDGER": "Monedero Solar"
        }
        
        ledger_name = ledger_names.get(self._ledger_type, self._ledger_type.replace("_", " ").title())
        self._attr_name = f"Octopus {ledger_name} Saldo"
        self._attr_unique_id = f"octopus_{account_number}_{self._ledger_type.lower()}_balance"
        self._attr_native_unit_of_measurement = CURRENCY_EURO
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:wallet"
        
        _LOGGER.debug("Initialized ledger sensor %s", self._attr_unique_id)

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
            "name": "Octopus Energy España",
            "manufacturer": "Octopus Energy",
            "model": "API España",
        }


class OctopusDeviceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for device information."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        device_id: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_number = account_number
        self._device_id = device_id
        self._sensor_type = sensor_type
        
        device = self._get_device_data()
        if device:
            device_name = device.get("name", "Dispositivo Desconocido")
            sensor_name = sensor_type.replace('_', ' ').title()
            self._attr_name = f"{device_name} {sensor_name}"
            self._attr_unique_id = f"octopus_{device_id}_{sensor_type}"
            
            # Set appropriate attributes based on sensor type
            if sensor_type == "last_energy_added":
                self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
                self._attr_device_class = SensorDeviceClass.ENERGY
                self._attr_state_class = SensorStateClass.TOTAL
                self._attr_icon = "mdi:lightning-bolt"
            elif sensor_type == "last_session_cost":
                self._attr_native_unit_of_measurement = CURRENCY_EURO
                self._attr_device_class = SensorDeviceClass.MONETARY
                self._attr_icon = "mdi:currency-eur"
            elif sensor_type == "last_soc_final":
                self._attr_native_unit_of_measurement = PERCENTAGE
                self._attr_device_class = SensorDeviceClass.BATTERY
                self._attr_icon = "mdi:battery"
            elif sensor_type == "current_state":
                self._attr_icon = "mdi:state-machine"
            elif sensor_type == "status":
                self._attr_icon = "mdi:information"
            elif sensor_type == "charging_sessions_count":
                self._attr_icon = "mdi:counter"
            elif sensor_type == "charging_mode":
                self._attr_icon = "mdi:tune"
            elif sensor_type == "scheduled_charges":
                self._attr_icon = "mdi:calendar-clock"

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
    def native_value(self) -> Any:
        """Return the sensor value based on real data structure."""
        device = self._get_device_data()
        if not device:
            return None

        if self._sensor_type == "status":
            return device.get("status", {}).get("current")
        
        elif self._sensor_type == "current_state":
            return device.get("status", {}).get("currentState")
        
        elif self._sensor_type == "charging_sessions_count":
            sessions = device.get("chargePointChargingSession", {}).get("edges", [])
            return len(sessions)
        
        elif self._sensor_type == "last_energy_added":
            sessions = device.get("chargePointChargingSession", {}).get("edges", [])
            if sessions:
                energy_data = sessions[0]["node"].get("energyAdded", {})
                value = energy_data.get("value")
                return float(value) if value else None
            return None
        
        elif self._sensor_type == "last_session_cost":
            sessions = device.get("chargePointChargingSession", {}).get("edges", [])
            if sessions:
                cost_data = sessions[0]["node"].get("cost", {})
                amount = cost_data.get("amount")
                return float(amount) if amount else None
            return None
        
        elif self._sensor_type == "last_soc_final":
            sessions = device.get("chargePointChargingSession", {}).get("edges", [])
            if sessions:
                soc_final = sessions[0]["node"].get("stateOfChargeFinal")
                return float(soc_final) if soc_final else None
            return None
        
        elif self._sensor_type == "charging_mode":
            preferences = device.get("preferences", {})
            return preferences.get("mode")
        
        elif self._sensor_type == "scheduled_charges":
            preferences = device.get("preferences", {})
            schedules = preferences.get("schedules", [])
            return len(schedules)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        device = self._get_device_data()
        if not device:
            return {}

        attrs = {
            "device_type": device.get("deviceType"),
            "provider": device.get("provider"),
            "property_id": device.get("propertyId"),
            "is_suspended": device.get("status", {}).get("isSuspended"),
            "account_number": self._account_number,
        }

        if self._sensor_type == "charging_sessions_count":
            sessions = device.get("chargePointChargingSession", {}).get("edges", [])
            if sessions:
                latest_session = sessions[0]["node"]
                attrs.update({
                    "latest_start": latest_session.get("start"),
                    "latest_end": latest_session.get("end"),
                    "latest_type": latest_session.get("type"),
                    "latest_soc_change": latest_session.get("stateOfChargeChange"),
                    "latest_problems": len(latest_session.get("problems", [])),
                })

        elif self._sensor_type == "charging_mode":
            preferences = device.get("preferences", {})
            if preferences:
                attrs.update({
                    "target_type": preferences.get("targetType"),
                    "unit": preferences.get("unit"),
                    "schedules": preferences.get("schedules", []),
                })

        return attrs


class OctopusAccountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for account information."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        account_number: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_number = account_number
        self._sensor_type = sensor_type
        
        sensor_names = {
            "properties_count": "Número de Propiedades",
            "address": "Dirección Principal"
        }
        
        self._attr_name = f"Octopus {sensor_names.get(sensor_type, sensor_type.replace('_', ' ').title())}"
        self._attr_unique_id = f"octopus_{account_number}_{sensor_type}"
        self._attr_icon = "mdi:home" if sensor_type == "properties_count" else "mdi:map-marker"
        
        _LOGGER.debug("Initialized account sensor %s", self._attr_unique_id)

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        account_data = self.coordinator.data.get("accounts", {}).get(self._account_number, {})
        
        if self._sensor_type == "properties_count":
            return len(account_data.get("properties", []))
        
        elif self._sensor_type == "address":
            properties = account_data.get("properties", [])
            if properties:
                return properties[0].get("address", "No disponible")
            return "No disponible"

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        account_data = self.coordinator.data.get("accounts", {}).get(self._account_number, {})
        
        attrs = {
            "account_number": self._account_number,
        }

        if self._sensor_type == "properties_count":
            properties = account_data.get("properties", [])
            if properties:
                attrs["properties"] = [
                    {
                        "id": prop.get("id"),
                        "address": prop.get("address"),
                        "postcode": prop.get("postcode"),
                    }
                    for prop in properties
                ]

        elif self._sensor_type == "address":
            properties = account_data.get("properties", [])
            if properties:
                prop = properties[0]
                attrs.update({
                    "property_id": prop.get("id"),
                    "postcode": prop.get("postcode"),
                    "split_address": prop.get("splitAddress", []),
                    "occupancy_periods": prop.get("occupancyPeriods", []),
                })

        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus Energy España",
            "manufacturer": "Octopus Energy",
            "model": "API España",
        }


class OctopusPropertySensor(CoordinatorEntity, SensorEntity):
    """Sensor for property measurements."""

    def __init__(
        self,
        coordinator: OctopusSpainDataUpdateCoordinator,
        property_id: str,
        sensor_type: str,
    ) -> None:
        super().__init__(coordinator)
        self._property_id = property_id
        self._sensor_type = sensor_type
        
        sensor_names = {
            "daily_consumption": "Consumo Diario",
            "total_measurements": "Total Mediciones"
        }
        
        self._attr_name = f"Propiedad {property_id} {sensor_names.get(sensor_type, sensor_type.title())}"
        self._attr_unique_id = f"octopus_property_{property_id}_{sensor_type}"
        
        if sensor_type == "daily_consumption":
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_icon = "mdi:flash"
        else:
            self._attr_icon = "mdi:counter"
            
        _LOGGER.debug("Initialized property sensor %s", self._attr_unique_id)

    @property
    def native_value(self) -> float | None:
        """Return the measurement value."""
        measurements_data = self.coordinator.data.get("measurements", {}).get(self._property_id, {})
        measurements = measurements_data.get("measurements", {}).get("edges", [])
        
        if self._sensor_type == "daily_consumption":
            if measurements:
                # Return the latest measurement
                latest = measurements[-1]["node"]
                value = latest.get("value")
                return float(value) if value else None
            return None
            
        elif self._sensor_type == "total_measurements":
            return len(measurements)
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        measurements_data = self.coordinator.data.get("measurements", {}).get(self._property_id, {})
        measurements = measurements_data.get("measurements", {}).get("edges", [])
        
        attrs = {
            "property_id": self._property_id,
            "measurements_count": len(measurements),
        }

        if measurements:
            latest = measurements[-1]["node"]
            attrs.update({
                "latest_measurement_start": latest.get("startAt"),
                "latest_measurement_end": latest.get("endAt"),
                "latest_measurement_unit": latest.get("unit"),
                "latest_measurement_type": latest.get("__typename"),
            })
            
            # Add metadata if available
            metadata = latest.get("metaData", {})
            if metadata:
                utility_filters = metadata.get("utilityFilters", {})
                if utility_filters:
                    attrs["reading_direction"] = utility_filters.get("readingDirection")

        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        """Attach property sensors to central integration device."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus Energy España",
            "manufacturer": "Octopus Energy",
            "model": "API España",
        }