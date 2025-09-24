"""The Wizarr integration."""
import asyncio
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_BASE_URL, 
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    SERVICE_CREATE_INVITATION,
    SERVICE_SEND_INVITATION_EMAIL
)
from .api import WizarrAPIClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

# Service schemas
CREATE_INVITATION_SCHEMA = vol.Schema({
    vol.Required("server_ids"): cv.string,
    vol.Optional("expires_in_days"): cv.positive_int,
    vol.Optional("duration"): cv.string,
    vol.Optional("library_ids"): cv.string,
    vol.Optional("allow_downloads"): cv.boolean,
    vol.Optional("allow_live_tv"): cv.boolean,
    vol.Optional("allow_mobile_uploads"): cv.boolean,
})

SEND_INVITATION_EMAIL_SCHEMA = vol.Schema({
    vol.Required("recipient_email"): cv.string,
    vol.Required("server_ids"): cv.string,
    vol.Optional("public_url"): cv.string,
    vol.Required("smtp_server"): cv.string,
    vol.Required("smtp_port"): cv.port,
    vol.Required("smtp_username"): cv.string, 
    vol.Required("smtp_password"): cv.string,
    vol.Optional("subject", default="Your Wizarr Invitation"): cv.string,
    vol.Optional("expires_in_days"): cv.positive_int,
    vol.Optional("duration"): cv.string,
    vol.Optional("library_ids"): cv.string,
    vol.Optional("allow_downloads"): cv.boolean,
    vol.Optional("allow_live_tv"): cv.boolean,
    vol.Optional("allow_mobile_uploads"): cv.boolean,
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Wizarr from a config entry."""
    base_url = entry.data[CONF_BASE_URL]
    api_key = entry.data[CONF_API_KEY]
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    session = async_get_clientsession(hass)
    client = WizarrAPIClient(base_url, api_key, session)

    coordinator = WizarrDataUpdateCoordinator(hass, client, update_interval)
    
    await coordinator.async_config_entry_first_refresh()

    # Create device registry entry
    device_registry = dr.async_get(hass)
    device_info = {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": entry.data.get("name", "Wizarr Server"),
        "manufacturer": "DJS91",
        "model": "Wizarr Server Integration",
        "sw_version": None,
        "configuration_url": base_url,
    }
    
    # Try to get version from status endpoint
    if coordinator.data and coordinator.data.get("status"):
        status_data = coordinator.data["status"]
        if isinstance(status_data, dict) and "version" in status_data:
            device_info["sw_version"] = status_data["version"]
    
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        **device_info
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": client
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def create_invitation_service(call: ServiceCall):
        """Handle create invitation service call."""
        # Parse server_ids from comma-separated string
        server_ids_str = call.data["server_ids"]
        server_ids = [int(id.strip()) for id in server_ids_str.split(",") if id.strip().isdigit()]
        
        if not server_ids:
            _LOGGER.error("No valid server IDs provided")
            return
        
        invitation_data = {
            "server_ids": server_ids,
        }
        
        # Add optional fields only if provided
        if "expires_in_days" in call.data:
            invitation_data["expires_in_days"] = call.data["expires_in_days"]
            
        if "duration" in call.data and call.data["duration"]:
            invitation_data["duration"] = call.data["duration"]
        else:
            invitation_data["unlimited"] = True
            
        if "library_ids" in call.data and call.data["library_ids"]:
            library_ids_str = call.data["library_ids"]
            library_ids = [int(id.strip()) for id in library_ids_str.split(",") if id.strip().isdigit()]
            if library_ids:
                invitation_data["library_ids"] = library_ids
                
        if "allow_downloads" in call.data:
            invitation_data["allow_downloads"] = call.data["allow_downloads"]
            
        if "allow_live_tv" in call.data:
            invitation_data["allow_live_tv"] = call.data["allow_live_tv"]
            
        if "allow_mobile_uploads" in call.data:
            invitation_data["allow_mobile_uploads"] = call.data["allow_mobile_uploads"]
        
        try:
            result = await client.create_invitation(invitation_data)
            _LOGGER.info("Invitation created successfully. Response: %s", result)
            
            # Handle different possible response structures
            invitation = None
            invitation_id = None
            invitation_url = None
            invitation_code = None
            
            if result:
                if isinstance(result, dict):
                    # Try different possible structures
                    invitation = result.get("invitation")
                    if invitation:
                        invitation_id = invitation.get("id")
                        invitation_url = invitation.get("url")
                        invitation_code = invitation.get("code")
                    else:
                        # Maybe the invitation data is at the root level
                        invitation_id = result.get("id")
                        invitation_url = result.get("url")
                        invitation_code = result.get("code")
            
            # Fire event with invitation details
            hass.bus.async_fire("wizarr_invitation_created", {
                "invitation_id": invitation_id,
                "invitation_url": invitation_url,
                "invitation_code": invitation_code,
                "data": result
            })
            
        except Exception as err:
            _LOGGER.error("Failed to create invitation: %s", err)

    async def send_invitation_email_service(call: ServiceCall):
        """Handle send invitation email service call."""
        import smtplib
        import re
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Validate email format
        recipient = call.data["recipient_email"]
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, recipient):
            _LOGGER.error("Invalid email format: %s", recipient)
            return
        
        # Parse server_ids from comma-separated string
        server_ids_str = call.data["server_ids"]
        server_ids = [int(id.strip()) for id in server_ids_str.split(",") if id.strip().isdigit()]
        
        if not server_ids:
            _LOGGER.error("No valid server IDs provided")
            return
        
        # First create the invitation
        invitation_data = {
            "server_ids": server_ids,
        }
        
        # Add optional fields only if provided
        if "expires_in_days" in call.data:
            invitation_data["expires_in_days"] = call.data["expires_in_days"]
            
        if "duration" in call.data and call.data["duration"]:
            invitation_data["duration"] = call.data["duration"]
        else:
            invitation_data["unlimited"] = True
            
        if "library_ids" in call.data and call.data["library_ids"]:
            library_ids_str = call.data["library_ids"]
            library_ids = [int(id.strip()) for id in library_ids_str.split(",") if id.strip().isdigit()]
            if library_ids:
                invitation_data["library_ids"] = library_ids
                
        if "allow_downloads" in call.data:
            invitation_data["allow_downloads"] = call.data["allow_downloads"]
            
        if "allow_live_tv" in call.data:
            invitation_data["allow_live_tv"] = call.data["allow_live_tv"]
            
        if "allow_mobile_uploads" in call.data:
            invitation_data["allow_mobile_uploads"] = call.data["allow_mobile_uploads"]
        
        try:
            # Create invitation
            invitation_result = await client.create_invitation(invitation_data)
            _LOGGER.info("Invitation API response: %s", invitation_result)
            
            # Handle different possible response structures
            invitation = None
            invitation_url = None
            
            if invitation_result:
                if isinstance(invitation_result, dict):
                    # Try different possible structures
                    invitation = invitation_result.get("invitation")
                    if invitation:
                        invitation_url = invitation.get("url")
                    else:
                        # Maybe the invitation data is at the root level
                        invitation_url = invitation_result.get("url")
                        invitation = invitation_result
            
            if not invitation_url:
                _LOGGER.error("No invitation URL received. Response: %s", invitation_result)
                return
            
            # Replace internal URL with public URL if provided
            public_url = call.data.get("public_url")
            if public_url:
                # Extract the path portion from the invitation URL
                # Example: http://192.168.1.29:5690/j/R9865DQSYP -> /j/R9865DQSYP
                import urllib.parse
                parsed_url = urllib.parse.urlparse(invitation_url)
                path_and_query = parsed_url.path
                if parsed_url.query:
                    path_and_query += "?" + parsed_url.query
                
                # Combine public URL with the path
                invitation_url = public_url.rstrip("/") + path_and_query
                _LOGGER.info("Replaced invitation URL with public URL: %s", invitation_url)
            
            # Fetch server details for personalized message
            server_name = "our media"
            server_type = "server"
            
            try:
                servers_data = await client.get_servers()
                if servers_data and isinstance(servers_data, dict):
                    servers_list = servers_data.get("servers", [])
                    # Find the first server from the provided server_ids
                    for server in servers_list:
                        if server.get("id") in server_ids:
                            server_name = server.get("name", "our media")
                            server_type = server.get("server_type", "server").title()
                            break
            except Exception as server_err:
                _LOGGER.warning("Could not fetch server details: %s", server_err)
                
            # Prepare email
            smtp_server = call.data["smtp_server"]
            smtp_port = call.data["smtp_port"]
            username = call.data["smtp_username"]
            password = call.data["smtp_password"]
            subject = call.data.get("subject", "Your Wizarr Invitation")
            
            msg = MIMEMultipart('alternative')  # For both HTML and plain text
            msg['From'] = username
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Create HTML email content
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f4f4f4;">
        <tr>
            <td align="center" style="padding: 20px;">
                <!-- Main Container -->
                <table cellpadding="0" cellspacing="0" border="0" width="600" style="max-width: 600px; background-color: #667eea; border-radius: 15px; overflow: hidden;" bgcolor="#667eea">
                    <!-- Header Section -->
                    <tr>
                        <td align="center" style="padding: 40px 20px 20px 20px;">
                            <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td align="center">
                                        <div style="width: 60px; height: 60px; background-color: rgba(255,255,255,0.2); border-radius: 50%; text-align: center; line-height: 60px; font-size: 24px; margin: 0 auto 20px auto;">🎬</div>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="color: white; font-size: 28px; font-weight: bold; padding-bottom: 10px;">
                                        Media Server Invitation
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="color: white; font-size: 18px; line-height: 1.4;">
                                        You have been invited to join the {server_name} {server_type} server!
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Content Section -->
                    <tr>
                        <td style="padding: 0 20px 20px 20px;">
                            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: white; border-radius: 10px; overflow: hidden;" bgcolor="white">
                                <tr>
                                    <td align="center" style="padding: 30px 20px 20px 20px;">
                                        <h2 style="color: #333; margin: 0 0 20px 0; font-size: 24px; font-weight: bold;">Welcome aboard! 🚀</h2>
                                        <p style="color: #666; font-size: 16px; line-height: 1.5; margin: 0 0 30px 0;">
                                            You now have access to an amazing collection of movies, TV shows, and more!
                                        </p>
                                    </td>
                                </tr>
                                
                                <!-- Button Section -->
                                <tr>
                                    <td align="center" style="padding: 0 20px 30px 20px;">
                                        <table cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td align="center" style="background-color: #ff6b6b; border-radius: 25px; padding: 15px 30px;">
                                                    <a href="{invitation_url}" style="color: white; text-decoration: none; font-weight: bold; font-size: 16px; display: block;">
                                                        Accept Your Invitation
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- Details Section -->
                                <tr>
                                    <td style="padding: 0 20px 30px 20px;">
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;" bgcolor="#f8f9fa">
                                            <tr>
                                                <td style="padding: 20px;">
                                                    <h3 style="color: #667eea; margin: 0 0 15px 0; font-size: 18px;">📋 Invitation Details</h3>
                                                    <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                                        <tr>
                                                            <td style="padding: 5px 0; color: #333; font-size: 14px;">
                                                                <strong>Server:</strong> {server_name} ({server_type})
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 5px 0; color: #333; font-size: 14px;">
                                                                <strong>Expires:</strong> {invitation_data.get('expires_in_days', 'Never')} {'days' if invitation_data.get('expires_in_days') else ''}
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 5px 0; color: #333; font-size: 14px;">
                                                                <strong>Access Level:</strong> {'Limited' if invitation_data.get('library_ids') else 'Full Library Access'}
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                
                                <!-- URL Section -->
                                <tr>
                                    <td style="padding: 0 20px 30px 20px;">
                                        <p style="font-size: 14px; color: #666; margin: 0; text-align: center; line-height: 1.4;">
                                            If the button doesn't work, copy this link to your browser:
                                        </p>
                                        <p style="font-size: 12px; color: #0066cc; margin: 10px 0 0 0; text-align: center; word-break: break-all; background-color: #f0f0f0; padding: 10px; border-radius: 3px;">
                                            {invitation_url}
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer Section -->
                    <tr>
                        <td align="center" style="padding: 20px; color: white;">
                            <p style="margin: 0 0 10px 0; font-size: 16px;">Enjoy streaming! 🍿</p>
                            <p style="margin: 0; font-size: 12px; opacity: 0.8;">If you have any issues, please contact your server administrator.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
            
            # Create plain text version for email clients that don't support HTML
            plain_body = f"""
You have been invited to join the {server_name} {server_type} server!

Click the link below to accept your invitation:
{invitation_url}

Invitation Details:
- Server: {server_name} ({server_type})
- Expires: {invitation_data.get('expires_in_days', 'Never')} {'days' if invitation_data.get('expires_in_days') else ''}
- Access Level: {'Limited' if invitation_data.get('library_ids') else 'Full Library Access'}

Enjoy!
"""
            
            # Attach both HTML and plain text versions
            msg.attach(MIMEText(plain_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            def send_email():
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()  # Always use TLS
                server.login(username, password)
                server.send_message(msg)
                server.quit()
            
            await hass.async_add_executor_job(send_email)
            
            _LOGGER.info("Invitation email sent successfully to %s", recipient)
            
            # Fire event
            hass.bus.async_fire("wizarr_invitation_email_sent", {
                "recipient": recipient,
                "invitation_id": invitation.get("id") if invitation else None,
                "invitation_url": invitation_url
            })
            
        except Exception as err:
            _LOGGER.error("Failed to send invitation email. Error: %s. Invitation data: %s", err, invitation_data)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_INVITATION,
        create_invitation_service,
        schema=CREATE_INVITATION_SCHEMA
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_INVITATION_EMAIL,
        send_invitation_email_service,
        schema=SEND_INVITATION_EMAIL_SCHEMA
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Remove services if no more entries
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_CREATE_INVITATION)
            hass.services.async_remove(DOMAIN, SERVICE_SEND_INVITATION_EMAIL)

    return unload_ok


class WizarrDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Wizarr data."""

    def __init__(self, hass: HomeAssistant, client: WizarrAPIClient, update_interval: int):
        """Initialize."""
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            data = {}
            
            # Fetch all endpoint data concurrently
            tasks = [
                ("status", self.client.get_status()),
                ("users", self.client.get_users()),
                ("invitations", self.client.get_invitations()),
                ("libraries", self.client.get_libraries()),
                ("servers", self.client.get_servers()),
                ("api_keys", self.client.get_api_keys()),
            ]
            
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            for (endpoint, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    _LOGGER.warning("Error fetching %s data: %s", endpoint, result)
                    data[endpoint] = None
                else:
                    data[endpoint] = result
                    
            return data
            
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")