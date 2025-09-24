"""Constants for the Wizarr integration."""

DOMAIN = "wizarr"
CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL = 30

# API endpoints
API_ENDPOINTS = {
    "status": "/status",
    "users": "/users", 
    "invitations": "/invitations",
    "libraries": "/libraries",
    "servers": "/servers",
    "api_keys": "/api-keys"
}

# Service names
SERVICE_CREATE_INVITATION = "create_invitation"
SERVICE_SEND_INVITATION_EMAIL = "send_invitation_email"

# Sensor types
SENSOR_TYPES = {
    "status": {
        "name": "Status",
        "icon": "mdi:information-outline",
        "unit": None
    },
    "users": {
        "name": "Users", 
        "icon": "mdi:account-multiple",
        "unit": None
    },
    "invitations": {
        "name": "Invitations",
        "icon": "mdi:email-multiple-outline", 
        "unit": None
    },
    "libraries": {
        "name": "Libraries",
        "icon": "mdi:library",
        "unit": None
    },
    "servers": {
        "name": "Servers",
        "icon": "mdi:server",
        "unit": None
    },
    "api_keys": {
        "name": "API Keys",
        "icon": "mdi:key",
        "unit": None
    }
}