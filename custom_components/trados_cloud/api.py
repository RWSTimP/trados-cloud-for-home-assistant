"""Trados Enterprise API Client."""
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp

from .const import (
    API_AUDIENCE,
    API_BASE_URL,
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
        region: str = "eu",
    ) -> None:
        """Initialize the API client."""
        self.session = session
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.region = region
        self.base_url = API_BASE_URL.format(region=region)
        self._token: str | None = None
        self._token_expires: datetime | None = None

    async def _get_access_token(self) -> str:
        """Get or refresh the access token from Auth0."""
        # Check if we have a valid cached token
        if self._token and self._token_expires:
            if datetime.now() < self._token_expires - timedelta(minutes=5):
                return self._token

        # Request a new token
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "audience": API_AUDIENCE,
        }

        try:
            async with self.session.post(
                AUTH0_TOKEN_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Auth0 token request failed: %s", error_text)
                    raise TradosAuthError(f"Authentication failed: {response.status}")

                data = await response.json()
                self._token = data["access_token"]
                expires_in = data.get("expires_in", 86400)  # Default 24 hours
                self._token_expires = datetime.now() + timedelta(seconds=expires_in)

                _LOGGER.debug("Successfully obtained access token, expires in %s seconds", expires_in)
                return self._token

        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during authentication: %s", err)
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
            params = {
                "top": top,
                "skip": skip,
                "fields": "id,name,status,dueBy,createdAt,taskType,project,input",
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
            await self.get_assigned_tasks()
            return True
        except (TradosAPIError, TradosAuthError) as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False
