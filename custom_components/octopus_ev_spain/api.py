"""API client for Octopus Energy Spain."""
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

    async def get_viewer_info(self) -> dict[str, Any]:
        """Get viewer information and accounts."""
        query = """
            query GetViewer {
                viewer {
                    accounts {
                        __typename
                        number
                        campaigns {
                            name
                            slug
                            expiryDate
                        }
                    }
                    email
                    familyName
                    givenName
                    preferredName
                    pronouns
                    id
                    mobile
                }
            }
        """
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["viewer"]

    async def get_devices(self, account_number: str, device_id: str | None = None) -> list[dict[str, Any]]:
        """Get smart flex devices."""
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
                        currentState
                        isSuspended
                    }
                    alerts
                    preferences {
                        mode
                        targetType
                        unit
                        schedules {
                            dayOfWeek
                            time
                            min
                            max
                        }
                    }
                    chargePointChargingSession(first: 10) {
                        edges {
                            node {
                                __typename
                                start
                                end
                                energyAdded {
                                    value
                                    unit
                                }
                                cost
                                stateOfChargeChange
                                stateOfChargeFinal
                                type
                                problems {
                                    __typename
                                    cause
                                }
                            }
                            cursor
                        }
                        pageInfo {
                            hasNextPage
                            hasPreviousPage
                            startCursor
                            endCursor
                        }
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

    async def get_account_info(self, account_number: str) -> dict[str, Any]:
        """Get account information."""
        query = """
            query GetAccount($accountNumber: String!) {
                account(accountNumber: $accountNumber) {
                    __typename
                    number
                    billingName
                    billingAddressLine1
                    billingAddressLine2
                    billingAddressLine3
                    billingAddressLine4
                    billingAddressLine5
                    billingAddressPostcode
                    ledgers {
                        __typename
                        ledgerType
                        balance
                        number
                        acceptsPayments
                        statements(first: 5) {
                            edges {
                                node {
                                    id
                                    amount
                                    consumptionStartDate
                                    consumptionEndDate
                                    issuedDate
                                    startAt
                                    endAt
                                    annulledBy
                                }
                            }
                        }
                    }
                    properties {
                        __typename
                        id
                        address
                        postcode
                        splitAddress
                        occupancyPeriods {
                            effectiveFrom
                            effectiveTo
                        }
                    }
                    maximumRefund {
                        amount
                        recommendedBalance
                        reasonToRecommendAmount
                    }
                    requestRefundEligibility {
                        canRequestRefund
                        reason
                    }
                }
            }
        """
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, {"accountNumber": account_number})
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["account"]

    async def get_property_measurements(
        self, 
        property_id: int, 
        start_at: str, 
        end_at: str, 
        utility_filters: list[dict] | None = None
    ) -> dict[str, Any]:
        """Get property measurements."""
        query = """
            query GetPropertyMeasurements($propertyId: Int!, $startAt: DateTime!, $endAt: DateTime!, $utilityFilters: [UtilityFilter!]) {
                property(id: $propertyId) {
                    __typename
                    id
                    electricitySupplyPoints {
                        __typename
                        id
                        cups
                    }
                    gasSupplyPoints {
                        __typename
                        id
                        cups
                    }
                    measurements(
                        startAt: $startAt
                        endAt: $endAt
                        utilityFilters: $utilityFilters
                    ) {
                        edges {
                            node {
                                __typename
                                startAt
                                endAt
                                value
                                unit
                                metaData {
                                    statistics
                                    utilityFilters {
                                        __typename
                                        readingDirection
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """
        
        if utility_filters is None:
            utility_filters = [{
                "electricityFilters": {
                    "readingDirection": "CONSUMPTION",
                    "readingFrequencyType": "HALF_HOURLY"
                }
            }]
        
        variables = {
            "propertyId": property_id,
            "startAt": start_at,
            "endAt": end_at,
            "utilityFilters": utility_filters
        }
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, variables)
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["property"]

    async def get_flex_planned_dispatches(self, account_number: str) -> list[dict[str, Any]]:
        """Get planned smart flex dispatches."""
        query = """
            query GetFlexDispatches($accountNumber: String!) {
                flexPlannedDispatches(accountNumber: $accountNumber) {
                    start
                    end
                    type
                }
            }
        """
        
        if not self._client:
            raise Exception("Not authenticated")
            
        response = await self._client.execute_async(query, {"accountNumber": account_number})
        
        if "errors" in response:
            raise Exception(f"GraphQL errors: {response['errors']}")
            
        return response["data"]["flexPlannedDispatches"]

    async def update_boost_charge(self, device_id: str, action: str = "BOOST") -> dict[str, Any]:
        """Update boost charging."""
        mutation = """
            mutation UpdateBoostCharge($input: BoostChargeInput!) {
                updateBoostCharge(input: $input) {
                    id
                    deviceType
                    provider
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
        return await self.update_boost_charge(device_id, "BOOST")

    async def stop_boost_charge(self, device_id: str) -> dict[str, Any]:
        """Stop boost charging."""
        return await self.update_boost_charge(device_id, "CANCEL")