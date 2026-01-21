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
    GLOBAL_API_BASE_URL,
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
            time_until_expiry = (self._token_expires - datetime.now()).total_seconds()
            _LOGGER.debug("Token expires in %s seconds", time_until_expiry)
            
            if datetime.now() < self._token_expires - timedelta(minutes=5):
                _LOGGER.debug("Using cached access token")
                return self._token
        
        # Token is missing or expired - try to refresh if we have a refresh token
        if self._refresh_token:
            _LOGGER.debug("Token %s, attempting refresh", "expired or expiring soon" if self._token else "missing")
            try:
                await self._refresh_access_token()
                if self._token:
                    return self._token
            except TradosAuthError as err:
                _LOGGER.warning("Token refresh failed: %s", err)
                raise TradosAuthError("Token refresh failed, re-authentication required") from err

        # No valid token and no refresh token available
        if not self._token:
            _LOGGER.error("No access token available and no refresh token to obtain one")
            raise TradosAuthError("No access token available")
        
        return self._token

    async def _refresh_access_token(self) -> None:
        """Refresh the access token using refresh token."""
        if not self._refresh_token:
            raise TradosAuthError("No refresh token available")

        _LOGGER.debug("Refreshing access token")
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
                    _LOGGER.debug("Refresh token was rotated")
                    self._refresh_token = data["refresh_token"]

                _LOGGER.debug("Access token refreshed successfully, expires in %s seconds", expires_in)

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
        _LOGGER.debug("Polling for device token")
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
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
                _LOGGER.debug("Poll response status: %s", response.status)

                if response.status == 200:
                    # Success!
                    self._token = data["access_token"]
                    self._refresh_token = data.get("refresh_token")
                    expires_in = data.get("expires_in", 86400)
                    self._token_expires = datetime.now() + timedelta(seconds=expires_in)
                    
                    _LOGGER.info("Device authorization completed successfully")
                    _LOGGER.debug("Token expires in %s seconds", expires_in)
                    return {
                        "status": "authorized",
                        "access_token": self._token,
                        "refresh_token": self._refresh_token,
                        "expires_in": expires_in,
                        "token_expires": self._token_expires.isoformat(),
                    }

                error = data.get("error")
                _LOGGER.debug("Poll result: %s", error or "unknown")
                if error == "authorization_pending":
                    _LOGGER.debug("Authorization still pending, will retry")
                    return {"status": "pending"}
                elif error == "slow_down":
                    _LOGGER.debug("Slow down requested by server")
                    return {"status": "slow_down"}
                elif error == "expired_token":
                    _LOGGER.warning("Device code expired")
                    return {"status": "expired"}
                elif error == "access_denied":
                    _LOGGER.warning("Authorization denied by user")
                    return {"status": "denied"}
                elif error == "invalid_grant":
                    _LOGGER.warning("Device code invalid or expired")
                    return {"status": "expired"}
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
        *,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated request to the Trados API."""
        _LOGGER.debug("Making %s request to %s", method, endpoint)
        token = await self._get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if self.tenant_id:
            headers["X-LC-Tenant"] = self.tenant_id

        url = f"{(base_url or self.base_url)}{endpoint}"
        _LOGGER.debug("Full URL: %s", url)

        try:
            async with self.session.request(
                method,
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
                **kwargs,
            ) as response:
                response_text = await response.text()
                _LOGGER.debug("Response status: %s", response.status)

                if response.status == 401:
                    # Token might be expired, clear it and retry once
                    _LOGGER.warning("Received 401, token may be expired")
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

    async def get_my_user(self) -> dict[str, Any]:
        """Get current user profile."""
        data = await self._make_request("GET", "/users/me")
        _LOGGER.debug("get_my_user response: %s", data)
        return data

    async def list_my_accounts(self) -> list[dict[str, Any]]:
        """List accounts/tenants accessible to the current user."""
        data = await self._make_request("GET", "/accounts", base_url=GLOBAL_API_BASE_URL)
        _LOGGER.debug("list_my_accounts raw response: %s", data)
        if isinstance(data, dict) and "items" in data:
            return data.get("items", [])
        if isinstance(data, list):
            return data
        return []

    async def get_project_source_files(self, project_id: str) -> tuple[list[dict[str, Any]], int]:
        """Get source files for a specific project.
        
        Returns:
            Tuple of (list of source files, number of API calls made)
        """
        _LOGGER.debug("Fetching source files for project %s", project_id)
        
        all_files = []
        skip = 0
        top = 100  # Max items per page
        api_calls = 0
        
        while True:
            params = {
                "fields": "id,totalWords",
                "top": top,
                "skip": skip,
            }
            
            try:
                data = await self._make_request(
                    "GET",
                    f"/projects/{project_id}/source-files",
                    params=params
                )
                api_calls += 1
            except TradosAuthError:
                # Retry once on auth error
                data = await self._make_request(
                    "GET",
                    f"/projects/{project_id}/source-files",
                    params=params
                )
                api_calls += 1
            
            items = data.get("items", [])
            all_files.extend(items)
            
            item_count = data.get("itemCount", 0)
            
            # Check if we've retrieved all items
            if len(all_files) >= item_count or len(items) < top:
                break
            
            skip += top
        
        _LOGGER.debug("Fetched %s source files for project %s", len(all_files), project_id)
        return all_files, api_calls

    async def get_assigned_tasks(self) -> list[dict[str, Any]]:
        """Get all tasks assigned to the authenticated user."""
        _LOGGER.debug("Fetching assigned tasks")

        # Track API call count
        api_call_count = 0
        
        # Get tasks with pagination support
        all_tasks = []
        skip = 0
        top = 100  # Max items per page

        while True:
            # Include fields parameter to get project and source file IDs
            params = {
                "top": top,
                "skip": skip,
                "fields": "status,taskType,project.id,inputFiles.targetFile.sourceFile.id,dueBy",
            }

            try:
                data = await self._make_request("GET", "/tasks/assigned", params=params)
                _LOGGER.debug("Response from /tasks/assigned (skip=%s): %s", skip, data)
                api_call_count += 1
            except TradosAuthError:
                # Retry once on auth error
                data = await self._make_request("GET", "/tasks/assigned", params=params)
                _LOGGER.debug("Response from /tasks/assigned (skip=%s, retry): %s", skip, data)
                api_call_count += 1

            items = data.get("items", [])
            all_tasks.extend(items)

            item_count = data.get("itemCount", 0)
            _LOGGER.debug("Fetched %s tasks (total so far: %s)", len(items), len(all_tasks))

            # Check if we've retrieved all items
            if len(all_tasks) >= item_count or len(items) < top:
                break

            skip += top

        _LOGGER.info("Successfully fetched %s assigned tasks", len(all_tasks))
        
        # Extract unique project IDs from tasks
        project_ids = set()
        for task in all_tasks:
            project = task.get("project", {})
            project_id = project.get("id")
            if project_id:
                project_ids.add(project_id)
        
        _LOGGER.debug("Found %d unique projects", len(project_ids))
        
        # Fetch source files for each project and build word count mapping
        word_count_map = {}  # (project_id, source_file_id) -> totalWords
        
        for project_id in project_ids:
            try:
                source_files, project_api_calls = await self.get_project_source_files(project_id)
                api_call_count += project_api_calls
                for sf in source_files:
                    key = (project_id, sf.get("id"))
                    word_count_map[key] = sf.get("totalWords", 0)
                _LOGGER.debug("Fetched %d source files for project %s", len(source_files), project_id)
            except TradosAPIError as err:
                _LOGGER.warning("Failed to fetch source files for project %s: %s", project_id, err)
        
        # Enrich tasks with word counts
        for task in all_tasks:
            project_id = task.get("project", {}).get("id")
            input_files = task.get("inputFiles", [])
            
            total_words = 0
            for input_file in input_files:
                target_file = input_file.get("targetFile", {})
                source_file = target_file.get("sourceFile", {})
                source_file_id = source_file.get("id")
                
                if project_id and source_file_id:
                    key = (project_id, source_file_id)
                    words = word_count_map.get(key, 0)
                    total_words += words
            
            task["total_words"] = total_words
        
        _LOGGER.info(
            "Fetched %d tasks from %d projects using %d API calls",
            len(all_tasks),
            len(project_ids),
            api_call_count
        )
        
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
