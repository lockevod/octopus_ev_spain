"""Constants for Octopus Energy Spain integration - SIMPLIFIED."""
from typing import Final

DOMAIN: Final = "octopus_ev_spain"

# Configuration keys
CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"

# Default values - SIMPLIFIED
DEFAULT_SCAN_INTERVAL: Final = 120  # 2 minutes like original repo
DEFAULT_NAME: Final = "Octopus Energy Spain"
DEFAULT_MAX_PERCENTAGE: Final = 95
DEFAULT_TARGET_TIME: Final = "10:30"

# API constants
API_ENDPOINT: Final = "https://api.oees-kraken.energy/v1/graphql/"

# Ledger types (from real traces)
SPAIN_ELECTRICITY_LEDGER: Final = "SPAIN_ELECTRICITY_LEDGER"
SPAIN_GAS_LEDGER: Final = "SPAIN_GAS_LEDGER" 
SOLAR_WALLET_LEDGER: Final = "SOLAR_WALLET_LEDGER"

# Legacy constants for backward compatibility
ELECTRICITY_LEDGER: Final = SPAIN_ELECTRICITY_LEDGER
GAS_LEDGER: Final = SPAIN_GAS_LEDGER

# Ledger friendly names (for sensors)
LEDGER_NAMES = {
    SPAIN_ELECTRICITY_LEDGER: "Electricidad",
    SPAIN_GAS_LEDGER: "Gas",
    SOLAR_WALLET_LEDGER: "Monedero Solar"
}

# Device states (from real traces)
DEVICE_STATES = [
    "SMART_CONTROL_NOT_AVAILABLE",    # Car not connected
    "SMART_CONTROL_CAPABLE",          # Car connected, ready
    "BOOSTING",                       # Boost charging active
    "SMART_CONTROL_IN_PROGRESS"       # Scheduled charging in progress
]

# State translations
DEVICE_STATE_TRANSLATIONS = {
    "SMART_CONTROL_NOT_AVAILABLE": "Desconectado",
    "SMART_CONTROL_CAPABLE": "Conectado",
    "BOOSTING": "Carga Rápida",
    "SMART_CONTROL_IN_PROGRESS": "Carga Programada"
}

# Connected states (when car is plugged in)
CONNECTED_STATES = [
    "SMART_CONTROL_CAPABLE",
    "BOOSTING", 
    "SMART_CONTROL_IN_PROGRESS"
]

# Device types
DEVICE_TYPE_CHARGE_POINT = "SmartFlexChargePoint"
DEVICE_TYPE_VEHICLE = "SmartFlexVehicle"

# Platforms
PLATFORMS: Final = ["sensor", "switch", "button", "number", "time"]

# Services
SERVICE_START_BOOST = "start_boost_charge"
SERVICE_STOP_BOOST = "stop_boost_charge"
SERVICE_REFRESH_CHARGER = "refresh_charger"
SERVICE_CHECK_CHARGER = "check_charger"
SERVICE_CAR_CONNECTED = "car_connected"
SERVICE_CAR_DISCONNECTED = "car_disconnected"
SERVICE_SET_PREFERENCES = "set_preferences"

# Service attributes
ATTR_DEVICE_ID = "device_id"
ATTR_NOTIFY = "notify"
ATTR_MAX_PERCENTAGE = "max_percentage"
ATTR_TARGET_TIME = "target_time"

# Days of the week for schedules
DAYS_OF_WEEK = [
    "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", 
    "FRIDAY", "SATURDAY", "SUNDAY"
]

# Event names for automations
EVENT_CHARGER_CHECKED = "octopus_charger_checked"
EVENT_CHARGER_REFRESHED = "octopus_charger_refreshed"
EVENT_CAR_CONNECTED = "octopus_car_connected"
EVENT_CAR_DISCONNECTED = "octopus_car_disconnected"
EVENT_PREFERENCES_UPDATED = "octopus_preferences_updated"