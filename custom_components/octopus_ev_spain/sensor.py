"""Sensor platform for Octopus Energy Spain."""
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
        
        # Add ledger sensors
        for ledger in account_data.get("ledgers", []):
            entities.append(OctopusLedgerSensor(coordinator, account_number, ledger))

        # Add account info sensors
        entities.extend([
            OctopusAccountSensor(coordinator, account_number, "properties_count"),
            OctopusAccountSensor(coordinator, account_number, "billing_address"),
        ])

    # Device sensors
    for account_number, devices in coordinator.data.get("devices", {}).items():
        for device in devices:
            device_id = device["id"]
            
            # Add device status sensors
            entities.extend([
                OctopusDeviceSensor(coordinator, account_number, device_id, "status"),
                OctopusDeviceSensor(coordinator, account_number, device_id, "current_state"),
                OctopusDeviceSensor(coordinator, account_number, device_id, "charging_sessions"),
                OctopusDeviceSensor(coordinator, account_number, device_id, "last_energy_added"),
                OctopusDeviceSensor(coordinator, account_number, device_id, "last_session_cost"),
                OctopusDeviceSensor(coordinator, account_number, device_id, "charging_mode"),
            ])

    # Measurements sensors
    for property_id, measurements_data in coordinator.data.get("measurements", {}).items():
        entities.append(OctopusPropertySensor(coordinator, property_id, "consumption"))

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
        
        ledger_name = self._ledger_type.replace("_", " ").title()
        self._attr_name = f"Octopus {ledger_name} Balance"
        self._attr_unique_id = f"octopus_{account_number}_{self._ledger_type.lower()}_balance"
        self._attr_native_unit_of_measurement = CURRENCY_EURO
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        _LOGGER.debug("Initialized ledger sensor %s", self._attr_unique_id)

    @property
    def native_value(self) -> float | None:
        """Return the balance value."""
        account_data = self.coordinator.data.get("accounts", {}).get(self._account_number, {})
        for ledger in account_data.get("ledgers", []):
            if ledger["ledgerType"] == self._ledger_type:
                return float(ledger["balance"]) / 100
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        account_data = self.coordinator.data.get("accounts", {}).get(self._account_number, {})
        for ledger in account_data.get("ledgers", []):
            if ledger["ledgerType"] == self._ledger_type:
                attrs = {
                    "ledger_number": ledger.get("number"),
                    "accepts_payments": ledger.get("acceptsPayments"),
                    "account_number": self._account_number,
                }
                
                # Add last statement info
                statements = ledger.get("statements", {}).get("edges", [])
                if statements:
                    last_statement = statements[0]["node"]
                    attrs.update({
                        "last_statement_amount": last_statement.get("amount"),
                        "last_statement_issued": last_statement.get("issuedDate"),
                        "last_statement_period_start": last_statement.get("consumptionStartDate"),
                        "last_statement_period_end": last_statement.get("consumptionEndDate"),
                    })
                
                return attrs
        return {}

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus EV Energy",
            "manufacturer": "Octopus EV Energy",
            "model": "Spain EV API",
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
            device_name = device.get("name", "Unknown Device")
            self._attr_name = f"{device_name} {sensor_type.replace('_', ' ').title()}"
            self._attr_unique_id = f"octopus_{device_id}_{sensor_type}"
            
            # Set appropriate attributes based on sensor type
            if sensor_type == "last_energy_added":
                self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
                self._attr_device_class = SensorDeviceClass.ENERGY
                self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            elif sensor_type == "last_session_cost":
                self._attr_native_unit_of_measurement = CURRENCY_EURO
                self._attr_device_class = SensorDeviceClass.MONETARY

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
        # Attach all device sensors to central integration device
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus EV Energy",
            "manufacturer": "Octopus EV Energy",
            "model": "Spain API",
        }

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        device = self._get_device_data()
        if not device:
            return None

        if self._sensor_type == "status":
            return device.get("status", {}).get("current")
        elif self._sensor_type == "current_state":
            return device.get("status", {}).get("currentState")
        elif self._sensor_type == "charging_sessions":
            sessions = device.get("chargePointChargingSession", {}).get("edges", [])
            return len(sessions)
        elif self._sensor_type == "last_energy_added":
            sessions = device.get("chargePointChargingSession", {}).get("edges", [])
            if sessions:
                energy_data = sessions[0]["node"].get("energyAdded", {})
                return float(energy_data.get("value", 0)) if energy_data.get("value") else None
        elif self._sensor_type == "last_session_cost":
            sessions = device.get("chargePointChargingSession", {}).get("edges", [])
            if sessions:
                cost = sessions[0]["node"].get("cost")
                return float(cost) if cost else None
        elif self._sensor_type == "charging_mode":
            preferences = device.get("preferences", {})
            return preferences.get("mode")

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

        if self._sensor_type == "charging_sessions":
            sessions = device.get("chargePointChargingSession", {}).get("edges", [])
            if sessions:
                latest_session = sessions[0]["node"]
                attrs.update({
                    "latest_start": latest_session.get("start"),
                    "latest_end": latest_session.get("end"),
                    "latest_type": latest_session.get("type"),
                    "latest_soc_change": latest_session.get("stateOfChargeChange"),
                    "latest_soc_final": latest_session.get("stateOfChargeFinal"),
                    "latest_problems": len(latest_session.get("problems", [])),
                })

        # Add preferences info
        preferences = device.get("preferences", {})
        if preferences:
            attrs.update({
                "target_type": preferences.get("targetType"),
                "unit": preferences.get("unit"),
                "schedules_count": len(preferences.get("schedules", [])),
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
        
        self._attr_name = f"Octopus {sensor_type.replace('_', ' ').title()}"
        self._attr_unique_id = f"octopus_{account_number}_{sensor_type}"
        _LOGGER.debug("Initialized account sensor %s", self._attr_unique_id)

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        account_data = self.coordinator.data.get("accounts", {}).get(self._account_number, {})
        
        if self._sensor_type == "properties_count":
            return len(account_data.get("properties", []))
        elif self._sensor_type == "billing_address":
            address_lines = [
                account_data.get("billingAddressLine1"),
                account_data.get("billingAddressLine2"),
                account_data.get("billingAddressLine3"),
                account_data.get("billingAddressLine4"),
                account_data.get("billingAddressLine5"),
            ]
            return ", ".join(filter(None, address_lines))

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        account_data = self.coordinator.data.get("accounts", {}).get(self._account_number, {})
        
        attrs = {
            "account_number": self._account_number,
            "billing_name": account_data.get("billingName"),
            "billing_postcode": account_data.get("billingAddressPostcode"),
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

        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        # Attach account sensors to central integration device
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus EV Energy",
            "manufacturer": "Octopus EV Energy",
            "model": "Spain API",
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
        
        self._attr_name = f"Property {property_id} {sensor_type.title()}"
        self._attr_unique_id = f"octopus_property_{property_id}_{sensor_type}"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        _LOGGER.debug("Initialized property sensor %s", self._attr_unique_id)

    @property
    def native_value(self) -> float | None:
        """Return the latest measurement value."""
        measurements_data = self.coordinator.data.get("measurements", {}).get(self._property_id, {})
        measurements = measurements_data.get("measurements", {}).get("edges", [])
        
        if measurements:
            # Return the latest measurement
            latest = measurements[-1]["node"]
            return float(latest.get("value", 0))
        
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
                "reading_direction": latest.get("metaData", {}).get("utilityFilters", {}).get("readingDirection"),
            })

        # Add supply point info
        electricity_points = measurements_data.get("electricitySupplyPoints", [])
        gas_points = measurements_data.get("gasSupplyPoints", [])
        
        if electricity_points:
            attrs["electricity_supply_points"] = [
                {"id": point.get("id"), "cups": point.get("cups")}
                for point in electricity_points
            ]
        
        if gas_points:
            attrs["gas_supply_points"] = [
                {"id": point.get("id"), "cups": point.get("cups")}
                for point in gas_points
            ]

        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device = self._get_device_data()
        if not device:
            return {}
            
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus EV Energy",
            "manufacturer": "Octopus EV Energy",
            "model": "Spain API",
        }