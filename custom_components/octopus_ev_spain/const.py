"""Constants for Octopus Energy Spain integration - CORRECTED based on real traces."""
from typing import Final

DOMAIN: Final = "octopus_ev_spain"

# Configuration keys
CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Default values
DEFAULT_SCAN_INTERVAL: Final = 120  # 2 minutes for devices
DEFAULT_NAME: Final = "Octopus Energy Spain"

# API constants
API_ENDPOINT: Final = "https://api.oees-kraken.energy/v1/graphql/"

# Ledger types (from real traces)
SPAIN_ELECTRICITY_LEDGER: Final = "SPAIN_ELECTRICITY_LEDGER"
SPAIN_GAS_LEDGER: Final = "SPAIN_GAS_LEDGER" 
SOLAR_WALLET_LEDGER: Final = "SOLAR_WALLET_LEDGER"

# Legacy constants for backward compatibility
ELECTRICITY_LEDGER: Final = SPAIN_ELECTRICITY_LEDGER
GAS_LEDGER: Final = SPAIN_GAS_LEDGER

# Device states (from real traces)
DEVICE_STATES = [
    "SMART_CONTROL_NOT_AVAILABLE",
    "SMART_CONTROL_IN_PROGRESS", 
    "BOOSTING",
    "SMART_CONTROL_CAPABLE"
]

# Device types (from real traces)
DEVICE_TYPE_CHARGE_POINT = "SmartFlexChargePoint"
DEVICE_TYPE_VEHICLE = "SmartFlexVehicle"

# Platforms
PLATFORMS: Final = ["sensor", "switch", "button"]

# Services
SERVICE_START_BOOST = "start_boost_charge"
SERVICE_STOP_BOOST = "stop_boost_charge"
SERVICE_REFRESH_CHARGER = "refresh_charger"
SERVICE_CHECK_CHARGER = "check_charger"
SERVICE_CAR_CONNECTED = "car_connected"
SERVICE_CAR_DISCONNECTED = "car_disconnected"

# Attributes
ATTR_DEVICE_ID = "device_id"
ATTR_NOTIFY = "notify"

# Charging session types (from real traces)
CHARGING_SESSION_TYPES = [
    "SMART",
    "BOOST", 
    "PUBLIC"
]

# Boost charge actions (from real traces)
BOOST_ACTION_START = "BOOST"
BOOST_ACTION_STOP = "CANCEL"