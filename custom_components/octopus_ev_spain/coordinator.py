"""Data update coordinator for Octopus Energy Spain - CORRECTED."""
from __future__ import annotations

import asyncio
from datetime import timedelta, datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OctopusSpainAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class OctopusSpainDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API with corrected structure."""

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
        
        # Different intervals for different types of data
        self._devices_interval = timedelta(minutes=2)      # Chargers every 2 min
        self._account_interval = timedelta(minutes=15)     # Accounts every 15 min
        self._measurements_interval = timedelta(hours=1)   # Measurements every 1 hour
        
        # Track last update time by type
        self._last_devices_update = None
        self._last_account_update = None
        self._last_measurements_update = None
        
        super().__init__(hass, logger, name=DOMAIN, update_interval=self._devices_interval)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data with smart refresh based on intervals."""
        now = datetime.now()
        
        # Determine what to update based on intervals
        update_devices = (
            self._last_devices_update is None or 
            now - self._last_devices_update >= self._devices_interval
        )
        
        update_account = (
            self._last_account_update is None or 
            now - self._last_account_update >= self._account_interval
        )
        
        update_measurements = (
            self._last_measurements_update is None or 
            now - self._last_measurements_update >= self._measurements_interval
        )

        # If no initial data, update everything
        if not hasattr(self, 'data') or not self.data:
            return await self._refresh_all_data()

        # Selective update
        current_data = self.data.copy()
        
        if update_devices:
            _LOGGER.debug("Updating devices data")
            devices_data = await self._refresh_devices_data()
            current_data["devices"] = devices_data["devices"]
            self._last_devices_update = now

        if update_account:
            _LOGGER.debug("Updating account data")
            account_data = await self._refresh_account_data()
            current_data["accounts"] = account_data["accounts"]
            self._last_account_update = now

        if update_measurements:
            _LOGGER.debug("Updating measurements data")
            measurements_data = await self._refresh_measurements_data()
            current_data["measurements"] = measurements_data["measurements"]
            self._last_measurements_update = now

        return current_data

    async def async_refresh_specific_device(self, device_id: str) -> None:
        """Refresh data for a specific device using corrected API calls."""
        _LOGGER.info("Manual refresh of device %s requested", device_id)
        try:
            # If no initial data, perform full refresh first
            if not hasattr(self, 'data') or not self.data:
                _LOGGER.info("No initial data found, performing full refresh first")
                await self.async_request_refresh()
                return
                
            account = await self.async_get_account_for_device(device_id)
            if not account:
                _LOGGER.warning("Device %s not found in any account, trying full refresh", device_id)
                await self.async_request_refresh()
                return
                
            # Use the corrected API method
            device_data = await self.api.get_devices(account, device_id)
            
            # Update only this device in the data
            if hasattr(self, 'data') and self.data:
                current_devices = self.data.get("devices", {}).get(account, [])
                updated_devices = []
                
                # Replace or add the updated device
                device_found = False
                for existing_device in current_devices:
                    if existing_device.get("id") == device_id:
                        # Replace with updated data
                        if device_data:
                            updated_devices.append(device_data[0])  # get_devices returns list
                            device_found = True
                    else:
                        updated_devices.append(existing_device)
                
                # If not found, add it
                if not device_found and device_data:
                    updated_devices.append(device_data[0])
                
                self.data["devices"][account] = updated_devices
                self.async_update_listeners()
            else:
                await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to refresh device %s: %s", device_id, err)
            raise

    async def _refresh_all_data(self) -> dict[str, Any]:
        """Refresh all data types using corrected API calls."""
        try:
            # Get viewer info and accounts
            viewer_info = await self.api.get_viewer_info()
            self.accounts = [account["number"] for account in viewer_info["accounts"]]
            
            data = {
                "viewer": viewer_info,
                "accounts": {},
                "devices": {},
                "measurements": {},
                "flex_dispatches": {},
            }

            # Fetch data for each account
            for account_number in self.accounts:
                try:
                    # Account info (ledgers + properties)
                    account_data = await self.api.get_account_info(account_number)
                    data["accounts"][account_number] = account_data
                    
                    # Devices with enhanced info
                    devices = await self.api.get_devices(account_number)
                    data["devices"][account_number] = devices
                    
                    # For each device, get additional info
                    for device in devices:
                        device_id = device.get("id")
                        if device_id and device.get("__typename") == "SmartFlexChargePoint":
                            try:
                                # Get planned dispatches
                                flex_dispatches = await self.api.flex_planned_dispatches(device_id)
                                data["flex_dispatches"][device_id] = flex_dispatches
                            except Exception as err:
                                _LOGGER.warning("Failed to get flex dispatches for device %s: %s", device_id, err)
                                data["flex_dispatches"][device_id] = []

                    # Property measurements
                    for property_data in account_data.get("properties", []):
                        property_id = property_data.get("id")
                        if property_id and property_id not in data["measurements"]:
                            try:
                                measurements = await self.api.get_smart_usage(property_id)
                                data["measurements"][property_id] = measurements
                            except Exception as err:
                                _LOGGER.warning("Failed to get measurements for property %s: %s", property_id, err)
                                data["measurements"][property_id] = {"measurements": {"edges": []}}

                except Exception as err:
                    _LOGGER.error("Failed to fetch data for account %s: %s", account_number, err)
                    data["accounts"][account_number] = {"ledgers": [], "properties": []}
                    data["devices"][account_number] = []

            # Update timestamps
            now = datetime.now()
            self._last_devices_update = now
            self._last_account_update = now
            self._last_measurements_update = now

            return data

        except Exception as err:
            if "authentication" in str(err).lower():
                raise ConfigEntryAuthFailed("Authentication failed") from err
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _refresh_devices_data(self) -> dict[str, Any]:
        """Refresh only devices data using corrected API calls."""
        devices_data = {"devices": {}}
        
        for account_number in self.accounts:
            try:
                devices = await self.api.get_devices(account_number)
                devices_data["devices"][account_number] = devices
            except Exception as err:
                _LOGGER.error("Failed to fetch devices for account %s: %s", account_number, err)
                devices_data["devices"][account_number] = []
        
        return devices_data

    async def _refresh_account_data(self) -> dict[str, Any]:
        """Refresh only account data using corrected API calls."""
        account_data = {"accounts": {}}
        
        for account_number in self.accounts:
            try:
                account_info = await self.api.get_account_info(account_number)
                account_data["accounts"][account_number] = account_info
            except Exception as err:
                _LOGGER.error("Failed to fetch account info for %s: %s", account_number, err)
                account_data["accounts"][account_number] = {"ledgers": [], "properties": []}
        
        return account_data

    async def _refresh_measurements_data(self) -> dict[str, Any]:
        """Refresh only measurements data using corrected API calls."""
        measurements_data = {"measurements": {}}
        
        # Get unique property IDs from current accounts
        property_ids = set()
        for account_data in self.data.get("accounts", {}).values():
            for property_data in account_data.get("properties", []):
                property_id = property_data.get("id")
                if property_id:
                    property_ids.add(property_id)
        
        for property_id in property_ids:
            try:
                measurements = await self.api.get_smart_usage(property_id)
                measurements_data["measurements"][property_id] = measurements
            except Exception as err:
                _LOGGER.error("Failed to fetch measurements for property %s: %s", property_id, err)
                measurements_data["measurements"][property_id] = {"measurements": {"edges": []}}
        
        return measurements_data

    async def async_get_device_data(self, device_id: str) -> dict | None:
        """Get data for a specific device."""
        for account_devices in self.data.get("devices", {}).values():
            for device in account_devices:
                if device.get("id") == device_id:
                    return device
        return None

    async def async_get_account_for_device(self, device_id: str) -> str | None:
        """Get the account number for a specific device."""
        for account_number, devices in self.data.get("devices", {}).items():
            for device in devices:
                if device.get("id") == device_id:
                    return account_number
        return None