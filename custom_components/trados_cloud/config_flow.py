"""Config flow for Trados Enterprise integration."""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .api import TradosAPIClient, TradosAuthError
from .const import (
    API_BASE_URL,
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
        self._name: str = ""
        self._region: str | None = None
        self._scan_interval: float = DEFAULT_SCAN_INTERVAL.total_seconds() / 60
        self._device_code: str | None = None
        self._user_code: str | None = None
        self._verification_uri: str | None = None
        self._verification_uri_complete: str | None = None
        self._interval: int = 5
        self._api_client: TradosAPIClient | None = None
        self._poll_result: dict[str, Any] | None = None
        self._defaults: dict[str, Any] = _load_defaults()
        self._user_display_name: str | None = None
        self._available_tenants: list[dict[str, Any]] = []

        self._global_store: Store | None = None
        self._global_data: dict[str, Any] | None = None

    async def _load_global(self) -> dict[str, Any]:
        if self._global_data is None:
            self._global_store = Store(self.hass, 1, f"{DOMAIN}_global_credentials")
            self._global_data = await self._global_store.async_load() or {}
        return self._global_data

    async def _save_global(self) -> None:
        if self._global_store and self._global_data is not None:
            await self._global_store.async_save(self._global_data)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - collect credentials."""
        errors: dict[str, str] = {}

        global_data = await self._load_global()
        default_client_id = global_data.get(CONF_CLIENT_ID, self._defaults.get("client_id", ""))
        default_client_secret = global_data.get(CONF_CLIENT_SECRET, self._defaults.get("client_secret", ""))

        # If globals exist, we can skip directly to authorization
        if default_client_id and default_client_secret and user_input is None:
            self._client_id = default_client_id
            self._client_secret = default_client_secret
            self._scan_interval = DEFAULT_SCAN_INTERVAL.total_seconds() / 60
            return await self.async_step_authorize()

        if user_input is not None:
            self._client_id = user_input.get(CONF_CLIENT_ID, default_client_id)
            self._client_secret = user_input.get(CONF_CLIENT_SECRET, default_client_secret)
            self._scan_interval = user_input.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds() / 60
            )

            # Persist global client credentials for reuse
            global_data[CONF_CLIENT_ID] = self._client_id
            global_data[CONF_CLIENT_SECRET] = self._client_secret
            self._global_data = global_data
            await self._save_global()

            return await self.async_step_authorize()

        # Show credential form only for client credentials + scan interval
        data_schema = vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID, default=default_client_id): str,
                vol.Required(CONF_CLIENT_SECRET, default=default_client_secret): str,
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
        """Show authorization URL and start polling."""
        if self._poll_result:
            # Already authorized, advance to finish
            return self.async_show_progress_done(next_step_id="select_tenant")

        if not self._api_client:
            session = async_get_clientsession(self.hass)
            # Region is not known yet; use placeholder until tenant selection
            placeholder_region = self._region or DEFAULT_REGION
            self._api_client = TradosAPIClient(
                session=session,
                client_id=self._client_id,
                client_secret=self._client_secret,
                tenant_id=self._tenant_id or "",
                region=placeholder_region,
            )

        if not self._device_code:
            try:
                device_data = await self._api_client.start_device_flow()
                self._device_code = device_data["device_code"]
                self._user_code = device_data["user_code"]
                self._verification_uri = device_data["verification_uri"]
                self._verification_uri_complete = device_data.get("verification_uri_complete")
                self._interval = device_data["interval"]

                auth_url = self._verification_uri_complete or self._verification_uri
                _LOGGER.info("Device flow started")
                _LOGGER.info("Authorization URL: %s", auth_url)
                if not self._verification_uri_complete:
                    _LOGGER.info("User code: %s", self._user_code)

            except TradosAuthError as err:
                _LOGGER.error("Failed to start device flow: %s", err)
                return self.async_abort(reason="auth_failed")
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected error starting device flow: %s", err)
                return self.async_abort(reason="unknown")

        auth_url = self._verification_uri_complete or self._verification_uri
        _LOGGER.info("Authorization URL: %s", auth_url)

        # Show progress with URL and start polling immediately
        return self.async_show_progress(
            step_id="authorize",
            progress_action="authorize_device",
            description_placeholders={
                "verification_uri": auth_url,
            },
            progress_task=asyncio.create_task(self.async_poll_for_token()),
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
                    return self.async_show_progress_done(next_step_id="select_tenant")
                    
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
                    return self.async_show_progress_done(next_step_id="expired")
                    
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
        """Legacy entry point; forward to tenant selection."""
        return await self.async_step_select_tenant(user_input)

    async def async_step_select_tenant(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick which tenant/account to use."""
        if not self._poll_result:
            return self.async_abort(reason="auth_state_missing")

        if not self._available_tenants:
            abort_result = await self._async_fill_user_and_tenants()
            if abort_result:
                return abort_result

        if len(self._available_tenants) == 1 and not user_input:
            _LOGGER.info("Only one tenant available; selecting automatically")
            return await self._async_complete_flow(self._available_tenants[0])

        errors: dict[str, str] = {}
        if user_input:
            tenant_id = user_input.get(CONF_TENANT_ID)
            tenant = next((t for t in self._available_tenants if t["id"] == tenant_id), None)
            if tenant:
                return await self._async_complete_flow(tenant)
            errors["base"] = "tenant_invalid"

        def _label(tenant: dict[str, Any]) -> str:
            region = tenant.get("region") or "?"
            return f"{tenant['name']} [{region}] ({tenant['id']})"

        tenant_options = {t["id"]: _label(t) for t in self._available_tenants}

        return self.async_show_form(
            step_id="select_tenant",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TENANT_ID): vol.In(tenant_options),
                }
            ),
            errors=errors,
            description_placeholders={"user": self._user_display_name or ""},
        )

    async def _async_fill_user_and_tenants(self) -> FlowResult | None:
        """Populate user profile and accessible tenants using the fresh token."""
        if not self._api_client:
            return self.async_abort(reason="auth_state_missing")

        try:
            accounts = await self._api_client.list_my_accounts()
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Failed to fetch accounts after auth: %s", err)
            return self.async_abort(reason="user_fetch_failed")

        self._user_display_name = None
        self._available_tenants = []

        for acc in accounts:
            # Accept any reasonable identifier key
            tenant_id = None
            for key in ("accountUid", "accountId", "id", "tenantId", "uid"):
                candidate = acc.get(key)
                if candidate:
                    tenant_id = candidate
                    break

            if not tenant_id:
                continue

            name = acc.get("name") or acc.get("displayName") or tenant_id
            region = acc.get("region") or acc.get("dataCenter") or acc.get("datacenter") or acc.get("location") or DEFAULT_REGION
            self._available_tenants.append({"id": tenant_id, "name": name, "region": region})

        self._available_tenants.sort(key=lambda t: (t["name"] or "").lower())

        _LOGGER.debug(
            "Tenant discovery: raw accounts=%s; normalized tenants=%s",
            accounts,
            self._available_tenants,
        )

        if not self._available_tenants:
            _LOGGER.warning("No tenants available after discovery; accounts response: %s", accounts)
            return self.async_abort(reason="no_tenants")

        return None

    async def _async_complete_flow(self, tenant: dict[str, Any]) -> FlowResult:
        """Finalize entry creation once tenant is selected."""
        if not self._api_client:
            return self.async_abort(reason="auth_state_missing")

        self._tenant_id = tenant["id"]
        self._region = tenant.get("region") or DEFAULT_REGION
        self._api_client.tenant_id = self._tenant_id
        if self._region:
            self._api_client.base_url = API_BASE_URL.format(region=self._region)

        # Fetch user profile in tenant context to set display name
        try:
            user = await self._api_client.get_my_user()
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Failed to fetch user profile in tenant %s: %s", self._tenant_id, err)
            return self.async_abort(reason="user_fetch_failed")

        self._user_display_name = user.get("email") or user.get("fullName") or ""
        self._name = self._user_display_name or self._name or "Trados"

        await self.async_set_unique_id(f"{self._tenant_id}_{self._name}")
        self._abort_if_unique_id_configured()

        title = self._name or f"Trados Cloud ({self._tenant_id})"
        token_expires = (
            self._api_client._token_expires.isoformat()
            if self._api_client._token_expires
            else None
        )

        entry_data = {
            CONF_NAME: self._name,
            CONF_CLIENT_ID: self._client_id,
            CONF_CLIENT_SECRET: self._client_secret,
            CONF_TENANT_ID: self._tenant_id,
            CONF_REGION: self._region,
            CONF_SCAN_INTERVAL: self._scan_interval,
            CONF_ACCESS_TOKEN: self._api_client._token,
            CONF_REFRESH_TOKEN: self._api_client._refresh_token,
            CONF_TOKEN_EXPIRES: token_expires,
            "tenant_name": tenant.get("name"),
            "user_display_name": self._user_display_name,
        }

        return self.async_create_entry(title=title, data=entry_data)

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
