"""API client for Octopus Energy Spain - FIXED following original pattern."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from python_graphql_client import GraphqlClient

_LOGGER = logging.getLogger(__name__)

GRAPH_QL_ENDPOINT = "https://api.oees-kraken.energy/v1/graphql/"


class OctopusSpainAPI:
    """API client for Octopus Energy Spain - FIXED to follow original pattern."""

    def __init__(self, email: str, password: str) -> None:
        """Initialize the API client."""
        self._email = email
        self._password = password
        self._token: str | None = None
        self._client: GraphqlClient | None = None

    async def login(self) -> bool:
        """Login and get authentication token - EXACTLY like original."""
        _LOGGER.debug("Attempting login for %s", self._email)
        
        # EXACT mutation from original - only request token
        mutation = """
           mutation obtainKrakenToken($input: ObtainJSONWebTokenInput!) {
              obtainKrakenToken(input: $input) {
                token
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
            
            _LOGGER.debug("Successfully logged in")
            return True
            
        except Exception as err:
            _LOGGER.error("Error during login: %s", err)
            return False

    async def _execute_query(self, query: str, variables: dict = None) -> dict:
        """Execute a GraphQL query - NO AUTO RE-LOGIN like original."""
        if not self._client:
            raise Exception("Not authenticated - call login() first")
            
        try:
            response = await self._client.execute_async(query, variables or {})
            
            if "errors" in response:
                # Log the error but don't auto-retry - let coordinator handle it
                _LOGGER.warning("GraphQL errors: %s", response["errors"])
                raise Exception(f"GraphQL errors: {response['errors']}")
                
            return response
            
        except Exception as err:
            _LOGGER.error("Query execution failed: %s", err)
            raise

    async def get_viewer_info(self) -> dict[str, Any]:
        """Get viewer information with accounts."""
        query = """
            query GetUser { 
                viewer { 
                    id 
                    preferredName 
                    givenName 
                    familyName 
                    email 
                    mobile 
                    accounts { 
                        number 
                        __typename 
                    } 
                } 
            }
        """
        
        response = await self._execute_query(query)
        return response["data"]["viewer"]

    async def get_account_info(self, account_number: str) -> dict[str, Any]:
        """Get complete account information."""
        # Get ledgers
        ledgers_query = """
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
        
        response = await self._execute_query(ledgers_query, {"accountNumber": account_number})
        return response["data"]["account"]

    async def get_account_billing_info(self, account_number: str) -> dict[str, Any]:
        """Get account billing information including invoices - FROM ORIGINAL REPO."""
        query = """
            query GetAccountBilling($account: String!) {
              accountBillingInfo(accountNumber: $account) {
                ledgers {
                  ledgerType
                  statementsWithDetails(first: 1) {
                    edges {
                      node {
                        amount
                        consumptionStartDate
                        consumptionEndDate
                        issuedDate
                      }
                    }
                  }
                  balance
                }
              }
            }
        """
        
        response = await self._execute_query(query, {"account": account_number})
        return response["data"]["accountBillingInfo"]

    async def get_account_properties(self, account_number: str) -> dict[str, Any]:
        """Get account properties including address and contract number."""
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
                    }
                    number
                }
            }
        """
        
        response = await self._execute_query(query, {"accountNumber": account_number})
        return response["data"]["account"]

    async def get_property_meters(self, property_id: str) -> dict[str, Any]:
        """Get CUPS for electricity (ignore gas)."""
        query = """
            query GetMetersForProperty($propertyId: ID!) {
                property(id: $propertyId) {
                    id
                    electricitySupplyPoints {
                        id
                        cups
                    }
                    gasSupplyPoints {
                        id
                        cups
                    }
                }
            }
        """
        
        response = await self._execute_query(query, {"propertyId": property_id})
        return response["data"]["property"]

    async def get_electricity_agreement(self, meter_id: str) -> dict[str, Any]:
        """Get active electricity contract details."""
        query = """
            query GetElectricityAgreementsForMeter($meterId: ID!) {
                electricitySupplyPoint(id: $meterId) {
                    activeAgreement {
                        id
                        validFrom
                        validTo
                        product {
                            displayName
                        }
                    }
                    id
                }
            }
        """
        
        response = await self._execute_query(query, {"meterId": meter_id})
        return response["data"]["electricitySupplyPoint"]

    async def get_devices_with_states(self, account_number: str) -> list[dict[str, Any]]:
        """Get devices with their current states."""
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
        
        response = await self._execute_query(query, {"accountNumber": account_number})
        devices = response["data"]["devices"]
        
        _LOGGER.debug("Found %d devices for account %s", len(devices), account_number)
        return devices

    async def get_planned_dispatches(self, device_id: str) -> list[dict[str, Any]]:
        """Get planned dispatches for a device - EXACT query from traces."""
        query = """
            query FlexPlannedDispatches($deviceId: String!) { 
                flexPlannedDispatches(deviceId: $deviceId) { 
                    start 
                    end 
                    type 
                } 
            }
        """
        
        response = await self._execute_query(query, {"deviceId": device_id})
        dispatches = response["data"]["flexPlannedDispatches"]
        _LOGGER.debug("Found %d planned dispatches for device %s", len(dispatches), device_id)
        return dispatches

    async def get_device_preferences(self, account_number: str, device_id: str) -> dict[str, Any]:
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
        
        response = await self._execute_query(query, {
            "accountNumber": account_number,
            "deviceId": device_id
        })
        devices = response["data"]["devices"]
        return devices[0] if devices else {}

    async def get_charge_history(self, account_number: str, device_id: str, last: int = 5) -> list[dict[str, Any]]:
        """Get charge history."""
        query = """
            query GetSmartFlexChargeHistory($accountNumber: String!, $deviceId: String, $sessionTypes: [ChargingSessionType], $last: Int, $after: DateTime!) { 
                devices(deviceId: $deviceId, accountNumber: $accountNumber) { 
                    __typename 
                    id 
                    ... on SmartFlexChargePoint { 
                        chargePointChargingSession: chargingSessions(sessionTypes: $sessionTypes, last: $last, after: $after) { 
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
                                    } 
                                } 
                            } 
                        } 
                    } 
                } 
            }
        """
        
        # Get history from last 90 days
        after_date = (datetime.now() - timedelta(days=90)).isoformat().replace('+00:00', 'Z')
        
        response = await self._execute_query(query, {
            "accountNumber": account_number,
            "deviceId": device_id,
            "sessionTypes": ["SMART"],
            "last": last,
            "after": after_date
        })
        return response["data"]["devices"]

    async def start_boost_charge(self, device_id: str) -> dict[str, Any]:
        """Start boost charging."""
        mutation = """
            mutation FlexUpdateBoostCharge($input: UpdateBoostChargeInput!) { 
                updateBoostCharge(input: $input) { 
                    id 
                    provider 
                    deviceType 
                } 
            }
        """
        
        response = await self._execute_query(mutation, {
            "input": {
                "deviceId": device_id,
                "action": "BOOST"
            }
        })
        return response["data"]["updateBoostCharge"]

    async def stop_boost_charge(self, device_id: str) -> dict[str, Any]:
        """Stop boost charging."""
        mutation = """
            mutation FlexUpdateBoostCharge($input: UpdateBoostChargeInput!) { 
                updateBoostCharge(input: $input) { 
                    id 
                    provider 
                    deviceType 
                } 
            }
        """
        
        response = await self._execute_query(mutation, {
            "input": {
                "deviceId": device_id,
                "action": "CANCEL"
            }
        })
        return response["data"]["updateBoostCharge"]

    async def set_smart_flex_device_preferences(self, device_id: str, mode: str = "CHARGE", unit: str = "PERCENTAGE", schedules: list = None) -> dict[str, Any]:
        """Set device preferences."""
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
        
        response = await self._execute_query(mutation, {
            "input": {
                "deviceId": device_id,
                "mode": mode,
                "unit": unit,
                "schedules": schedules or []
            }
        })
        return response["data"]["setDevicePreferences"]