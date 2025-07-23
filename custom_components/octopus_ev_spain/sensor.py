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

from .const import DOMAIN, ELECTRICITY_LEDGER, SOLAR_WALLET_LEDGER, LEDGER_NAMES
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
        
        # Add existing ledger sensors - FILTER OUT GAS LEDGERS
        for ledger in account_data.get("ledgers", []):
            ledger_type = ledger.get("ledgerType")
            # Only create sensors for electricity and solar wallet, NOT gas
            if ledger_type in [ELECTRICITY_LEDGER, SOLAR_WALLET_LEDGER]:
                entities.append(OctopusLedgerSensor(coordinator, account_number, ledger))
            else:
                _LOGGER.debug("Skipping ledger type: %s (not electricity/solar)", ledger_type)
        
        # Add invoice sensor (from original repo)
        billing_data = coordinator.data.get("billing_info", {}).get(account_number, {})
        if billing_data.get("last_invoice") is not None:
            entities.append(OctopusInvoiceSensor(coordinator, account_number))

        # Add NEW pricing sensors if available
        agreement_prices = coordinator.data.get("agreement_prices", {}).get(account_number, {})
        hourly_prices = coordinator.data.get("hourly_prices", {}).get(account_number, {})
        if agreement_prices.get("product", {}).get("prices"):
            entities.append(OctopusTariffPricesSensor(coordinator, account_number))
        if hourly_prices.get("today") or hourly_prices.get("tomorrow"):
            entities.append(OctopusCurrentPriceSensor(coordinator, account_number))
            entities.append(OctopusCurrentPriceEVSensor(coordinator, account_number))

    # Device sensors
    for account_number, devices in coordinator.data.get("devices", {}).items():
        for device in devices:
            device_id = device["id"]
            device_type = device.get("__typename")
            
            if device_type == "SmartFlexChargePoint":
                # Add charger-specific sensors (order: contrato, dirección, estado, planificada, fecha, duración, energía, coste)
                entities.extend([
                    # NEW: Reference sensors for contract info in charger device (FIRST)
                    OctopusChargerContractReferenceSensor(coordinator, account_number, device_id),
                    OctopusChargerAddressReferenceSensor(coordinator, account_number, device_id),
                    OctopusDeviceStateSensor(coordinator, account_number, device_id),
                    OctopusChargerPlannedDispatchesSensor(coordinator, device_id),
                    # NEW: Automation-friendly sensors for planned dispatches
                    OctopusChargerNextSessionStartSensor(coordinator, device_id),
                    OctopusChargerNextSessionEndSensor(coordinator, device_id),
                    OctopusChargerTotalHoursTodaySensor(coordinator, device_id),
                    # NEW: Date of last charge session
                    OctopusChargerLastSessionDateSensor(coordinator, device_id),
                    OctopusChargerLastSessionDurationSensor(coordinator, device_id),
                    OctopusChargerLastEnergyAddedSensor(coordinator, device_id),
                    OctopusChargerLastSessionCostSensor(coordinator, device_id),
                    # REMOVED: OctopusChargerPreferencesSensor - no aporta valor según usuario
                ])

    async_add_entities(entities)


def _safe_device_info(device_id: str, device: dict[str, Any] | None) -> dict[str, Any]:
    """Safely create device info."""
    if not device:
        return {
            "identifiers": {(DOMAIN, device_id)},
            "name": "Unknown Device",  # This will be translated by HA
            "manufacturer": "Lockevod",
            "model": "Unknown",
        }


class OctopusCurrentPriceEVSensor(CoordinatorEntity, SensorEntity):
    """Sensor for current electricity price with EV charging discount."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, account_number: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number
        
        is_single_account = len(coordinator.accounts) == 1
        self._attr_name = "Octopus Precio Actual EV" if is_single_account else f"Octopus Precio Actual EV ({account_number})"
        self._attr_unique_id = f"octopus_{account_number}_12_current_price_ev"  # Added 12_ prefix
        self._attr_native_unit_of_measurement = "€/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_icon = "mdi:car-electric"

    def _get_charger_device_id(self) -> str | None:
        """Find the first charger device for this account."""
        devices = self.coordinator.data.get("devices", {}).get(self._account_number, [])
        for device in devices:
            if device.get("__typename") == "SmartFlexChargePoint":
                return device.get("id")
        return None

    def _is_charger_connected(self, device_id: str) -> bool:
        """Check if charger is connected."""
        devices = self.coordinator.data.get("devices", {}).get(self._account_number, [])
        for device in devices:
            if device.get("id") == device_id:
                current_state = device.get("status", {}).get("currentState")
                connected_states = ["SMART_CONTROL_CAPABLE", "BOOSTING", "SMART_CONTROL_IN_PROGRESS"]
                return current_state in connected_states
        return False

    def _get_current_price_with_ev_discount(self) -> float | None:
        """Get current price with EV discount applied if charging is scheduled."""
        import pytz
        
        # Get charger device
        device_id = self._get_charger_device_id()
        if not device_id:
            # No charger found, return normal price
            return self._get_normal_current_price()
        
        # Check if charger is connected
        if not self._is_charger_connected(device_id):
            # Not connected, return normal price
            return self._get_normal_current_price()
        
        # Get current time
        tz = pytz.timezone('Europe/Madrid')
        now = datetime.now(tz)
        
        # Check if we're currently in a scheduled charging period
        dispatches = self.coordinator.data.get("planned_dispatches", {}).get(device_id, [])
        for dispatch in dispatches:
            start_time = dispatch.get("start")
            end_time = dispatch.get("end")
            
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    
                    if start_dt <= now < end_dt:
                        # We're in a charging period, return EV price
                        return 0.068
                except (ValueError, TypeError):
                    continue
        
        # Not in charging period, return normal price
        return self._get_normal_current_price()

    def _get_normal_current_price(self) -> float | None:
        """Get normal current price (same logic as OctopusCurrentPriceSensor)."""
        import pytz
        
        hourly_data = self.coordinator.data.get("hourly_prices", {}).get(self._account_number, {})
        if not hourly_data:
            return None
        
        # Get current time in Spanish timezone
        tz = pytz.timezone('Europe/Madrid')
        now = datetime.now(tz)
        
        # Check today's prices first
        today_prices = hourly_data.get("today", [])
        for price_entry in today_prices:
            try:
                start_dt = datetime.fromisoformat(price_entry["start"])
                end_dt = datetime.fromisoformat(price_entry["end"])
                
                if start_dt <= now < end_dt:
                    return float(price_entry["value"])
            except (ValueError, TypeError, KeyError):
                continue
        
        # Fallback: calculate directly from tariff
        tariff_data = self.coordinator.data.get("agreement_prices", {}).get(self._account_number, {})
        prices = tariff_data.get("product", {}).get("prices", {})
        variable_terms = prices.get("variableTerm", [])
        
        if len(variable_terms) >= 3:
            price_peak = float(variable_terms[0])
            price_standard = float(variable_terms[1]) 
            price_valley = float(variable_terms[2])
            
            return self._calculate_spanish_price(now, price_peak, price_standard, price_valley)
        
        return None

    def _calculate_spanish_price(self, dt: datetime, price_peak: float, price_standard: float, price_valley: float) -> float:
        """Calculate price using Spanish tariff rules."""
        weekday = dt.weekday()  # 0=Monday, 6=Sunday
        hour = dt.hour
        
        # Weekend: Always VALLE
        if weekday >= 5:
            return price_valley
            
        # Weekdays: Time-based pricing
        if (10 <= hour < 14) or (18 <= hour < 22):  # PUNTA
            return price_peak
        elif (8 <= hour < 10) or (14 <= hour < 18) or (22 <= hour < 24):  # LLANO
            return price_standard
        else:  # VALLE: 0:00-8:00
            return price_valley

    @property
    def native_value(self) -> float | None:
        """Return current electricity price with EV discount."""
        return self._get_current_price_with_ev_discount()

    @property
    def available(self) -> bool:
        """Return if sensor is available."""
        hourly_data = self.coordinator.data.get("hourly_prices", {}).get(self._account_number, {})
        tariff_data = self.coordinator.data.get("agreement_prices", {}).get(self._account_number, {})
        
        # Available if we have either hourly data or tariff data
        has_hourly = bool(hourly_data.get("today") or hourly_data.get("tomorrow"))
        has_tariff = bool(tariff_data.get("product", {}).get("prices"))
        
        return has_hourly or has_tariff

    def _generate_ev_prices_for_day(self, target_date, base_prices: list) -> list:
        """Generate EV prices for a specific day applying EV discount to charging periods."""
        device_id = self._get_charger_device_id()
        if not device_id or not self._is_charger_connected(device_id):
            # No charger or not connected, return base prices
            return base_prices
        
        # Get planned dispatches
        dispatches = self.coordinator.data.get("planned_dispatches", {}).get(device_id, [])
        if not dispatches:
            return base_prices
        
        # Create modified prices list
        ev_prices = []
        for price_entry in base_prices:
            try:
                start_dt = datetime.fromisoformat(price_entry["start"])
                end_dt = datetime.fromisoformat(price_entry["end"])
                
                # Check if this interval overlaps with any charging dispatch
                is_charging_period = False
                for dispatch in dispatches:
                    dispatch_start = dispatch.get("start")
                    dispatch_end = dispatch.get("end")
                    
                    if dispatch_start and dispatch_end:
                        try:
                            dispatch_start_dt = datetime.fromisoformat(dispatch_start.replace('Z', '+00:00'))
                            dispatch_end_dt = datetime.fromisoformat(dispatch_end.replace('Z', '+00:00'))
                            
                            # Check if intervals overlap
                            if (start_dt < dispatch_end_dt and end_dt > dispatch_start_dt):
                                is_charging_period = True
                                break
                        except (ValueError, TypeError):
                            continue
                
                # Use EV price if in charging period, otherwise use normal price
                price_value = 0.068 if is_charging_period else price_entry["value"]
                
                ev_price_entry = {
                    "start": price_entry["start"],
                    "end": price_entry["end"],
                    "value": price_value
                }
                ev_prices.append(ev_price_entry)
                
            except (ValueError, TypeError, KeyError):
                # If parsing fails, use original entry
                ev_prices.append(price_entry)
        
        return ev_prices

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return hourly prices for today and tomorrow with EV discount applied."""
        hourly_data = self.coordinator.data.get("hourly_prices", {}).get(self._account_number, {})
        
        # Get base prices
        base_today = hourly_data.get("today", [])
        base_tomorrow = hourly_data.get("tomorrow", [])
        
        # Apply EV discount
        import pytz
        tz = pytz.timezone('Europe/Madrid')
        today = datetime.now(tz).date()
        tomorrow = today + timedelta(days=1)
        
        ev_today = self._generate_ev_prices_for_day(today, base_today)
        ev_tomorrow = self._generate_ev_prices_for_day(tomorrow, base_tomorrow)
        
        attrs = {
            "account_number": self._account_number,
            "today": ev_today,
            "tomorrow": ev_tomorrow,
        }
        
        # Add charger info
        device_id = self._get_charger_device_id()
        if device_id:
            attrs["charger_device_id"] = device_id
            attrs["charger_connected"] = self._is_charger_connected(device_id)
            
            # Add dispatch info
            dispatches = self.coordinator.data.get("planned_dispatches", {}).get(device_id, [])
            attrs["charging_sessions_count"] = len(dispatches)
            
            if dispatches:
                charging_periods = []
                for dispatch in dispatches:
                    start_time = dispatch.get("start")
                    end_time = dispatch.get("end")
                    if start_time and end_time:
                        charging_periods.append({
                            "start": start_time,
                            "end": end_time
                        })
                attrs["charging_periods"] = charging_periods
        else:
            attrs["charger_device_id"] = None
            attrs["charger_connected"] = False
            attrs["charging_sessions_count"] = 0
        
        # Add convenience attributes
        if ev_today:
            prices_values = [float(p["value"]) for p in ev_today if "value" in p]
            if prices_values:
                attrs["today_min_price"] = min(prices_values)
                attrs["today_max_price"] = max(prices_values)
                attrs["today_avg_price"] = sum(prices_values) / len(prices_values)
                attrs["today_prices_count"] = len(prices_values)
                
                # Count EV discounted periods
                ev_periods = [p for p in ev_today if p.get("value") == 0.068]
                attrs["today_ev_discount_periods"] = len(ev_periods)
        
        if ev_tomorrow:
            prices_values = [float(p["value"]) for p in ev_tomorrow if "value" in p]
            if prices_values:
                attrs["tomorrow_min_price"] = min(prices_values)
                attrs["tomorrow_max_price"] = max(prices_values)
                attrs["tomorrow_avg_price"] = sum(prices_values) / len(prices_values)
                attrs["tomorrow_prices_count"] = len(prices_values)
                
                # Count EV discounted periods  
                ev_periods = [p for p in ev_tomorrow if p.get("value") == 0.068]
                attrs["tomorrow_ev_discount_periods"] = len(ev_periods)
        
        # Add current period info
        import pytz
        tz = pytz.timezone('Europe/Madrid')
        now = datetime.now(tz)
        
        for price_entry in ev_today:
            try:
                start_dt = datetime.fromisoformat(price_entry["start"])
                end_dt = datetime.fromisoformat(price_entry["end"])
                
                if start_dt <= now < end_dt:
                    attrs["current_period_start"] = price_entry["start"]
                    attrs["current_period_end"] = price_entry["end"]
                    attrs["current_period_value"] = price_entry["value"]
                    attrs["current_period_is_ev_discount"] = (price_entry["value"] == 0.068)
                    break
            except (ValueError, TypeError, KeyError):
                continue
        
        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus Energy EV España",
            "manufacturer": "Lockevod",
            "model": "Spain",
        }
        
    return {
        "identifiers": {(DOMAIN, device_id)},
        "name": device.get("name", "Unknown Device"),
        "manufacturer": "Lockevod",
        "model": f"{device.get('__typename', 'Unknown')} ({device.get('provider', 'Unknown')})",
        "sw_version": device.get("deviceType", "Unknown"),
    }


# NEW SENSORS - Contract and Property Information

class OctopusContractNumberSensor(CoordinatorEntity, SensorEntity):
    """Sensor for contract number."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, account_number: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number
        
        is_single_account = len(coordinator.accounts) == 1
        self._attr_name = "Octopus Número de Contrato" if is_single_account else f"Octopus Número de Contrato ({account_number})"
        self._attr_unique_id = f"octopus_{account_number}_01_contract_number"  # FIXED: Added 01_ prefix
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
        self._attr_unique_id = f"octopus_{account_number}_02_address"  # FIXED: Added 02_ prefix
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
        self._attr_unique_id = f"octopus_{account_number}_03_electricity_cups"  # FIXED: Added 03_ prefix
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
        self._attr_unique_id = f"octopus_{account_number}_04_contract_type"  # FIXED: Added 04_ prefix
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
        self._attr_unique_id = f"octopus_{account_number}_05_contract_valid_from"  # FIXED: Added 05_ prefix
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
        self._attr_unique_id = f"octopus_{account_number}_06_contract_valid_to"  # FIXED: Added 06_ prefix
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
        device_name = device.get("name", "Charger") if device else "Charger"
        self._attr_name = f"{device_name} Contract Number"
        self._attr_unique_id = f"octopus_{device_id}_01_contract_number_ref"
        self._attr_translation_key = "contract_number"  # Use translation key
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
        device_name = device.get("name", "Charger") if device else "Charger"
        self._attr_name = f"{device_name} Address"
        self._attr_unique_id = f"octopus_{device_id}_02_address_ref"
        self._attr_translation_key = "address"  # Use translation key
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
        
        # FIXED: Added numeric prefixes for proper ordering
        if self._ledger_type == ELECTRICITY_LEDGER:
            self._attr_unique_id = f"octopus_{account_number}_07_electricity_balance"
        elif self._ledger_type == SOLAR_WALLET_LEDGER:
            self._attr_unique_id = f"octopus_{account_number}_08_solar_wallet_balance"
        else:
            # Fallback for any other ledger types
            self._attr_unique_id = f"octopus_{account_number}_99_{self._ledger_type.lower()}_balance"
            
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
        self._attr_unique_id = f"octopus_{account_number}_09_last_invoice"  # FIXED: Added 09_ prefix
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


# NEW PRICING SENSORS

class OctopusTariffPricesSensor(CoordinatorEntity, SensorEntity):
    """Sensor for tariff price structure."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, account_number: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number
        
        is_single_account = len(coordinator.accounts) == 1
        self._attr_name = "Octopus Precios Tarifa" if is_single_account else f"Octopus Precios Tarifa ({account_number})"
        self._attr_unique_id = f"octopus_{account_number}_10_tariff_prices"  # Added 10_ prefix
        self._attr_icon = "mdi:currency-eur"

    @property
    def native_value(self) -> str | None:
        """Return tariff price summary."""
        prices_data = self.coordinator.data.get("agreement_prices", {}).get(self._account_number, {})
        prices = prices_data.get("product", {}).get("prices", {})
        
        if not prices:
            return "No disponible"
        
        variable_terms = prices.get("variableTerm", [])
        if variable_terms:
            # Show the main variable term (usually the first one for standard rate)
            main_rate = variable_terms[0] if len(variable_terms) > 0 else 0
            
            # Check if we have different rates (indicating time-of-use pricing)
            if len(variable_terms) > 1:
                min_rate = min(variable_terms)
                max_rate = max(variable_terms)
                return f"Variable: {min_rate:.3f} - {max_rate:.3f} €/kWh"
            else:
                return f"Variable: {main_rate:.3f} €/kWh"
        
        return "Sin datos de precios"

    @property
    def available(self) -> bool:
        """Return if sensor is available."""
        prices_data = self.coordinator.data.get("agreement_prices", {}).get(self._account_number, {})
        return bool(prices_data.get("product", {}).get("prices"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes with detailed pricing."""
        prices_data = self.coordinator.data.get("agreement_prices", {}).get(self._account_number, {})
        prices = prices_data.get("product", {}).get("prices", {})
        
        attrs = {
            "account_number": self._account_number,
        }
        
        if prices:
            # Fixed terms
            fixed_terms = prices.get("fixedTerm", [])
            fixed_units = prices.get("fixedTermUnits", "")
            if fixed_terms:
                attrs["fixed_term_power"] = f"{fixed_terms[0]} {fixed_units}" if len(fixed_terms) > 0 else None
                attrs["fixed_term_energy"] = f"{fixed_terms[1]} {fixed_units}" if len(fixed_terms) > 1 else None
            
            # Variable terms
            variable_terms = prices.get("variableTerm", [])
            variable_units = prices.get("variableTermUnits", "")
            if variable_terms:
                attrs["variable_term_units"] = variable_units
                attrs["variable_terms_count"] = len(variable_terms)
                
                # Intelligent GO typically has 3 rates: Peak, Standard, Off-peak
                if len(variable_terms) >= 3:
                    attrs["rate_peak"] = f"{variable_terms[0]} {variable_units}"      # Peak (most expensive)
                    attrs["rate_standard"] = f"{variable_terms[1]} {variable_units}"  # Standard
                    attrs["rate_offpeak"] = f"{variable_terms[2]} {variable_units}"   # Off-peak (cheapest)
                elif len(variable_terms) == 2:
                    attrs["rate_peak"] = f"{variable_terms[0]} {variable_units}"
                    attrs["rate_offpeak"] = f"{variable_terms[1]} {variable_units}"
                elif len(variable_terms) == 1:
                    attrs["rate_standard"] = f"{variable_terms[0]} {variable_units}"
                
                # Add all rates as list for automations
                attrs["all_variable_rates"] = [float(rate) for rate in variable_terms]
            
            # Adjustment mechanism
            adjustment = prices.get("adjustmentMechanism")
            if adjustment:
                attrs["adjustment_average"] = adjustment.get("average")
                attrs["adjustment_units"] = adjustment.get("units")
        
        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Octopus Energy EV España",
            "manufacturer": "Lockevod",
            "model": "Spain",
        }


class OctopusCurrentPriceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for current electricity price."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, account_number: str) -> None:
        super().__init__(coordinator)
        self._account_number = account_number
        
        is_single_account = len(coordinator.accounts) == 1
        self._attr_name = "Octopus Precio Actual" if is_single_account else f"Octopus Precio Actual ({account_number})"
        self._attr_unique_id = f"octopus_{account_number}_11_current_price"  # Added 11_ prefix
        self._attr_native_unit_of_measurement = "€/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_icon = "mdi:cash"

    def _get_current_price(self) -> float | None:
        """Get current price based on time from generated hourly data."""
        import pytz
        
        hourly_data = self.coordinator.data.get("hourly_prices", {}).get(self._account_number, {})
        if not hourly_data:
            return None
        
        # Get current time in Spanish timezone
        tz = pytz.timezone('Europe/Madrid')
        now = datetime.now(tz)
        
        # Check today's prices first
        today_prices = hourly_data.get("today", [])
        for price_entry in today_prices:
            try:
                start_dt = datetime.fromisoformat(price_entry["start"])
                end_dt = datetime.fromisoformat(price_entry["end"])
                
                if start_dt <= now < end_dt:
                    return float(price_entry["value"])
            except (ValueError, TypeError, KeyError):
                continue
        
        # Fallback: calculate directly from tariff if no match found
        tariff_data = self.coordinator.data.get("agreement_prices", {}).get(self._account_number, {})
        prices = tariff_data.get("product", {}).get("prices", {})
        variable_terms = prices.get("variableTerm", [])
        
        if len(variable_terms) >= 3:
            # Use Spanish tariff logic
            price_peak = float(variable_terms[0])
            price_standard = float(variable_terms[1]) 
            price_valley = float(variable_terms[2])
            
            return self._calculate_spanish_price(now, price_peak, price_standard, price_valley)
        
        return None
    
    def _calculate_spanish_price(self, dt: datetime, price_peak: float, price_standard: float, price_valley: float) -> float:
        """Calculate price using Spanish tariff rules."""
        weekday = dt.weekday()  # 0=Monday, 6=Sunday
        hour = dt.hour
        
        # Weekend: Always VALLE
        if weekday >= 5:
            return price_valley
            
        # Weekdays: Time-based pricing
        if (10 <= hour < 14) or (18 <= hour < 22):  # PUNTA
            return price_peak
        elif (8 <= hour < 10) or (14 <= hour < 18) or (22 <= hour < 24):  # LLANO
            return price_standard
        else:  # VALLE: 0:00-8:00
            return price_valley

    @property
    def native_value(self) -> float | None:
        """Return current electricity price."""
        return self._get_current_price()

    @property
    def available(self) -> bool:
        """Return if sensor is available."""
        hourly_data = self.coordinator.data.get("hourly_prices", {}).get(self._account_number, {})
        tariff_data = self.coordinator.data.get("agreement_prices", {}).get(self._account_number, {})
        
        # Available if we have either hourly data or tariff data
        has_hourly = bool(hourly_data.get("today") or hourly_data.get("tomorrow"))
        has_tariff = bool(tariff_data.get("product", {}).get("prices"))
        
        return has_hourly or has_tariff

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return hourly prices for today and tomorrow."""
        hourly_data = self.coordinator.data.get("hourly_prices", {}).get(self._account_number, {})
        
        attrs = {
            "account_number": self._account_number,
            "today": hourly_data.get("today", []),
            "tomorrow": hourly_data.get("tomorrow", []),
        }
        
        # Add some convenience attributes
        today_prices = hourly_data.get("today", [])
        tomorrow_prices = hourly_data.get("tomorrow", [])
        
        if today_prices:
            prices_values = [float(p["value"]) for p in today_prices if "value" in p]
            if prices_values:
                attrs["today_min_price"] = min(prices_values)
                attrs["today_max_price"] = max(prices_values)
                attrs["today_avg_price"] = sum(prices_values) / len(prices_values)
                attrs["today_prices_count"] = len(prices_values)
        
        if tomorrow_prices:
            prices_values = [float(p["value"]) for p in tomorrow_prices if "value" in p]
            if prices_values:
                attrs["tomorrow_min_price"] = min(prices_values)
                attrs["tomorrow_max_price"] = max(prices_values)
                attrs["tomorrow_avg_price"] = sum(prices_values) / len(prices_values)
                attrs["tomorrow_prices_count"] = len(prices_values)
        
        # Add current period info
        import pytz
        
        tz = pytz.timezone('Europe/Madrid')
        now = datetime.now(tz)
        
        for price_entry in today_prices:
            try:
                start_dt = datetime.fromisoformat(price_entry["start"])
                end_dt = datetime.fromisoformat(price_entry["end"])
                
                if start_dt <= now < end_dt:
                    attrs["current_period_start"] = price_entry["start"]
                    attrs["current_period_end"] = price_entry["end"]
                    attrs["current_period_value"] = price_entry["value"]
                    break
            except (ValueError, TypeError, KeyError):
                continue
        
        return attrs

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
        device_name = device.get("name", "Device") if device else "Device"
        self._attr_name = f"{device_name} State"
        self._attr_unique_id = f"octopus_{device_id}_03_current_state"
        self._attr_translation_key = "device_state"  # Use translation key
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
            
            # Use English states - will be translated by HA
            state_translations = {
                "SMART_CONTROL_NOT_AVAILABLE": "disconnected",
                "SMART_CONTROL_CAPABLE": "connected",
                "BOOSTING": "boost_charging",
                "SMART_CONTROL_IN_PROGRESS": "scheduled_charging"
            }
            
            translated_state = state_translations.get(current_state, current_state)
            return translated_state if translated_state else "unknown"
        return "unknown"

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
        device_name = device.get("name", "Charger") if device else "Charger"
        self._attr_name = f"{device_name} Planned Sessions"
        self._attr_unique_id = f"octopus_{device_id}_04_planned_dispatches"
        self._attr_translation_key = "planned_dispatches"  # Use translation key
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
        """Return planned dispatches info with schedules - ENHANCED to show times."""
        device = self._get_device_data()
        if not device:
            return "Device not found"
        
        current_state = device.get("status", {}).get("currentState")
        dispatches = self.coordinator.data.get("planned_dispatches", {}).get(self._device_id, [])
        
        # Check if car is connected
        connected_states = ["SMART_CONTROL_CAPABLE", "BOOSTING", "SMART_CONTROL_IN_PROGRESS"]
        is_connected = current_state in connected_states
        
        if not is_connected:
            return "Car not connected"
        
        # Car is connected, show dispatch count and times
        dispatch_count = len(dispatches)
        if dispatch_count == 0:
            return "No scheduled sessions"
        
        # Format dispatches with times
        try:
            time_ranges = []
            for dispatch in dispatches:
                start_time = dispatch.get("start")
                end_time = dispatch.get("end")
                
                if start_time and end_time:
                    try:
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        
                        # Format as HH:MM-HH:MM
                        time_range = f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
                        time_ranges.append(time_range)
                    except ValueError:
                        continue
            
            if time_ranges:
                if dispatch_count == 1:
                    return f"1 session: {time_ranges[0]}"
                else:
                    times_str = ", ".join(time_ranges)
                    return f"{dispatch_count} sessions: {times_str}"
            else:
                # Fallback if time parsing fails
                if dispatch_count == 1:
                    return "1 scheduled session"
                else:
                    return f"{dispatch_count} scheduled sessions"
                    
        except Exception as err:
            _LOGGER.warning("Failed to format dispatch times: %s", err)
            # Fallback to simple count
            if dispatch_count == 1:
                return "1 scheduled session"
            else:
                return f"{dispatch_count} scheduled sessions"

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


class OctopusChargerNextSessionStartSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next session start time - FOR AUTOMATIONS."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Charger") if device else "Charger"
        self._attr_name = f"{device_name} Next Session Start"
        self._attr_unique_id = f"octopus_{device_id}_05_next_session_start"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:play-circle"

    def _get_device_data(self) -> dict[str, Any] | None:
        for devices in self.coordinator.data.get("devices", {}).values():
            for device in devices:
                if device.get("id") == self._device_id:
                    return device
        return None

    @property
    def native_value(self) -> datetime | None:
        """Return next session start datetime."""
        dispatches = self.coordinator.data.get("planned_dispatches", {}).get(self._device_id, [])
        
        if not dispatches:
            return None
            
        # Get the first (next) session
        first_dispatch = dispatches[0]
        start_time = first_dispatch.get("start")
        
        if start_time:
            try:
                return datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                pass
        return None

    @property
    def available(self) -> bool:
        return True

    @property
    def device_info(self) -> dict[str, Any]:
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        dispatches = self.coordinator.data.get("planned_dispatches", {}).get(self._device_id, [])
        return {
            "device_id": self._device_id,
            "total_sessions": len(dispatches),
            "has_sessions": len(dispatches) > 0
        }


class OctopusChargerNextSessionEndSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last session end time today - FOR AUTOMATIONS."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Charger") if device else "Charger"
        self._attr_name = f"{device_name} Last Session End"
        self._attr_unique_id = f"octopus_{device_id}_06_last_session_end"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:stop-circle"

    def _get_device_data(self) -> dict[str, Any] | None:
        for devices in self.coordinator.data.get("devices", {}).values():
            for device in devices:
                if device.get("id") == self._device_id:
                    return device
        return None

    @property
    def native_value(self) -> datetime | None:
        """Return last session end datetime today."""
        dispatches = self.coordinator.data.get("planned_dispatches", {}).get(self._device_id, [])
        
        if not dispatches:
            return None
            
        # Get the last session's end time
        last_dispatch = dispatches[-1]
        end_time = last_dispatch.get("end")
        
        if end_time:
            try:
                return datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                pass
        return None

    @property
    def available(self) -> bool:
        return True

    @property
    def device_info(self) -> dict[str, Any]:
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)


class OctopusChargerTotalHoursTodaySensor(CoordinatorEntity, SensorEntity):
    """Sensor for total charging hours today - FOR AUTOMATIONS."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Charger") if device else "Charger"
        self._attr_name = f"{device_name} Total Hours Today"
        self._attr_unique_id = f"octopus_{device_id}_07_total_hours_today"
        self._attr_native_unit_of_measurement = UnitOfTime.HOURS
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:clock-time-eight"

    def _get_device_data(self) -> dict[str, Any] | None:
        for devices in self.coordinator.data.get("devices", {}).values():
            for device in devices:
                if device.get("id") == self._device_id:
                    return device
        return None

    @property
    def native_value(self) -> float:
        """Return total hours of charging planned for today."""
        dispatches = self.coordinator.data.get("planned_dispatches", {}).get(self._device_id, [])
        
        if not dispatches:
            return 0.0
            
        total_hours = 0.0
        
        for dispatch in dispatches:
            start_time = dispatch.get("start")
            end_time = dispatch.get("end")
            
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration = (end_dt - start_dt).total_seconds() / 3600
                    total_hours += duration
                except ValueError:
                    continue
                    
        return round(total_hours, 2)

    @property
    def available(self) -> bool:
        return True

    @property
    def device_info(self) -> dict[str, Any]:
        device = self._get_device_data()
        return _safe_device_info(self._device_id, device)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed session info for automations."""
        dispatches = self.coordinator.data.get("planned_dispatches", {}).get(self._device_id, [])
        
        attrs = {
            "device_id": self._device_id,
            "total_sessions": len(dispatches),
            "session_details": []
        }
        
        # Add detailed session info
        for i, dispatch in enumerate(dispatches):
            start_time = dispatch.get("start")
            end_time = dispatch.get("end")
            dispatch_type = dispatch.get("type", "SMART")
            
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration_hours = round((end_dt - start_dt).total_seconds() / 3600, 2)
                    
                    session_detail = {
                        "session_number": i + 1,
                        "start_time": start_time,
                        "end_time": end_time,
                        "start_time_local": start_dt.strftime("%H:%M"),
                        "end_time_local": end_dt.strftime("%H:%M"),
                        "duration_hours": duration_hours,
                        "type": dispatch_type
                    }
                    attrs["session_details"].append(session_detail)
                    
                except ValueError:
                    continue
        
        # Add convenience attributes for automations
        if attrs["session_details"]:
            first_session = attrs["session_details"][0]
            last_session = attrs["session_details"][-1]
            
            attrs["first_session_start"] = first_session["start_time"]
            attrs["last_session_end"] = last_session["end_time"]
            attrs["time_slots"] = [f"{s['start_time_local']}-{s['end_time_local']}" for s in attrs["session_details"]]
        
        return attrs


class OctopusChargerLastSessionDateSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last charging session date - NEW SENSOR."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Charger") if device else "Charger"
        self._attr_name = f"{device_name} Last Charge Date"
        self._attr_unique_id = f"octopus_{device_id}_08_last_session_date"  # Updated from 05_ to 08_
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:calendar-clock"

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
    def native_value(self) -> datetime | None:
        last_session = self._get_last_session()
        if last_session:
            start_time = last_session.get("start")
            if start_time:
                try:
                    return datetime.fromisoformat(start_time.replace('Z', '+00:00'))
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

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        last_session = self._get_last_session()
        attrs = {"device_id": self._device_id}
        
        if last_session:
            start_time = last_session.get("start")
            end_time = last_session.get("end")
            
            if start_time:
                attrs["start_time"] = start_time
            if end_time:
                attrs["end_time"] = end_time
                
            # Add session type if available
            session_type = last_session.get("type")
            if session_type:
                attrs["session_type"] = session_type
        
        return attrs


class OctopusChargerLastEnergyAddedSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last charging session energy added - FIXED availability."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Charger") if device else "Charger"
        self._attr_name = f"{device_name} Last Energy Added"
        self._attr_unique_id = f"octopus_{device_id}_10_last_energy_added"  # Updated from 07_
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


class OctopusChargerLastSessionDurationSensor(CoordinatorEntity, SensorEntity):
    """Sensor for last charging session duration - FIXED availability."""

    def __init__(self, coordinator: OctopusSpainDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        
        device = self._get_device_data()
        device_name = device.get("name", "Charger") if device else "Charger"
        self._attr_name = f"{device_name} Last Session Duration"
        self._attr_unique_id = f"octopus_{device_id}_09_last_session_duration"  # Updated from 06_
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
        device_name = device.get("name", "Charger") if device else "Charger"
        self._attr_name = f"{device_name} Last Session Cost"
        self._attr_unique_id = f"octopus_{device_id}_11_last_session_cost"  # Updated from 08_
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