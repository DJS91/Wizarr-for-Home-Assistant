"""Wizarr sensor platform."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wizarr sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    entities = []
    for sensor_type in SENSOR_TYPES:
        entities.append(WizarrSensor(coordinator, config_entry, sensor_type))

    async_add_entities(entities)


class WizarrSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a Wizarr sensor."""

    def __init__(self, coordinator, config_entry, sensor_type):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.sensor_type = sensor_type
        self._attr_name = f"Wizarr {SENSOR_TYPES[sensor_type]['name']}"
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        self._attr_icon = SENSOR_TYPES[sensor_type]["icon"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Wizarr instance."""
        base_url = self.config_entry.data.get("base_url", "")
        device_name = self.config_entry.data.get("name", "Wizarr Server")
        
        # Try to get version from coordinator data
        sw_version = None
        if self.coordinator.data and self.coordinator.data.get("status"):
            status_data = self.coordinator.data["status"]
            if isinstance(status_data, dict) and "version" in status_data:
                sw_version = status_data["version"]
        
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name=device_name,
            manufacturer="DJS91",
            model="Wizarr Server Integration",
            sw_version=sw_version,
            configuration_url=base_url,
        )

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
            
        data = self.coordinator.data.get(self.sensor_type)
        if data is None:
            return "unavailable"
            
        # For status, return a summary
        if self.sensor_type == "status":
            return "online"
        
        # For lists, return the count
        elif isinstance(data, list):
            return len(data)
            
        # For objects with a count or total field
        elif isinstance(data, dict):
            if "total" in data:
                return data["total"]
            elif "count" in data:
                return data["count"]
            elif isinstance(data.get("data"), list):
                return len(data["data"])
            else:
                return "available"
                
        return str(data)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        if self.coordinator.data is None:
            return {}
            
        data = self.coordinator.data.get(self.sensor_type)
        if data is None:
            return {"status": "unavailable"}

        # Return the full data as attributes
        attributes = {"raw_data": data}
        
        # Add specific attributes based on sensor type
        if self.sensor_type == "status" and isinstance(data, dict):
            # Extract key status information
            for key in ["total_users", "total_invitations", "total_requests", "version"]:
                if key in data:
                    attributes[key] = data[key]
                    
        elif self.sensor_type == "users" and isinstance(data, (list, dict)):
            if isinstance(data, dict) and "data" in data:
                users_list = data["data"]
            else:
                users_list = data if isinstance(data, list) else []
                
            attributes["total_users"] = len(users_list)
            if users_list:
                # Count by server type
                servers = {}
                for user in users_list:
                    server_type = user.get("server_type", "unknown")
                    servers[server_type] = servers.get(server_type, 0) + 1
                attributes["users_by_server"] = servers
                
        elif self.sensor_type == "invitations" and isinstance(data, (list, dict)):
            if isinstance(data, dict) and "data" in data:
                invitations_list = data["data"] 
            else:
                invitations_list = data if isinstance(data, list) else []
                
            attributes["total_invitations"] = len(invitations_list)
            if invitations_list:
                # Count by status
                statuses = {}
                for invitation in invitations_list:
                    status = invitation.get("status", "unknown")
                    statuses[status] = statuses.get(status, 0) + 1
                attributes["invitations_by_status"] = statuses
                
        elif self.sensor_type == "libraries" and isinstance(data, (list, dict)):
            if isinstance(data, dict) and "data" in data:
                libraries_list = data["data"]
            else:
                libraries_list = data if isinstance(data, list) else []
                
            attributes["total_libraries"] = len(libraries_list)
            if libraries_list:
                # Count by server
                servers = {}
                for library in libraries_list:
                    server_name = library.get("server_name", "unknown")
                    servers[server_name] = servers.get(server_name, 0) + 1
                attributes["libraries_by_server"] = servers
                
        elif self.sensor_type == "servers" and isinstance(data, (list, dict)):
            if isinstance(data, dict) and "data" in data:
                servers_list = data["data"]
            else:
                servers_list = data if isinstance(data, list) else []
                
            attributes["total_servers"] = len(servers_list)
            if servers_list:
                # Count by server type
                types = {}
                for server in servers_list:
                    server_type = server.get("server_type", "unknown")
                    types[server_type] = types.get(server_type, 0) + 1
                attributes["servers_by_type"] = types
                
        elif self.sensor_type == "api_keys" and isinstance(data, (list, dict)):
            if isinstance(data, dict) and "data" in data:
                keys_list = data["data"]
            else:
                keys_list = data if isinstance(data, list) else []
                
            attributes["total_api_keys"] = len(keys_list)
            if keys_list:
                # Count active vs inactive
                active_count = sum(1 for key in keys_list if not key.get("deleted_at"))
                attributes["active_api_keys"] = active_count
                attributes["inactive_api_keys"] = len(keys_list) - active_count

        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success