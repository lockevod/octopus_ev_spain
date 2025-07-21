"""API client for Octopus Energy Spain - CORRECTED based on real app traces."""
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
        """Get user information."""
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
        """Get account list."""
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
        """Get account ledgers."""
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
        """Get account properties."""
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

    # SIMPLIFIED DEVICE QUERIES BASED ON REAL TRACES
    async def get_smart_flex_devices_states(self, account_number: str) -> list[dict[str, Any]]:
        """Get device states - REAL SIMPLE query from traces."""
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
        """Get specific device state - REAL query from traces."""
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

    async def get_smart_flex_devices_basic(self, account_number: str) -> list[dict[str, Any]]:
        """Get basic device info including names."""
        query = """
            query GetSmartFlexDevices($accountNumber: String!) { 
                devices(accountNumber: $accountNumber) { 
                    __typename 
                    id 
                    name 
                    deviceType 
                    provider 
                    propertyId 
                    status { 
                        current 
                        isSuspended 
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

    async def flex_planned_dispatches(self, device_id: str) -> list[dict[str, Any]]:
        """Get flex planned dispatches - REAL query from traces."""
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

    async def get_smart_flex_charge_history(self, account_number: str, device_id: str, last: int = 10) -> list[dict[str, Any]]:
        """Get charge history - REAL query from traces with more sessions."""
        query = """
            query GetSmartFlexChargeHistory($accountNumber: String!, $deviceId: String, $sessionTypes: [ChargingSessionType], $last: Int, $before: DateTime, $after: DateTime!) { 
                devices(deviceId: $deviceId, accountNumber: $accountNumber) { 
                    __typename 
                    id 
                    ... on SmartFlexChargePoint { 
                        chargePointChargingSession: chargingSessions(sessionTypes: $sessionTypes, last: $last, before: $before, after: $after) { 
                            __typename 
                            edges { 
                                cursor 
                                node { 
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
                    } 
                } 
            }
        """
        
        # Get history from last year
        after_date = (datetime.now() - timedelta(days=365)).isoformat().replace('+00:00', 'Z')
        
        variables = {
            "accountNumber": account_number,
            "deviceId": device_id,
            "sessionTypes": ["SMART"],
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

    async def get_smart_flex_device_preferences(self, account_number: str, device_id: str) -> dict[str, Any]:
        """Get device preferences."""
        query = """
            query GetSmartFlexDevicePreferences($accountNumber: String!, $deviceId: String!) { 
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
            
        devices = response["data"]["devices"]
        return devices[0] if devices else {}

    async def set_smart_flex_device_preferences(self, device_id: str, mode: str = "CHARGE", unit: str = "PERCENTAGE", schedules: list = None) -> dict[str, Any]:
        """Set device preferences - REAL mutation from traces."""
        mutation = """
            mutation SetSmartFlexDevicePreferences($input: SmartFlexDevicePreferencesInput!) { 
                setDevicePreferences(input: $input) { 
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
        
        if schedules is None:
            schedules = []
        
        variables = {
            "input": {
                "deviceId": device_id,
                "mode": mode,
                "unit": unit,
                "schedules": schedules
            }
        }
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(mutation, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["setDevicePreferences"]

    async def flex_update_boost_charge(self, device_id: str, action: str) -> dict[str, Any]:
        """Update boost charge - REAL mutation from traces."""
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

    # COMPATIBILITY METHODS 
    async def get_viewer_info(self) -> dict[str, Any]:
        """Get viewer info with accounts for compatibility."""
        user_info = await self.get_user_info()
        accounts = await self.get_account_list()
        user_info["accounts"] = accounts
        return user_info

    async def get_account_info(self, account_number: str) -> dict[str, Any]:
        """Get complete account information."""
        ledgers_info = await self.get_ledgers(account_number)
        properties_info = await self.get_account_properties(account_number)
        
        account_info = {
            "number": account_number,
            "ledgers": ledgers_info.get("ledgers", []),
            "properties": properties_info.get("properties", []),
        }
        
        return account_info