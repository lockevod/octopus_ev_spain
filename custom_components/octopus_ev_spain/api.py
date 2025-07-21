"""API client for Octopus Energy Spain - CORRECTED based on real HTTP traces."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from python_graphql_client import GraphqlClient

_LOGGER = logging.getLogger(__name__)

GRAPH_QL_ENDPOINT = "https://api.oees-kraken.energy/v1/graphql/"


class OctopusSpainAPI:
    """API client for Octopus Energy Spain."""

    def __init__(self, email: str, password: str) -> None:
        """Initialize the API client."""
        self._email = email
        self._password = password
        self._token: str | None = None
        self._client: GraphqlClient | None = None

    async def login(self) -> bool:
        """Login and get authentication token."""
        mutation = """
           mutation obtainKrakenToken($input: ObtainJSONWebTokenInput!) {
              obtainKrakenToken(input: $input) {
                token
                refreshToken
                refreshExpiresIn
              }
            }
        """
        variables = {"input": {"email": self._email, "password": self._password}}

        client = GraphqlClient(endpoint=GRAPH_QL_ENDPOINT)
        
        try:
            response = await client.execute_async(mutation, variables)

            if "errors" in response:
                _LOGGER.error("Login failed: %s", response["errors"])
                return False

            token_data = response["data"]["obtainKrakenToken"]
            self._token = token_data["token"]
            
            # Create authenticated client
            self._client = GraphqlClient(
                endpoint=GRAPH_QL_ENDPOINT,
                headers={"authorization": self._token}
            )
            
            _LOGGER.debug("Successfully logged in to Octopus Energy Spain API")
            return True
            
        except Exception as err:
            _LOGGER.error("Error during login: %s", err)
            return False

    async def get_user_info(self) -> dict[str, Any]:
        """Get user information - EXACT query from traces."""
        query = """
            query GetUser { 
                viewer { 
                    id 
                    preferredName 
                    givenName 
                    familyName 
                    email 
                    mobile 
                    pronouns 
                } 
            }
        """
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["viewer"]

    async def get_account_list(self) -> list[dict[str, Any]]:
        """Get account list - EXACT query from traces."""
        query = """
            query GetAccountList { 
                viewer { 
                    accounts { 
                        number 
                        __typename 
                    } 
                } 
            }
        """
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["viewer"]["accounts"]

    async def get_ledgers(self, account_number: str) -> dict[str, Any]:
        """Get account ledgers - EXACT query from traces."""
        query = """
            query GetLedgers($accountNumber: String!) { 
                account(accountNumber: $accountNumber) { 
                    ledgers { 
                        number 
                        ledgerType 
                        balance 
                        acceptsPayments 
                        __typename 
                    } 
                    number 
                    __typename 
                } 
            }
        """
        
        variables = {"accountNumber": account_number}
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["account"]

    async def get_account_properties(self, account_number: str) -> dict[str, Any]:
        """Get account properties - EXACT query from traces."""
        query = """
            query GetAccountProperties($accountNumber: String!) { 
                account(accountNumber: $accountNumber) { 
                    properties { 
                        id 
                        address 
                        splitAddress 
                        postcode 
                        occupancyPeriods { 
                            effectiveTo 
                            effectiveFrom 
                        } 
                        __typename 
                    } 
                    number 
                    __typename 
                } 
            }
        """
        
        variables = {"accountNumber": account_number}
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["account"]

    async def get_smart_flex_devices(self, account_number: str, device_id: str | None = None) -> list[dict[str, Any]]:
        """Get smart flex devices - EXACT query from traces."""
        query = """
            query GetSmartFlexDevices($accountNumber: String!, $deviceId: String) { 
                devices(accountNumber: $accountNumber, deviceId: $deviceId) { 
                    __typename 
                    id 
                    name 
                    deviceType 
                    provider 
                    propertyId 
                    status { 
                        current 
                        isSuspended 
                    } 
                    ... on SmartFlexVehicle { 
                        make 
                    } 
                } 
            }
        """
        
        variables = {
            "accountNumber": account_number,
            "deviceId": device_id
        }
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["devices"]

    async def get_smart_flex_device_states(self, account_number: str) -> list[dict[str, Any]]:
        """Get device states - EXACT query from traces."""
        query = """
            query GetSmartFlexDevicesStates($accountNumber: String!) { 
                devices(accountNumber: $accountNumber) { 
                    id 
                    __typename 
                    status { 
                        currentState 
                    } 
                } 
            }
        """
        
        variables = {"accountNumber": account_number}
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["devices"]

    async def get_smart_flex_device_state(self, account_number: str, device_id: str) -> dict[str, Any]:
        """Get specific device state - EXACT query from traces."""
        query = """
            query GetSmartFlexDeviceState($accountNumber: String!, $deviceID: String!) { 
                devices(accountNumber: $accountNumber, deviceId: $deviceID) { 
                    id 
                    __typename 
                    status { 
                        currentState 
                    } 
                } 
            }
        """
        
        variables = {
            "accountNumber": account_number,
            "deviceID": device_id
        }
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        devices = response["data"]["devices"]
        return devices[0] if devices else {}

    async def get_smart_flex_device_preferences(self, account_number: str, device_id: str | None = None) -> list[dict[str, Any]]:
        """Get device preferences - EXACT query from traces."""
        query = """
            query GetSmartFlexDevicePreferences($accountNumber: String!, $deviceId: String) { 
                devices(accountNumber: $accountNumber, deviceId: $deviceId) { 
                    id 
                    __typename 
                    preferences { 
                        targetType 
                        unit 
                        mode 
                        schedules { 
                            dayOfWeek 
                            time 
                            min 
                            max 
                        } 
                    } 
                } 
            }
        """
        
        variables = {
            "accountNumber": account_number,
            "deviceId": device_id
        }
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["devices"]

    async def get_smart_flex_device_alerts(self, account_number: str) -> list[dict[str, Any]]:
        """Get device alerts - EXACT query from traces."""
        query = """
            query GetSmartFlexDeviceAlerts($accountNumber: String!) { 
                devices(accountNumber: $accountNumber) { 
                    id 
                    __typename 
                    alerts { 
                        message 
                        publishedAt 
                    } 
                } 
            }
        """
        
        variables = {"accountNumber": account_number}
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["devices"]

    async def get_smart_flex_charge_history(self, account_number: str, device_id: str, session_types: list[str] = None, last: int = 10) -> list[dict[str, Any]]:
        """Get charge history - EXACT query from traces with fragment."""
        query = """
            query GetSmartFlexChargeHistory($accountNumber: String!, $deviceId: String, $sessionTypes: [ChargingSessionType], $last: Int, $before: DateTime, $after: DateTime!) { 
                devices(deviceId: $deviceId, accountNumber: $accountNumber) { 
                    __typename 
                    id 
                    ... on SmartFlexVehicle { 
                        vehicleChargingSession: chargingSessions(sessionTypes: $sessionTypes, last: $last, before: $before, after: $after) { 
                            __typename 
                            ...ChargeHistoryFragment 
                        } 
                    } 
                    ... on SmartFlexChargePoint { 
                        chargePointChargingSession: chargingSessions(sessionTypes: $sessionTypes, last: $last, before: $before, after: $after) { 
                            __typename 
                            ...ChargeHistoryFragment 
                        } 
                    } 
                } 
            }  
            
            fragment ChargeHistoryFragment on DeviceChargingSessionConnection { 
                edges { 
                    cursor 
                    node { 
                        __typename 
                        ... on DeviceChargingSession { 
                            __typename 
                            start 
                            end 
                            stateOfChargeChange 
                            stateOfChargeFinal 
                            energyAdded { 
                                value 
                                unit 
                            } 
                            cost { 
                                amount 
                                currency 
                            } 
                            ... on SmartFlexChargingSession { 
                                type 
                                problems { 
                                    __typename 
                                    ... on SmartFlexChargingError { 
                                        cause 
                                    } 
                                    ... on SmartFlexChargingTruncation { 
                                        truncationCause 
                                        originalAchievableStateOfCharge 
                                        achievableStateOfCharge 
                                    } 
                                } 
                            } 
                            ... on PublicChargingSession { 
                                location 
                                operatorImageUrl 
                            } 
                        } 
                    } 
                } 
                pageInfo { 
                    hasNextPage 
                    hasPreviousPage 
                    startCursor 
                    endCursor 
                } 
            }
        """
        
        if session_types is None:
            session_types = ["SMART"]
            
        # Set after date to 1 year ago
        after_date = (datetime.now() - timedelta(days=365)).isoformat() + "Z"
        
        variables = {
            "accountNumber": account_number,
            "deviceId": device_id,
            "sessionTypes": session_types,
            "last": last,
            "before": None,
            "after": after_date
        }
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["devices"]

    async def get_smart_usage(self, property_id: str, timezone: str = "Europe/Madrid", start_at: str = None, end_at: str = None) -> dict[str, Any]:
        """Get smart usage measurements - EXACT query from traces."""
        if not start_at:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            start_at = start_time.isoformat().replace('+00:00', 'Z')
            end_at = end_time.isoformat().replace('+00:00', 'Z')
            
        query = """
            query GetSmartUsage($propertyId: ID!, $timezone: String!, $startAt: DateTime!, $endAt: DateTime!, $utilityFilters: [UtilityFiltersInput!]!) { 
                property(id: $propertyId) { 
                    measurements(first: 1000, timezone: $timezone, startAt: $startAt, endAt: $endAt, utilityFilters: $utilityFilters) { 
                        edges { 
                            node { 
                                __typename 
                                value 
                                unit 
                                ... on IntervalMeasurementType { 
                                    startAt 
                                    endAt 
                                } 
                                metaData { 
                                    utilityFilters { 
                                        __typename 
                                        ... on ElectricityFiltersOutput { 
                                            readingDirection 
                                        } 
                                        ... on GasFiltersOutput { 
                                            __typename 
                                        } 
                                        ... on WaterFiltersOutput { 
                                            __typename 
                                        } 
                                    } 
                                    statistics { 
                                        label 
                                        value 
                                        type 
                                        costInclTax { 
                                            costCurrency 
                                            estimatedAmount 
                                        } 
                                        costExclTax { 
                                            costCurrency 
                                            estimatedAmount 
                                        } 
                                    } 
                                } 
                            } 
                        } 
                    } 
                } 
            }
        """
        
        # Get CUPS from property first
        meter_info = await self.get_meters_for_property(property_id)
        electricity_cups = None
        for esp in meter_info.get("electricitySupplyPoints", []):
            electricity_cups = esp.get("cups")
            break
            
        if not electricity_cups:
            raise Exception("No electricity supply point found for property")
        
        variables = {
            "propertyId": property_id,
            "timezone": timezone,
            "startAt": start_at,
            "endAt": end_at,
            "utilityFilters": [
                {
                    "electricityFilters": {
                        "readingFrequencyType": "DAY_INTERVAL",
                        "marketSupplyPointId": electricity_cups,
                        "readingDirection": "CONSUMPTION"
                    }
                }
            ]
        }
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["property"]

    async def get_meters_for_property(self, property_id: str) -> dict[str, Any]:
        """Get meters for property - EXACT query from traces."""
        query = """
            query GetMetersForProperty($propertyId: ID!) { 
                property(id: $propertyId) { 
                    id 
                    electricitySupplyPoints { 
                        id 
                        cups 
                        __typename 
                    } 
                    gasSupplyPoints { 
                        id 
                        cups 
                        __typename 
                    } 
                    __typename 
                } 
            }
        """
        
        variables = {"propertyId": property_id}
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["property"]

    async def flex_planned_dispatches(self, device_id: str) -> list[dict[str, Any]]:
        """Get flex planned dispatches - EXACT query from traces."""
        query = """
            query FlexPlannedDispatches($deviceId: String!) { 
                flexPlannedDispatches(deviceId: $deviceId) { 
                    start 
                    end 
                    type 
                } 
            }
        """
        
        variables = {"deviceId": device_id}
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["flexPlannedDispatches"]

    async def flex_update_boost_charge(self, device_id: str, action: str) -> dict[str, Any]:
        """Update boost charge - EXACT mutation from traces."""
        mutation = """
            mutation FlexUpdateBoostCharge($input: UpdateBoostChargeInput!) { 
                updateBoostCharge(input: $input) { 
                    id 
                    provider 
                    deviceType 
                } 
            }
        """
        
        variables = {
            "input": {
                "deviceId": device_id,
                "action": action
            }
        }
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(mutation, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["updateBoostCharge"]

    async def start_boost_charge(self, device_id: str) -> dict[str, Any]:
        """Start boost charging."""
        return await self.flex_update_boost_charge(device_id, "BOOST")

    async def stop_boost_charge(self, device_id: str) -> dict[str, Any]:
        """Stop boost charging."""
        return await self.flex_update_boost_charge(device_id, "CANCEL")

    # Convenience methods that combine multiple calls for compatibility
    async def get_viewer_info(self) -> dict[str, Any]:
        """Get viewer info with accounts for compatibility."""
        user_info = await self.get_user_info()
        accounts = await self.get_account_list()
        user_info["accounts"] = accounts
        return user_info

    async def get_devices(self, account_number: str, device_id: str | None = None) -> list[dict[str, Any]]:
        """Get devices with enhanced info."""
        # Get basic device info
        devices = await self.get_smart_flex_devices(account_number, device_id)
        
        # Enhance with current states and preferences
        for device in devices:
            device_id = device.get("id")
            if device_id:
                try:
                    # Get current state
                    state_info = await self.get_smart_flex_device_state(account_number, device_id)
                    if state_info and "status" in state_info:
                        device["status"]["currentState"] = state_info["status"].get("currentState")
                    
                    # Get preferences if it's a charge point
                    if device.get("__typename") == "SmartFlexChargePoint":
                        prefs = await self.get_smart_flex_device_preferences(account_number, device_id)
                        if prefs and len(prefs) > 0:
                            device["preferences"] = prefs[0].get("preferences", {})
                            
                        # Get recent charge history
                        charge_history = await self.get_smart_flex_charge_history(account_number, device_id, ["SMART"], 1)
                        if charge_history and len(charge_history) > 0:
                            device["chargePointChargingSession"] = charge_history[0].get("chargePointChargingSession", {})
                            
                except Exception as err:
                    _LOGGER.warning("Failed to get enhanced info for device %s: %s", device_id, err)
                    
        return devices

    async def get_account_info(self, account_number: str) -> dict[str, Any]:
        """Get complete account information."""
        # Get ledgers and properties
        ledgers_info = await self.get_ledgers(account_number)
        properties_info = await self.get_account_properties(account_number)
        
        # Combine the information
        account_info = {
            "number": account_number,
            "ledgers": ledgers_info.get("ledgers", []),
            "properties": properties_info.get("properties", []),
        }
        
        return account_info