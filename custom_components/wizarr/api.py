"""Wizarr API client."""
import asyncio
import aiohttp
import logging
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger(__name__)


class WizarrAPIClient:
    """Client for Wizarr API."""

    def __init__(self, base_url: str, api_key: str, session: aiohttp.ClientSession):
        """Initialize the API client."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = session
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an API request."""
        url = f"{self.base_url}/api{endpoint}"
        
        try:
            async with self.session.request(
                method, url, headers=self.headers, json=data
            ) as response:
                if response.status in [200, 201]:  # Handle both 200 OK and 201 Created
                    return await response.json()
                elif response.status == 401:
                    raise Exception("Invalid API key")
                else:
                    # Log the response content for debugging
                    response_text = await response.text()
                    _LOGGER.error("API request failed. Status: %s, Response: %s, URL: %s, Data: %s", 
                                response.status, response_text, url, data)
                    response.raise_for_status()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Wizarr API: %s", err)
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            raise

    async def get_status(self) -> Dict[str, Any]:
        """Get status information."""
        return await self._request("GET", "/status")

    async def get_users(self) -> Dict[str, Any]:
        """Get all users."""
        return await self._request("GET", "/users")

    async def get_invitations(self) -> Dict[str, Any]:
        """Get all invitations."""
        return await self._request("GET", "/invitations")

    async def get_libraries(self) -> Dict[str, Any]:
        """Get all libraries."""
        return await self._request("GET", "/libraries")

    async def get_servers(self) -> Dict[str, Any]:
        """Get all servers."""
        return await self._request("GET", "/servers")

    async def get_api_keys(self) -> Dict[str, Any]:
        """Get all API keys."""
        return await self._request("GET", "/api-keys")

    async def create_invitation(self, invitation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new invitation."""
        return await self._request("POST", "/invitations", invitation_data)

    async def delete_invitation(self, invitation_id: str) -> Dict[str, Any]:
        """Delete an invitation."""
        return await self._request("DELETE", f"/invitations/{invitation_id}")

    async def delete_user(self, user_id: str) -> Dict[str, Any]:
        """Delete a user."""
        return await self._request("DELETE", f"/users/{user_id}")

    async def extend_user(self, user_id: str, extension_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extend a user's expiry date."""
        return await self._request("POST", f"/users/{user_id}/extend", extension_data)