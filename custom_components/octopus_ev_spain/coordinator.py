"""Data update coordinator for Octopus Energy Spain - FIXED following original pattern."""
from __future__ import annotations

import asyncio
from datetime import timedelta, datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OctopusSpainAPI
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class OctopusSpainDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API - FIXED following original pattern."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        api: OctopusSpainAPI,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.api = api
        self.accounts: list[str] = []
        
        # Simple single interval like original
        super().__init__(hass, logger, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data - EXACTLY following original pattern."""
        try:
            # CRITICAL: Login once per update cycle, like original
            login_success = await self.api.login()
            if not login_success:
                raise ConfigEntryAuthFailed("Login failed")
            
            _LOGGER.debug("Login successful, fetching data...")
            
            # Following original pattern: get viewer info first
            viewer_info = await self.api.get_viewer_info()
            self.accounts = [account["number"] for account in viewer_info["accounts"]]
            
            data = {
                "viewer": viewer_info,
                "accounts": {},
                "billing_info": {},  # NEW: For invoice data
                "account_properties": {},  # NEW: For contract and address data
                "property_meters": {},     # NEW: For CUPS data
                "electricity_agreements": {},  # NEW: For contract details
                "agreement_prices": {},    # NEW: For tariff prices
                "hourly_prices": {},       # NEW: For hourly pricing
                "devices": {},
                "planned_dispatches": {},
                "charge_history": {},
                "device_preferences": {},
            }

            # Fetch data for each account - simplified
            for account_number in self.accounts:
                try:
                    _LOGGER.debug("Fetching data for account %s", account_number)
                    
                    # Get account info (ledgers)
                    account_data = await self.api.get_account_info(account_number)
                    data["accounts"][account_number] = account_data
                    
                    # Get billing info for invoices (from original repo pattern)
                    try:
                        billing_data = await self.api.get_account_billing_info(account_number)
                        data["billing_info"][account_number] = self._process_billing_data(billing_data)
                        _LOGGER.debug("Got billing info for account %s", account_number)
                    except Exception as err:
                        _LOGGER.warning("Failed to get billing info for account %s: %s", account_number, err)
                        data["billing_info"][account_number] = {"last_invoice": None}
                    
                    # Get account properties (contract number, address)
                    try:
                        properties_data = await self.api.get_account_properties(account_number)
                        data["account_properties"][account_number] = properties_data
                        _LOGGER.debug("Got properties for account %s", account_number)
                        
                        # Get property meters (CUPS) if we have properties
                        if properties_data.get("properties"):
                            property_id = properties_data["properties"][0]["id"]
                            try:
                                meters_data = await self.api.get_property_meters(property_id)
                                data["property_meters"][account_number] = meters_data
                                _LOGGER.debug("Got meters for property %s", property_id)
                                
                                # Get electricity agreement details if we have electricity meter
                                electricity_points = meters_data.get("electricitySupplyPoints", [])
                                if electricity_points:
                                    meter_id = electricity_points[0]["id"]
                                    try:
                                        agreement_data = await self.api.get_electricity_agreement(meter_id)
                                        data["electricity_agreements"][account_number] = agreement_data
                                        _LOGGER.debug("Got electricity agreement for meter %s", meter_id)
                                        
                                        # NEW: Get agreement prices if we have active agreement
                                        active_agreement = agreement_data.get("activeAgreement")
                                        if active_agreement:
                                            agreement_id = active_agreement.get("id")
                                            if agreement_id:
                                                try:
                                                    prices_data = await self.api.get_agreement_prices(agreement_id)
                                                    data["agreement_prices"][account_number] = prices_data
                                                    _LOGGER.debug("Got agreement prices for %s", agreement_id)
                                                    
                                                    # Generate hourly prices from tariff structure
                                                    try:
                                                        data["hourly_prices"][account_number] = self._generate_hourly_prices_from_tariff(prices_data)
                                                        _LOGGER.debug("Generated hourly prices from tariff for agreement %s", agreement_id)
                                                    except Exception as err:
                                                        _LOGGER.warning("Failed to generate hourly prices: %s", err)
                                                        data["hourly_prices"][account_number] = {"today": [], "tomorrow": []}
                                                        
                                                except Exception as err:
                                                    _LOGGER.warning("Failed to get agreement prices: %s", err)
                                                    data["agreement_prices"][account_number] = {}
                                                    data["hourly_prices"][account_number] = {"today": [], "tomorrow": []}
                                        else:
                                            data["agreement_prices"][account_number] = {}
                                            data["hourly_prices"][account_number] = {"today": [], "tomorrow": []}
                                        
                                    except Exception as err:
                                        _LOGGER.warning("Failed to get electricity agreement for meter %s: %s", meter_id, err)
                                        data["electricity_agreements"][account_number] = {}
                                        data["agreement_prices"][account_number] = {}
                                        data["hourly_prices"][account_number] = {"today": [], "tomorrow": []}
                                else:
                                    data["electricity_agreements"][account_number] = {}
                                    data["agreement_prices"][account_number] = {}
                                    data["hourly_prices"][account_number] = {"today": [], "tomorrow": []}
                            except Exception as err:
                                _LOGGER.warning("Failed to get meters for property %s: %s", property_id, err)
                                data["property_meters"][account_number] = {}
                                data["electricity_agreements"][account_number] = {}
                                data["agreement_prices"][account_number] = {}
                                data["hourly_prices"][account_number] = {"today": [], "tomorrow": []}
                        else:
                            data["property_meters"][account_number] = {}
                            data["electricity_agreements"][account_number] = {}
                            data["agreement_prices"][account_number] = {}
                            data["hourly_prices"][account_number] = {"today": [], "tomorrow": []}
                    except Exception as err:
                        _LOGGER.warning("Failed to get properties for account %s: %s", account_number, err)
                        data["account_properties"][account_number] = {}
                        data["property_meters"][account_number] = {}
                        data["electricity_agreements"][account_number] = {}
                        data["agreement_prices"][account_number] = {}
                        data["hourly_prices"][account_number] = {"today": [], "tomorrow": []}
                    
                    # Get devices with states
                    devices = await self.api.get_devices_with_states(account_number)
                    data["devices"][account_number] = devices
                    
                    # Get extended info for chargers ONLY if connected
                    for device in devices:
                        device_id = device.get("id")
                        device_name = device.get("name", "Unknown")
                        device_type = device.get("__typename")
                        current_state = device.get("status", {}).get("currentState")
                        
                        if device_type == "SmartFlexChargePoint":
                            _LOGGER.debug("Processing charger %s (ID: %s, State: %s)", 
                                        device_name, device_id, current_state)
                            
                            # Initialize with empty data
                            data["planned_dispatches"][device_id] = []
                            data["charge_history"][device_id] = []
                            data["device_preferences"][device_id] = {}
                            
                            # Get preferences (always available)
                            try:
                                preferences = await self.api.get_device_preferences(account_number, device_id)
                                data["device_preferences"][device_id] = preferences
                                _LOGGER.debug("Got preferences for charger %s", device_name)
                            except Exception as err:
                                _LOGGER.warning("Failed to get preferences for %s: %s", device_name, err)
                            
                            # Get planned dispatches - ALWAYS try to get them, don't depend on state
                            try:
                                dispatches = await self.api.get_planned_dispatches(device_id)
                                data["planned_dispatches"][device_id] = dispatches
                                _LOGGER.debug("Got %d planned dispatches for %s", len(dispatches), device_name)
                            except Exception as err:
                                _LOGGER.warning("Failed to get planned dispatches for %s: %s", device_name, err)
                                data["planned_dispatches"][device_id] = []
                            
                            # Get charge history - ALWAYS try to get it (should always be available)
                            try:
                                history = await self.api.get_charge_history(account_number, device_id, 3)
                                data["charge_history"][device_id] = history
                                if history and len(history) > 0:
                                    sessions = history[0].get("chargePointChargingSession", {}).get("edges", [])
                                    _LOGGER.debug("Got %d charge sessions for %s", len(sessions), device_name)
                                else:
                                    _LOGGER.debug("No charge history returned for %s", device_name)
                            except Exception as err:
                                if "KT-CT-7899" in str(err):
                                    _LOGGER.debug("No charge history for %s (device may be new or no sessions yet)", device_name)
                                    data["charge_history"][device_id] = []
                                else:
                                    _LOGGER.warning("Failed to get charge history for %s: %s", device_name, err)
                                    data["charge_history"][device_id] = []

                except Exception as err:
                    _LOGGER.error("Failed to fetch data for account %s: %s", account_number, err)
                    # Set default empty data for failed account
                    data["accounts"][account_number] = {"ledgers": []}
                    data["devices"][account_number] = []
                    data["account_properties"][account_number] = {}
                    data["property_meters"][account_number] = {}
                    data["electricity_agreements"][account_number] = {}
                    data["agreement_prices"][account_number] = {}
                    data["hourly_prices"][account_number] = {"today": [], "tomorrow": []}

            _LOGGER.info("Data update completed for %d accounts", len(self.accounts))
            return data

        except Exception as err:
            if "authentication" in str(err).lower() or "expired" in str(err).lower() or "KT-CT-1124" in str(err):
                _LOGGER.error("Authentication failed: %s", err)
                raise ConfigEntryAuthFailed("Authentication failed") from err
            elif "too many requests" in str(err).lower() or "KT-CT-1199" in str(err):
                _LOGGER.warning("Rate limited, will retry on next update: %s", err)
                raise UpdateFailed(f"Rate limited: {err}") from err
            else:
                _LOGGER.error("Error updating data: %s", err)
                raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_refresh_specific_device(self, device_id: str) -> None:
        """Refresh data for a specific device - FIXED to not cause too many logins."""
        _LOGGER.info("Manual refresh requested for device %s", device_id)
        try:
            # Find which account this device belongs to
            account = await self.async_get_account_for_device(device_id)
            if not account:
                _LOGGER.warning("Device %s not found, doing full refresh", device_id)
                await self.async_request_refresh()
                return
            
            # Login once for this refresh operation
            login_success = await self.api.login()
            if not login_success:
                raise Exception("Login failed for device refresh")
                
            # Get updated device data
            devices = await self.api.get_devices_with_states(account)
            
            # Update the device in current data
            if hasattr(self, 'data') and self.data:
                self.data["devices"][account] = devices
                
                # Update extended data for this device if it's a charger
                for device in devices:
                    if device.get("id") == device_id and device.get("__typename") == "SmartFlexChargePoint":
                        device_name = device.get("name", "Unknown")
                        current_state = device.get("status", {}).get("currentState")
                        
                        # ALWAYS update planned dispatches, don't depend on connection state
                        try:
                            dispatches = await self.api.get_planned_dispatches(device_id)
                            self.data["planned_dispatches"][device_id] = dispatches
                            _LOGGER.info("Refreshed %d planned dispatches for %s", len(dispatches), device_name)
                        except Exception as err:
                            _LOGGER.warning("Failed to refresh planned dispatches for %s: %s", device_name, err)
                            self.data["planned_dispatches"][device_id] = []
                        
                        break
                
                self.async_update_listeners()
            else:
                await self.async_request_refresh()
                
        except Exception as err:
            _LOGGER.error("Failed to refresh device %s: %s", device_id, err)
            raise

    async def async_get_device_data(self, device_id: str) -> dict | None:
        """Get data for a specific device."""
        for account_devices in self.data.get("devices", {}).values():
            for device in account_devices:
                if device.get("id") == device_id:
                    return device
        return None

    async def async_get_device_state(self, device_id: str) -> dict | None:
        """Get state for a specific device."""
        device = await self.async_get_device_data(device_id)
        return device if device else None

    async def async_get_account_for_device(self, device_id: str) -> str | None:
        """Get the account number for a specific device."""
        for account_number, devices in self.data.get("devices", {}).items():
            for device in devices:
                if device.get("id") == device_id:
                    return account_number
        return None

    def has_charge_history(self, device_id: str) -> bool:
        """Check if device has charge history."""
        history_data = self.data.get("charge_history", {}).get(device_id, [])
        if history_data and len(history_data) > 0:
            sessions = history_data[0].get("chargePointChargingSession", {}).get("edges", [])
            return len(sessions) > 0
        return False

    def get_planned_dispatches_count(self, device_id: str) -> int:
        """Get number of planned dispatches for device."""
        dispatches = self.data.get("planned_dispatches", {}).get(device_id, [])
        return len(dispatches)

    def _process_billing_data(self, billing_data: dict) -> dict:
        """Process billing data to extract invoice info - FROM ORIGINAL REPO."""
        from datetime import datetime, timedelta
        
        ledgers = billing_data.get("ledgers", [])
        
        # Find electricity ledger with invoice data
        electricity_ledger = None
        for ledger in ledgers:
            if ledger.get("ledgerType") == "SPAIN_ELECTRICITY_LEDGER":
                electricity_ledger = ledger
                break
        
        if not electricity_ledger:
            return {"last_invoice": None}
        
        statements = electricity_ledger.get("statementsWithDetails", {}).get("edges", [])
        
        if not statements:
            return {
                "last_invoice": {
                    "amount": None,
                    "issued": None,
                    "start": None,
                    "end": None
                }
            }
        
        # Get the most recent invoice
        invoice = statements[0]["node"]
        
        try:
            # Process dates following original pattern
            issued_date = None
            start_date = None
            end_date = None
            
            if invoice.get("issuedDate"):
                issued_date = datetime.fromisoformat(invoice["issuedDate"]).date()
            
            if invoice.get("consumptionStartDate"):
                # Original adds 2 hours (timezone adjustment)
                start_date = (datetime.fromisoformat(invoice["consumptionStartDate"]) + timedelta(hours=2)).date()
            
            if invoice.get("consumptionEndDate"):
                # Original subtracts 1 second 
                end_date = (datetime.fromisoformat(invoice["consumptionEndDate"]) - timedelta(seconds=1)).date()
            
            return {
                "last_invoice": {
                    "amount": invoice["amount"] if invoice.get("amount") else 0,
                    "issued": issued_date,
                    "start": start_date,
                    "end": end_date,
                }
            }
            
        except Exception as err:
            _LOGGER.warning("Failed to process invoice dates: %s", err)
            return {
                "last_invoice": {
                    "amount": invoice.get("amount", 0),
                    "issued": None,
                    "start": None,
                    "end": None,
                }
            }

    def _generate_hourly_prices_from_tariff(self, prices_data: dict) -> dict:
        """Generate hourly pricing data from Spanish tariff structure."""
        import pytz
        
        if not prices_data or not prices_data.get("product", {}).get("prices"):
            return {"today": [], "tomorrow": []}
        
        prices = prices_data["product"]["prices"]
        variable_terms = prices.get("variableTerm", [])
        
        if len(variable_terms) < 3:
            # Not a time-of-use tariff, return empty
            return {"today": [], "tomorrow": []}
        
        # Spanish tariff rates (from your specification)
        price_peak = float(variable_terms[0])      # PUNTA: 0.197
        price_standard = float(variable_terms[1])  # LLANO: 0.122  
        price_valley = float(variable_terms[2])    # VALLE: 0.084
        
        # Get timezone
        tz = pytz.timezone('Europe/Madrid')
        today = datetime.now(tz).date()
        tomorrow = today + timedelta(days=1)
        
        today_prices = []
        tomorrow_prices = []
        
        # Generate prices for today and tomorrow
        for target_date in [today, tomorrow]:
            prices_for_day = []
            
            # Generate 30-minute intervals for the full day
            current_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
            end_of_day = current_dt + timedelta(days=1)
            
            while current_dt < end_of_day:
                interval_end = current_dt + timedelta(minutes=30)
                
                # Determine price based on Spanish tariff rules
                price = self._get_spanish_tariff_price(current_dt, price_peak, price_standard, price_valley)
                
                price_entry = {
                    "start": current_dt.isoformat(),
                    "end": interval_end.isoformat(), 
                    "value": price
                }
                
                prices_for_day.append(price_entry)
                current_dt = interval_end
            
            # Add to appropriate day
            if target_date == today:
                today_prices = prices_for_day
            else:
                tomorrow_prices = prices_for_day
        
        return {
            "today": today_prices,
            "tomorrow": tomorrow_prices
        }
    
    def _get_spanish_tariff_price(self, dt: datetime, price_peak: float, price_standard: float, price_valley: float) -> float:
        """Get price for specific datetime based on Spanish tariff rules."""
        weekday = dt.weekday()  # 0=Monday, 6=Sunday
        hour = dt.hour
        
        # Weekend (Saturday=5, Sunday=6): Always VALLE
        if weekday >= 5:
            return price_valley
            
        # Weekdays: Apply time-based pricing
        # PUNTA: 10:00-14:00 and 18:00-22:00
        if (10 <= hour < 14) or (18 <= hour < 22):
            return price_peak
        # LLANO: 8:00-10:00, 14:00-18:00, 22:00-24:00  
        elif (8 <= hour < 10) or (14 <= hour < 18) or (22 <= hour < 24):
            return price_standard
        # VALLE: 0:00-8:00
        else:
            return price_valley