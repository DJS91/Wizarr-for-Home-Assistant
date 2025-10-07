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

    def _enrich_invitations_with_user_emails(self, invitations_data):
        """Replace user IDs in invitations with user email addresses and library IDs with library names."""
        if not invitations_data or not self.coordinator.data:
            return invitations_data
        
        # Get users data from coordinator
        users_data = self.coordinator.data.get("users")
        
        # Build user lookup map (user_id -> email)
        user_lookup = {}
        if users_data:
            users_list = []
            
            # Handle different response structures
            if isinstance(users_data, dict):
                # Check for "data" field (common API pattern)
                if "data" in users_data:
                    users_list = users_data.get("data", [])
                # Check for "users" field
                elif "users" in users_data:
                    users_list = users_data.get("users", [])
                # If dict has list items mixed with other fields, extract the list
                else:
                    for key, value in users_data.items():
                        if isinstance(value, list) and key != "count":
                            users_list = value
                            break
            elif isinstance(users_data, list):
                users_list = users_data
            
            for user in users_list:
                if isinstance(user, dict):
                    user_id = user.get("id")
                    email = user.get("email")
                    username = user.get("username")
                    # Create a display string with both username and email if available
                    if email and username:
                        display_name = f"{username} ({email})"
                    elif email:
                        display_name = email
                    elif username:
                        display_name = username
                    else:
                        display_name = f"User {user_id}"
                    
                    if user_id:
                        user_lookup[user_id] = display_name
        
        # Get libraries data from coordinator
        libraries_data = self.coordinator.data.get("libraries")
        
        # Build library lookup map (library_id -> library_name)
        library_lookup = {}
        if libraries_data:
            libraries_list = []
            
            # Handle different response structures
            if isinstance(libraries_data, dict):
                # Check for "data" field
                if "data" in libraries_data:
                    libraries_list = libraries_data.get("data", [])
                # Check for "libraries" field
                elif "libraries" in libraries_data:
                    libraries_list = libraries_data.get("libraries", [])
                # If dict has list items mixed with other fields, extract the list
                else:
                    for key, value in libraries_data.items():
                        if isinstance(value, list) and key != "count":
                            libraries_list = value
                            break
            elif isinstance(libraries_data, list):
                libraries_list = libraries_data
            
            for library in libraries_list:
                if isinstance(library, dict):
                    library_id = library.get("id")
                    library_name = library.get("name", library.get("title", f"Library {library_id}"))
                    server_name = library.get("server_name", "")
                    
                    # Include server name if available for clarity (since you have duplicate library names)
                    if server_name and server_name != "Unknown":
                        display_name = f"{library_name} ({server_name})"
                    else:
                        display_name = library_name
                    
                    if library_id:
                        library_lookup[library_id] = display_name
        
        # Process invitations data
        import copy
        enriched_data = copy.deepcopy(invitations_data)
        
        invitations_list = []
        
        # Handle different response structures
        if isinstance(enriched_data, dict):
            # Check for "data" field (common API pattern)
            if "data" in enriched_data:
                invitations_list = enriched_data.get("data", [])
            # Check for "invitations" field
            elif "invitations" in enriched_data:
                invitations_list = enriched_data.get("invitations", [])
            # If dict has list items mixed with other fields, extract the list
            else:
                for key, value in enriched_data.items():
                    if isinstance(value, list) and key != "count":
                        invitations_list = value
                        break
        elif isinstance(enriched_data, list):
            invitations_list = enriched_data
        
        # Replace used_by user ID with email and specific_libraries IDs with names
        for invitation in invitations_list:
            if isinstance(invitation, dict):
                # Handle used_by field - it might be a string like "<User 2>", an int, or a dict
                if "used_by" in invitation:
                    used_by = invitation["used_by"]
                    
                    # Check if it's a string like "<User 2>"
                    if isinstance(used_by, str) and used_by.startswith("<User ") and used_by.endswith(">"):
                        # Extract the user ID from "<User 2>"
                        try:
                            user_id = int(used_by.replace("<User ", "").replace(">", "").strip())
                            if user_id in user_lookup:
                                invitation["used_by"] = user_lookup[user_id]
                        except (ValueError, AttributeError):
                            pass  # Keep original value if parsing fails
                    
                    # If it's a dict with id field
                    elif used_by and isinstance(used_by, dict):
                        user_id = used_by.get("id")
                        if user_id and user_id in user_lookup:
                            invitation["used_by"] = user_lookup[user_id]
                    
                    # If it's just an ID number
                    elif isinstance(used_by, int):
                        if used_by in user_lookup:
                            invitation["used_by"] = user_lookup[used_by]
                
                # Handle specific_libraries field
                if "specific_libraries" in invitation:
                    specific_libs = invitation["specific_libraries"]
                    if isinstance(specific_libs, list) and specific_libs:
                        # Replace library IDs with names
                        library_names = []
                        for lib_id in specific_libs:
                            if isinstance(lib_id, int) and lib_id in library_lookup:
                                library_names.append(library_lookup[lib_id])
                            elif isinstance(lib_id, dict) and "id" in lib_id:
                                # If it's already an object with id
                                lookup_id = lib_id.get("id")
                                if lookup_id in library_lookup:
                                    library_names.append(library_lookup[lookup_id])
                                else:
                                    library_names.append(lib_id.get("name", f"Library {lookup_id}"))
                            else:
                                library_names.append(str(lib_id))
                        
                        invitation["specific_libraries"] = library_names
        
        # Return just the enriched invitations list
        return invitations_list

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

        # Return the full data as attributes with sensor-type-specific key
        if self.sensor_type == "invitations":
            # Enrich invitations data with user emails and library names
            # This returns a list of enriched invitations
            enriched_invitations = self._enrich_invitations_with_user_emails(data)
            attributes = {"invitations": enriched_invitations}
        else:
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
