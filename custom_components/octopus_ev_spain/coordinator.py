"""Data update coordinator for Octopus Energy Spain - SIMPLIFIED for real data structure."""
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
    """Class to manage fetching data from the API - SIMPLIFIED."""

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
        
        # Track charging sessions history in memory
        self._charging_sessions_history: dict[str, list[dict]] = {}
        
        # Simpler intervals
        self._devices_interval = timedelta(minutes=2)      # Device states every 2 min
        self._account_interval = timedelta(minutes=15)     # Accounts every 15 min
        self._extended_interval = timedelta(minutes=10)    # Extended data every 10 min
        
        # Track last update time by type
        self._last_devices_update = None
        self._last_account_update = None
        self._last_extended_update = None
        
        super().__init__(hass, logger, name=DOMAIN, update_interval=self._devices_interval)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data with simplified structure."""
        now = datetime.now()
        
        # Determine what to update
        update_devices = (
            self._last_devices_update is None or 
            now - self._last_devices_update >= self._devices_interval
        )
        
        update_account = (
            self._last_account_update is None or 
            now - self._last_account_update >= self._account_interval
        )
        
        update_extended = (
            self._last_extended_update is None or 
            now - self._last_extended_update >= self._extended_interval
        )

        # If no initial data, get everything
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

        if update_extended:
            _LOGGER.debug("Updating extended data")
            extended_data = await self._refresh_extended_data()
            current_data.update(extended_data)
            self._last_extended_update = now

        return current_data

    async def async_refresh_specific_device(self, device_id: str) -> None:
        """Refresh data for a specific device."""
        _LOGGER.info("Manual refresh of device %s requested", device_id)
        try:
            account = await self.async_get_account_for_device(device_id)
            if not account:
                _LOGGER.warning("Device %s not found, refreshing all data", device_id)
                await self.async_request_refresh()
                return
                
            # Get updated device with state using the combined query
            devices_with_states = await self.api.get_smart_flex_devices_states(account)
            
            # Update device in current data
            if hasattr(self, 'data') and self.data:
                current_devices = self.data.get("devices", {}).get(account, [])
                updated_devices = []
                
                # Replace or add the updated device
                device_found = False
                for existing_device in current_devices:
                    if existing_device.get("id") == device_id:
                        # Find updated device in response
                        for updated_device in devices_with_states:
                            if updated_device.get("id") == device_id:
                                # Merge with existing device info to keep name, etc.
                                merged_device = existing_device.copy()
                                merged_device["status"] = updated_device.get("status", {})
                                updated_devices.append(merged_device)
                                device_found = True
                                break
                        if not device_found:
                            updated_devices.append(existing_device)
                    else:
                        updated_devices.append(existing_device)
                
                self.data["devices"][account] = updated_devices
                self.async_update_listeners()
            else:
                await self.async_request_refresh()
                
        except Exception as err:
            _LOGGER.error("Failed to refresh device %s: %s", device_id, err)
            raise

    async def _refresh_all_data(self) -> dict[str, Any]:
        """Refresh all data using simplified structure."""
        try:
            # Get viewer info and accounts
            viewer_info = await self.api.get_viewer_info()
            self.accounts = [account["number"] for account in viewer_info["accounts"]]
            
            data = {
                "viewer": viewer_info,
                "accounts": {},
                "devices": {},
                "planned_dispatches": {},
                "charge_history": {},
                "device_preferences": {},
            }

            # Fetch data for each account
            for account_number in self.accounts:
                try:
                    # Account info (ledgers + properties)
                    account_data = await self.api.get_account_info(account_number)
                    data["accounts"][account_number] = account_data
                    
                    # Get devices WITH states in one call (simplified)
                    devices_with_states = await self.api.get_smart_flex_devices_states(account_number)
                    
                    # Get basic device info to merge names, etc.
                    try:
                        basic_devices = await self.api.get_smart_flex_devices_basic(account_number)
                        # Merge basic info with states
                        merged_devices = []
                        for state_device in devices_with_states:
                            device_id = state_device.get("id")
                            # Find corresponding basic device
                            basic_device = None
                            for basic in basic_devices:
                                if basic.get("id") == device_id:
                                    basic_device = basic
                                    break
                            
                            if basic_device:
                                # Merge basic info with state
                                merged_device = basic_device.copy()
                                merged_device["status"] = state_device.get("status", {})
                                merged_devices.append(merged_device)
                            else:
                                # Use state device as-is
                                merged_devices.append(state_device)
                        
                        data["devices"][account_number] = merged_devices
                    except Exception as err:
                        _LOGGER.warning("Failed to get basic device info for %s: %s", account_number, err)
                        # Use devices with states only
                        data["devices"][account_number] = devices_with_states
                    
                    # Get extended info for chargers
                    for device in data["devices"][account_number]:
                        device_id = device.get("id")
                        if device_id and device.get("__typename") == "SmartFlexChargePoint":
                            # Initialize with empty data
                            data["planned_dispatches"][device_id] = []
                            data["charge_history"][device_id] = []
                            data["device_preferences"][device_id] = {}
                            
                            # Get planned dispatches (most reliable)
                            try:
                                dispatches = await self.api.flex_planned_dispatches(device_id)
                                data["planned_dispatches"][device_id] = dispatches
                                _LOGGER.debug("Got %d planned dispatches for device %s", len(dispatches), device_id)
                            except Exception as err:
                                _LOGGER.warning("Failed to get planned dispatches for device %s: %s", device_id, err)
                            
                            # Get device preferences
                            try:
                                preferences = await self.api.get_smart_flex_device_preferences(account_number, device_id)
                                data["device_preferences"][device_id] = preferences
                                _LOGGER.debug("Got preferences for device %s", device_id)
                            except Exception as err:
                                _LOGGER.warning("Failed to get preferences for device %s: %s", device_id, err)
                                
                            # Get charge history (optional - can fail)
                            try:
                                history_data = await self.api.get_smart_flex_charge_history(account_number, device_id, 3)
                                data["charge_history"][device_id] = history_data
                                
                                # Store sessions in memory
                                if history_data and len(history_data) > 0:
                                    sessions = history_data[0].get("chargePointChargingSession", {}).get("edges", [])
                                    if sessions:
                                        self._update_sessions_history(device_id, sessions)
                                        _LOGGER.debug("Got %d charge sessions for device %s", len(sessions), device_id)
                                
                            except Exception as err:
                                if "KT-CT-7899" in str(err) or "chargePointChargingSession" in str(err):
                                    _LOGGER.info("No charge history for device %s (normal for new devices)", device_id)
                                else:
                                    _LOGGER.warning("Failed to get charge history for device %s: %s", device_id, err)

                except Exception as err:
                    _LOGGER.error("Failed to fetch data for account %s: %s", account_number, err)
                    data["accounts"][account_number] = {"ledgers": [], "properties": []}
                    data["devices"][account_number] = []

            # Update timestamps
            now = datetime.now()
            self._last_devices_update = now
            self._last_account_update = now
            self._last_extended_update = now

            return data

        except Exception as err:
            if "authentication" in str(err).lower():
                raise ConfigEntryAuthFailed("Authentication failed") from err
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _refresh_devices_data(self) -> dict[str, Any]:
        """Refresh only devices data - simplified."""
        devices_data = {"devices": {}}
        
        for account_number in self.accounts:
            try:
                # Get devices with states (combined)
                devices_with_states = await self.api.get_smart_flex_devices_states(account_number)
                
                # Merge with existing basic info if available
                existing_devices = self.data.get("devices", {}).get(account_number, [])
                merged_devices = []
                
                for state_device in devices_with_states:
                    device_id = state_device.get("id")
                    # Find existing device to preserve name, etc.
                    existing_device = None
                    for existing in existing_devices:
                        if existing.get("id") == device_id:
                            existing_device = existing
                            break
                    
                    if existing_device:
                        # Merge existing info with new state
                        merged_device = existing_device.copy()
                        merged_device["status"] = state_device.get("status", {})
                        merged_devices.append(merged_device)
                    else:
                        # Use state device as-is
                        merged_devices.append(state_device)
                
                devices_data["devices"][account_number] = merged_devices
                
            except Exception as err:
                _LOGGER.error("Failed to fetch devices for account %s: %s", account_number, err)
                devices_data["devices"][account_number] = []
        
        return devices_data

    async def _refresh_account_data(self) -> dict[str, Any]:
        """Refresh only account data."""
        account_data = {"accounts": {}}
        
        for account_number in self.accounts:
            try:
                account_info = await self.api.get_account_info(account_number)
                account_data["accounts"][account_number] = account_info
            except Exception as err:
                _LOGGER.error("Failed to fetch account info for %s: %s", account_number, err)
                account_data["accounts"][account_number] = {"ledgers": [], "properties": []}
        
        return account_data

    async def _refresh_extended_data(self) -> dict[str, Any]:
        """Refresh extended data (dispatches, history, preferences)."""
        extended_data = {
            "planned_dispatches": {},
            "charge_history": {},
            "device_preferences": {}
        }
        
        # Get charger device IDs from current data
        charger_ids = []
        for account_number, account_devices in self.data.get("devices", {}).items():
            for device in account_devices:
                if device.get("__typename") == "SmartFlexChargePoint":
                    charger_ids.append((device["id"], account_number))
        
        for device_id, account_number in charger_ids:
            # Initialize
            extended_data["planned_dispatches"][device_id] = []
            extended_data["charge_history"][device_id] = []
            extended_data["device_preferences"][device_id] = {}
            
            # Planned dispatches
            try:
                dispatches = await self.api.flex_planned_dispatches(device_id)
                extended_data["planned_dispatches"][device_id] = dispatches
            except Exception as err:
                _LOGGER.warning("Failed to get dispatches for device %s: %s", device_id, err)
            
            # Device preferences
            try:
                preferences = await self.api.get_smart_flex_device_preferences(account_number, device_id)
                extended_data["device_preferences"][device_id] = preferences
            except Exception as err:
                _LOGGER.warning("Failed to get preferences for device %s: %s", device_id, err)
            
            # Charge history (optional)
            try:
                history_response = await self.api.get_smart_flex_charge_history(account_number, device_id, 3)
                extended_data["charge_history"][device_id] = history_response
                
                if history_response and len(history_response) > 0:
                    sessions = history_response[0].get("chargePointChargingSession", {}).get("edges", [])
                    if sessions:
                        self._update_sessions_history(device_id, sessions)
                        
            except Exception as err:
                if "KT-CT-7899" in str(err):
                    _LOGGER.debug("No new charge history for device %s", device_id)
                else:
                    _LOGGER.warning("Failed to get charge history for device %s: %s", device_id, err)
        
        return extended_data

    def _update_sessions_history(self, device_id: str, new_sessions: list) -> None:
        """Update charging sessions history for device."""
        if device_id not in self._charging_sessions_history:
            self._charging_sessions_history[device_id] = []
        
        current_history = self._charging_sessions_history[device_id]
        
        # Add new sessions that aren't already in history
        for session_edge in new_sessions:
            session = session_edge["node"]
            session_start = session.get("start")
            
            # Check if this session is already in our history
            existing = any(
                existing_session.get("start") == session_start 
                for existing_session in current_history
            )
            
            if not existing and session_start:
                current_history.append(session)
        
        # Keep only last 30 sessions to avoid memory issues
        self._charging_sessions_history[device_id] = current_history[-30:]

    def get_sessions_history(self, device_id: str) -> list[dict]:
        """Get stored sessions history for device."""
        return self._charging_sessions_history.get(device_id, [])

    def has_charge_history(self, device_id: str) -> bool:
        """Check if device has any charge history available."""
        # Check if we have data in coordinator
        history_data = self.data.get("charge_history", {}).get(device_id, [])
        if history_data and len(history_data) > 0:
            sessions = history_data[0].get("chargePointChargingSession", {}).get("edges", [])
            if sessions:
                return True
        
        # Check if we have stored sessions
        stored_sessions = self._charging_sessions_history.get(device_id, [])
        return len(stored_sessions) > 0

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