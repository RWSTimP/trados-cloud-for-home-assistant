"""Trados Enterprise API Client."""
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp

from .const import (
    API_AUDIENCE,
    API_BASE_URL,
    AUTH0_DEVICE_CODE_URL,
    AUTH0_TOKEN_URL,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REGION,
    CONF_TENANT_ID,
)

_LOGGER = logging.getLogger(__name__)


class TradosAPIError(Exception):
    """Exception for Trados API errors."""


class TradosAuthError(TradosAPIError):
    """Exception for authentication errors."""


class TradosAPIClient:
    """Trados Enterprise API Client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        region: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expires: datetime | None = None,
    ) -> None:
        """Initialize the API client."""
        self.session = session
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.region = region
        self.base_url = API_BASE_URL.format(region=region)
        self._token: str | None = access_token
        self._refresh_token: str | None = refresh_token
        self._token_expires: datetime | None = token_expires

    async def _get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        # Check if we have a valid cached token
        if self._token and self._token_expires:
            if datetime.now() < self._token_expires - timedelta(minutes=5):
                return self._token
            
            # Try to refresh if we have a refresh token
            if self._refresh_token:
                try:
                    await self._refresh_access_token()
                    return self._token
                except TradosAuthError:
                    _LOGGER.warning("Token refresh failed, need re-authentication")
                    raise TradosAuthError("Token expired and refresh failed")

        if not self._token:
            raise TradosAuthError("No access token available")
        
        return self._token

    async def _refresh_access_token(self) -> None:
        """Refresh the access token using refresh token."""
        if not self._refresh_token:
            raise TradosAuthError("No refresh token available")

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        }

        try:
            async with self.session.post(
                AUTH0_TOKEN_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Token refresh failed: %s", error_text)
                    raise TradosAuthError(f"Token refresh failed: {response.status}")

                data = await response.json()
                self._token = data["access_token"]
                expires_in = data.get("expires_in", 86400)
                self._token_expires = datetime.now() + timedelta(seconds=expires_in)
                
                # Update refresh token if provided
                if "refresh_token" in data:
                    self._refresh_token = data["refresh_token"]

                _LOGGER.debug("Access token refreshed successfully")

        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during token refresh: %s", err)
            raise TradosAuthError(f"Network error: {err}") from err

    async def start_device_flow(self) -> dict[str, Any]:
        """Start the OAuth2 device authorization flow."""
        payload = {
            "client_id": self.client_id,
            "scope": "openid profile email offline_access",
            "audience": API_AUDIENCE,
        }

        try:
            async with self.session.post(
                AUTH0_DEVICE_CODE_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Device flow start failed: %s", error_text)
                    raise TradosAuthError(f"Device flow failed: {response.status}")

                data = await response.json()
                _LOGGER.info("Device flow started successfully")
                return {
                    "device_code": data["device_code"],
                    "user_code": data["user_code"],
                    "verification_uri": data.get("verification_uri_complete", data["verification_uri"]),
                    "verification_uri_complete": data.get("verification_uri_complete"),
                    "interval": data.get("interval", 5),
                    "expires_in": data.get("expires_in", 1800),
                }

        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during device flow: %s", err)
            raise TradosAuthError(f"Network error: {err}") from err

    async def poll_device_token(self, device_code: str) -> dict[str, Any]:
        """Poll for device flow token."""
        payload = {
            "client_id": self.client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }

        try:
            async with self.session.post(
                AUTH0_TOKEN_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                data = await response.json()

                if response.status == 200:
                    # Success!
                    self._token = data["access_token"]
                    self._refresh_token = data.get("refresh_token")
                    expires_in = data.get("expires_in", 86400)
                    self._token_expires = datetime.now() + timedelta(seconds=expires_in)
                    
                    _LOGGER.info("Device authorization completed successfully")
                    return {
                        "status": "authorized",
                        "access_token": self._token,
                        "refresh_token": self._refresh_token,
                        "expires_in": expires_in,
                        "token_expires": self._token_expires.isoformat(),
                    }

                error = data.get("error")
                if error == "authorization_pending":
                    return {"status": "pending"}
                elif error == "slow_down":
                    return {"status": "slow_down"}
                elif error == "expired_token":
                    return {"status": "expired"}
                elif error == "access_denied":
                    return {"status": "denied"}
                else:
                    _LOGGER.error("Device flow error: %s", data)
                    return {"status": "error", "error": error}

        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during device flow: %s", err)
            raise TradosAuthError(f"Network error: {err}") from err

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated request to the Trados API."""
        token = await self._get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "X-LC-Tenant": self.tenant_id,
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.request(
                method,
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
                **kwargs,
            ) as response:
                response_text = await response.text()

                if response.status == 401:
                    # Token might be expired, clear it and retry once
                    self._token = None
                    self._token_expires = None
                    raise TradosAuthError("Token expired")

                if response.status not in (200, 201, 202, 204):
                    _LOGGER.error(
                        "API request failed: %s %s - Status: %s, Response: %s",
                        method,
                        endpoint,
                        response.status,
                        response_text,
                    )
                    raise TradosAPIError(
                        f"API request failed with status {response.status}"
                    )

                if response.status == 204 or not response_text:
                    return {}

                return await response.json()

        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during API request: %s", err)
            raise TradosAPIError(f"Network error: {err}") from err

    async def get_assigned_tasks(self) -> list[dict[str, Any]]:
        """Get all tasks assigned to the authenticated user."""
        _LOGGER.debug("Fetching assigned tasks")

        # Get tasks with pagination support
        all_tasks = []
        skip = 0
        top = 100  # Max items per page

        while True:
            # Remove the fields parameter for now - we'll add back what we need once we test
            params = {
                "top": top,
                "skip": skip,
            }

            try:
                data = await self._make_request("GET", "/tasks/assigned", params=params)
            except TradosAuthError:
                # Retry once on auth error
                data = await self._make_request("GET", "/tasks/assigned", params=params)

            items = data.get("items", [])
            all_tasks.extend(items)

            item_count = data.get("itemCount", 0)
            _LOGGER.debug("Fetched %s tasks (total so far: %s)", len(items), len(all_tasks))

            # Check if we've retrieved all items
            if len(all_tasks) >= item_count or len(items) < top:
                break

            skip += top

        _LOGGER.info("Successfully fetched %s assigned tasks", len(all_tasks))
        return all_tasks

    async def test_connection(self) -> bool:
        """Test the API connection and credentials."""
        try:
            # Just test authentication by getting a token
            # Don't call any API endpoints yet
            token = await self._get_access_token()
            if token:
                _LOGGER.info("Connection test successful - authentication works")
                return True
            return False
        except (TradosAPIError, TradosAuthError) as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False
