"""Config flow for Trados Enterprise integration."""
import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any
import webbrowser

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TradosAPIClient, TradosAPIError, TradosAuthError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    CONF_TENANT_ID,
    CONF_TOKEN_EXPIRES,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _load_defaults() -> dict[str, Any]:
    """Load default credentials from .credentials.json if it exists."""
    defaults_file = Path(__file__).parent / ".credentials.json"
    if defaults_file.exists():
        try:
            with open(defaults_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                _LOGGER.debug("Loaded default credentials from %s", defaults_file)
                return data
        except (json.JSONDecodeError, OSError) as err:
            _LOGGER.warning("Failed to load defaults from %s: %s", defaults_file, err)
    return {}


class TradosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Trados Cloud with Device Code auth."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._tenant_id: str | None = None
        self._region: str = DEFAULT_REGION
        self._scan_interval: float = DEFAULT_SCAN_INTERVAL.total_seconds() / 60
        self._device_code: str | None = None
        self._user_code: str | None = None
        self._verification_uri: str | None = None
        self._verification_uri_complete: str | None = None
        self._interval: int = 5
        self._api_client: TradosAPIClient | None = None
        self._poll_result: dict[str, Any] | None = None
        self._defaults: dict[str, Any] = _load_defaults()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - collect credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._client_id = user_input[CONF_CLIENT_ID]
            self._client_secret = user_input[CONF_CLIENT_SECRET]
            self._tenant_id = user_input[CONF_TENANT_ID]
            self._region = user_input.get(CONF_REGION, DEFAULT_REGION)
            self._scan_interval = user_input.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds() / 60
            )

            # Check if already configured
            await self.async_set_unique_id(self._tenant_id)
            self._abort_if_unique_id_configured()

            # Create API client and start device flow
            session = async_get_clientsession(self.hass)
            self._api_client = TradosAPIClient(
                session=session,
                client_id=self._client_id,
                client_secret=self._client_secret,
                tenant_id=self._tenant_id,
                region=self._region,
            )

            try:
                device_data = await self._api_client.start_device_flow()
                self._device_code = device_data["device_code"]
                self._user_code = device_data["user_code"]
                self._verification_uri = device_data["verification_uri"]
                self._verification_uri_complete = device_data.get("verification_uri_complete")
                self._interval = device_data["interval"]
                
                # Use complete URI if available (includes code), otherwise show URI and code separately
                auth_url = self._verification_uri_complete or self._verification_uri
                _LOGGER.info("Device flow started")
                _LOGGER.info("Authorization URL: %s", auth_url)
                if not self._verification_uri_complete:
                    _LOGGER.info("User code: %s", self._user_code)
                
                return await self.async_step_authorize()
                
            except TradosAuthError as err:
                _LOGGER.error("Failed to start device flow: %s", err)
                errors["base"] = "auth_failed"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error: %s", err)
                errors["base"] = "unknown"

        # Show credential form with defaults from .credentials.json if available
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_CLIENT_ID,
                    default=self._defaults.get("client_id", "")
                ): str,
                vol.Required(
                    CONF_CLIENT_SECRET,
                    default=self._defaults.get("client_secret", "")
                ): str,
                vol.Required(
                    CONF_TENANT_ID,
                    default=self._defaults.get("tenant_id", "")
                ): str,
                vol.Optional(
                    CONF_REGION,
                    default=self._defaults.get("region", DEFAULT_REGION)
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=DEFAULT_SCAN_INTERVAL.total_seconds() / 60,
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_authorize(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show authorization URL for user to click."""
        auth_url = self._verification_uri_complete or self._verification_uri
        _LOGGER.info("Authorization URL: %s", auth_url)
        
        # Show external step with clickable URL and start polling immediately
        self.hass.async_create_task(self._start_polling_after_external_step())
        
        return self.async_external_step(
            step_id="authorize",
            url=auth_url,
        )
    
    async def _start_polling_after_external_step(self) -> None:
        """Start polling in the background while external step is displayed."""
        # Give the external step UI time to display
        await asyncio.sleep(1)
        _LOGGER.debug("Starting background polling")
        
        max_attempts = 60
        for attempt in range(max_attempts):
            _LOGGER.debug("Poll attempt %s/%s (interval: %ss)", attempt + 1, max_attempts, self._interval)
            try:
                result = await self._api_client.poll_device_token(self._device_code)
                
                if result["status"] == "authorized":
                    _LOGGER.info("Device authorization successful after %s attempts", attempt + 1)
                    self._poll_result = result
                    # Complete external step and move to finish
                    self.hass.async_create_task(
                        self._async_finish_external_step()
                    )
                    return
                    
                elif result["status"] == "pending":
                    _LOGGER.debug("Still pending, sleeping %ss before next poll", self._interval)
                    await asyncio.sleep(self._interval)
                    continue
                    
                elif result["status"] == "slow_down":
                    _LOGGER.debug("Slow down requested, increasing interval")
                    self._interval += 5
                    await asyncio.sleep(self._interval)
                    continue
                    
                else:
                    _LOGGER.warning("Authorization failed or expired: %s", result.get("status"))
                    return
                    
            except Exception as err:
                _LOGGER.error("Polling error: %s", err)
                await asyncio.sleep(self._interval)
    
    async def _async_finish_external_step(self) -> None:
        """Complete the external step and move to finish."""
        self.async_external_step_done(next_step_id="finish")
    
    async def async_step_authorize_complete(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """User clicked Submit - just show progress while waiting for polling."""
        return self.async_show_progress(
            step_id="authorize_complete",
            progress_action="authorize_device",
        )

    async def async_poll_for_token(self) -> FlowResult:
        """Background task to poll for device authorization."""
        max_attempts = 60  # 5 minutes with 5 second intervals
        _LOGGER.debug("Starting device code polling (max %s attempts)", max_attempts)
        
        for attempt in range(max_attempts):
            _LOGGER.debug("Poll attempt %s/%s (interval: %ss)", attempt + 1, max_attempts, self._interval)
            try:
                result = await self._api_client.poll_device_token(self._device_code)
                
                if result["status"] == "authorized":
                    # Store token info for finish step
                    _LOGGER.info("Device authorization successful after %s attempts", attempt + 1)
                    self._poll_result = result
                    return self.async_show_progress_done(next_step_id="finish")
                    
                elif result["status"] == "pending":
                    _LOGGER.debug("Still pending, sleeping %ss before next poll", self._interval)
                    await asyncio.sleep(self._interval)
                    continue
                    
                elif result["status"] == "slow_down":
                    _LOGGER.debug("Slow down requested, increasing interval from %ss to %ss", self._interval, self._interval + 5)
                    self._interval += 5
                    await asyncio.sleep(self._interval)
                    continue
                    
                elif result["status"] == "expired":
                    _LOGGER.warning("Device code expired after %s attempts", attempt + 1)
                    return self.async_show_progress_done(next_step_id="expired")
                    
                elif result["status"] == "denied":
                    _LOGGER.warning("Authorization denied after %s attempts", attempt + 1)
                    return self.async_show_progress_done(next_step_id="denied")
                    
                else:
                    _LOGGER.error("Unknown status '%s' after %s attempts", result.get("status"), attempt + 1)
                    return self.async_show_progress_done(next_step_id="error")
                    
            except TradosAuthError as err:
                _LOGGER.error("Polling error on attempt %s: %s", attempt + 1, err)
                return self.async_show_progress_done(next_step_id="auth_error")
        
        # Timeout
        return self.async_show_progress_done(next_step_id="timeout")

    async def async_step_expired(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle expired device code."""
        return self.async_abort(reason="device_code_expired")

    async def async_step_denied(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle denied authorization."""
        return self.async_abort(reason="authorization_denied")

    async def async_step_error(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle unknown error."""
        return self.async_abort(reason="unknown")

    async def async_step_auth_error(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle authentication error."""
        return self.async_abort(reason="auth_failed")

    async def async_step_timeout(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle timeout."""
        return self.async_abort(reason="timeout")

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Finish the flow after successful authorization."""
        return self.async_create_entry(
            title=f"Trados Cloud ({self._tenant_id})",
            data={
                CONF_CLIENT_ID: self._client_id,
                CONF_CLIENT_SECRET: self._client_secret,
                CONF_TENANT_ID: self._tenant_id,
                CONF_REGION: self._region,
                CONF_SCAN_INTERVAL: self._scan_interval,
                CONF_ACCESS_TOKEN: self._api_client._token,
                CONF_REFRESH_TOKEN: self._api_client._refresh_token,
                CONF_TOKEN_EXPIRES: self._api_client._token_expires.isoformat() if self._api_client._token_expires else None,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return TradosOptionsFlowHandler(config_entry)


class TradosOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Trados Enterprise."""

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
