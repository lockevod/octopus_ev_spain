"""Constants for the Octopus Energy Spain integration."""
from datetime import timedelta
from typing import Final

# Integration info
DOMAIN: Final = "octopus_ev_spain"
MANUFACTURER: Final = "Lockevod"
MODEL: Final = "Spain"

# Config flow
CONF_ACCOUNT = "account"
CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"

# Default values
DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)
DEFAULT_NAME = "Octopus Energy EV España"

# API constants
GRAPH_QL_ENDPOINT = "https://api.oees-kraken.energy/v1/graphql/"

# Ledger types from API
ELECTRICITY_LEDGER = "SPAIN_ELECTRICITY_LEDGER"
SOLAR_WALLET_LEDGER = "SPAIN_SOLAR_WALLET_LEDGER"

# Friendly names for ledgers
LEDGER_NAMES = {
    ELECTRICITY_LEDGER: "Electricidad",
    SOLAR_WALLET_LEDGER: "Monedero Solar"
}

# Device types
DEVICE_TYPE_CHARGEPOINT = "SmartFlexChargePoint"
DEVICE_TYPE_VEHICLE = "SmartFlexVehicle"

# Device states
DEVICE_STATE_DISCONNECTED = "SMART_CONTROL_NOT_AVAILABLE"
DEVICE_STATE_CONNECTED = "SMART_CONTROL_CAPABLE"
DEVICE_STATE_BOOST_CHARGING = "BOOSTING"
DEVICE_STATE_SCHEDULED_CHARGING = "SMART_CONTROL_IN_PROGRESS"

# Charging session types
CHARGE_SESSION_TYPE_SMART = "SMART"
CHARGE_SESSION_TYPE_MANUAL = "MANUAL"
CHARGE_SESSION_TYPE_PUBLIC = "PUBLIC"

# Spanish tariff periods (for price calculations)
SPANISH_TARIFF_PERIODS = {
    "PEAK": {
        "name": "Punta",
        "weekdays": [0, 1, 2, 3, 4],  # Monday to Friday
        "hours": [(10, 14), (18, 22)],  # 10:00-14:00 and 18:00-22:00
    },
    "STANDARD": {
        "name": "Llano", 
        "weekdays": [0, 1, 2, 3, 4],  # Monday to Friday
        "hours": [(8, 10), (14, 18), (22, 24)],  # 8:00-10:00, 14:00-18:00, 22:00-24:00
    },
    "VALLEY": {
        "name": "Valle",
        "weekdays": [0, 1, 2, 3, 4, 5, 6],  # All week
        "hours": [(0, 8)],  # 0:00-8:00 on weekdays, all day on weekends
        "weekend_all_day": True,  # Weekends (Saturday=5, Sunday=6) are all valley
    },
}

# EV charging discount price (€/kWh)
EV_DISCOUNT_PRICE = 0.068

# Services
SERVICE_START_BOOST = "start_boost_charge"
SERVICE_STOP_BOOST = "stop_boost_charge"
SERVICE_REFRESH_CHARGER = "refresh_charger"
SERVICE_CHECK_CHARGER = "check_charger"
SERVICE_SET_PREFERENCES = "set_preferences"

# Service data keys
ATTR_DEVICE_ID = "device_id"
ATTR_MAX_PERCENTAGE = "max_percentage"
ATTR_TARGET_TIME = "target_time"
ATTR_NOTIFY = "notify"

# Error codes from API
ERROR_CODE_AUTH_FAILED = "KT-CT-1124"
ERROR_CODE_RATE_LIMITED = "KT-CT-1199"
ERROR_CODE_NO_HISTORY = "KT-CT-7899"

# Update intervals
UPDATE_INTERVAL_FAST = timedelta(minutes=1)
UPDATE_INTERVAL_NORMAL = timedelta(minutes=5)
UPDATE_INTERVAL_SLOW = timedelta(minutes=15)

# Sensor unique ID prefixes (for proper ordering)
SENSOR_PREFIX_CONTRACT_NUMBER = "01"
SENSOR_PREFIX_ADDRESS = "02"
SENSOR_PREFIX_CUPS = "03"
SENSOR_PREFIX_CONTRACT_TYPE = "04"
SENSOR_PREFIX_CONTRACT_VALID_FROM = "05"
SENSOR_PREFIX_CONTRACT_VALID_TO = "06"
SENSOR_PREFIX_ELECTRICITY_BALANCE = "07"
SENSOR_PREFIX_SOLAR_WALLET_BALANCE = "08"
SENSOR_PREFIX_LAST_INVOICE = "09"
SENSOR_PREFIX_TARIFF_PRICES = "10"
SENSOR_PREFIX_CURRENT_PRICE = "11"
SENSOR_PREFIX_CURRENT_PRICE_EV = "12"

# Device sensor prefixes
DEVICE_SENSOR_PREFIX_CONTRACT_REF = "01"
DEVICE_SENSOR_PREFIX_ADDRESS_REF = "02"
DEVICE_SENSOR_PREFIX_STATE = "03"
DEVICE_SENSOR_PREFIX_PLANNED_DISPATCHES = "04"
DEVICE_SENSOR_PREFIX_NEXT_SESSION_START = "05"
DEVICE_SENSOR_PREFIX_NEXT_SESSION_END = "06"
DEVICE_SENSOR_PREFIX_TOTAL_HOURS_TODAY = "07"
DEVICE_SENSOR_PREFIX_LAST_SESSION_DATE = "08"
DEVICE_SENSOR_PREFIX_LAST_SESSION_DURATION = "09"
DEVICE_SENSOR_PREFIX_LAST_ENERGY_ADDED = "10"
DEVICE_SENSOR_PREFIX_LAST_SESSION_COST = "11"

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

# Event names for automations
EVENT_CHARGER_CHECKED = "octopus_charger_checked"
EVENT_CHARGER_REFRESHED = "octopus_charger_refreshed"
EVENT_CAR_CONNECTED = "octopus_car_connected"
EVENT_CAR_DISCONNECTED = "octopus_car_disconnected"
EVENT_PREFERENCES_UPDATED = "octopus_preferences_updated"


# Default values for charger configuration
DEFAULT_MAX_PERCENTAGE = 95
DEFAULT_TARGET_TIME = "10:30"

# Days of the week (for preferences)
DAYS_OF_WEEK = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]

# Valid time options for target time (04:00 to 11:00 in 30-minute steps)  
VALID_TIME_OPTIONS = [
    "04:00", "04:30", "05:00", "05:30", "06:00", "06:30",
    "07:00", "07:30", "08:00", "08:30", "09:00", "09:30", 
    "10:00", "10:30", "11:00"
]

# Platforms (for future reference)
PLATFORMS = PLATFORMS = ["sensor", "switch", "number", "select"]