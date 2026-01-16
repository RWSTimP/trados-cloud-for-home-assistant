"""Config flow for Trados Cloud integration with OAuth2."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import webhook
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REGION,
    CONF_TENANT_ID,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .oauth import async_get_auth_implementation

_LOGGER = logging.getLogger(__name__)


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Handle OAuth2 flow for Trados Cloud."""

    DOMAIN = DOMAIN
    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        super().__init__()
        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._tenant_id: str | None = None
        self._region: str = DEFAULT_REGION
        self._scan_interval: float = DEFAULT_SCAN_INTERVAL.total_seconds() / 60

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data that needs to be appended to the authorize url."""
        return {
            "audience": "https://api.eu.cloud.trados.com/",
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        return await self.async_step_auth()

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle authentication step - collect credentials first."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._client_id = user_input[CONF_CLIENT_ID]
            self._client_secret = user_input[CONF_CLIENT_SECRET]
            self._tenant_id = user_input[CONF_TENANT_ID]
            self._region = user_input.get(CONF_REGION, DEFAULT_REGION)
            self._scan_interval = user_input.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds() / 60
            )

            # Set unique ID based on tenant
            await self.async_set_unique_id(self._tenant_id)
            self._abort_if_unique_id_configured()

            # Get OAuth2 implementation
            try:
                implementation = await async_get_auth_implementation(
                    self.hass, self._client_id, self._client_secret
                )
                self.flow_impl = implementation
                return await self.async_step_pick_implementation()
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error setting up OAuth2: %s", err)
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_CLIENT_SECRET): str,
                vol.Required(CONF_TENANT_ID): str,
                vol.Optional(CONF_REGION, default=DEFAULT_REGION): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=DEFAULT_SCAN_INTERVAL.total_seconds() / 60,
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
            }
        )

        return self.async_show_form(
            step_id="auth",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "docs_url": "https://github.com/yourusername/trados-cloud-ha"
            },
        )

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        """Create an entry for the flow."""
        data[CONF_CLIENT_ID] = self._client_id
        data[CONF_CLIENT_SECRET] = self._client_secret
        data[CONF_TENANT_ID] = self._tenant_id
        data[CONF_REGION] = self._region
        data[CONF_SCAN_INTERVAL] = self._scan_interval

        return self.async_create_entry(
            title=f"Trados Cloud ({self._tenant_id})",
            data=data,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return TradosOptionsFlowHandler(config_entry)


class TradosOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Trados Cloud."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.data.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds() / 60
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
                }
            ),
        )
