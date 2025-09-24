"""Config flow for Wizarr integration."""
import logging
import voluptuous as vol
import aiohttp

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_API_KEY, CONF_BASE_URL, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
from .api import WizarrAPIClient

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME, default="Wizarr"): str,
    vol.Required(CONF_BASE_URL): str,
    vol.Required(CONF_API_KEY): str,
    vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=10))
})


class WizarrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Wizarr."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                await self._test_credentials(
                    user_input[CONF_BASE_URL], 
                    user_input[CONF_API_KEY]
                )
                
                await self.async_set_unique_id(user_input[CONF_BASE_URL])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_NAME], 
                    data=user_input
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", 
            data_schema=DATA_SCHEMA, 
            errors=errors
        )

    async def _test_credentials(self, base_url: str, api_key: str):
        """Test if we can authenticate with the API."""
        session = async_get_clientsession(self.hass)
        client = WizarrAPIClient(base_url, api_key, session)
        
        try:
            await client.get_status()
        except aiohttp.ClientError:
            raise CannotConnect
        except Exception as err:
            if "Invalid API key" in str(err):
                raise InvalidAuth
            raise CannotConnect


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""