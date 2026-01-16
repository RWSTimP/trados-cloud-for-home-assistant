"""OAuth2 implementation for Trados Cloud."""
import logging
from typing import Any

from homeassistant.components.application_credentials import (
    AuthImplementation,
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

_LOGGER = logging.getLogger(__name__)

AUTH0_DOMAIN = "sdl-prod.eu.auth0.com"
AUTH0_AUTHORIZE_URL = f"https://{AUTH0_DOMAIN}/authorize"
AUTH0_TOKEN_URL = f"https://{AUTH0_DOMAIN}/oauth/token"
API_AUDIENCE = "https://api.eu.cloud.trados.com/"


class TradosOAuth2Implementation(config_entry_oauth2_flow.LocalOAuth2Implementation):
    """Trados Cloud OAuth2 implementation."""

    def __init__(
        self,
        hass: HomeAssistant,
        domain: str,
        client_id: str,
        client_secret: str,
        authorize_url: str,
        token_url: str,
    ) -> None:
        """Initialize Trados OAuth2 implementation."""
        super().__init__(
            hass,
            domain,
            client_id,
            client_secret,
            authorize_url,
            token_url,
        )
        self._audience = API_AUDIENCE

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data to pass to authorization endpoint."""
        return {
            "audience": self._audience,
        }

    async def async_resolve_external_data(self, external_data: Any) -> dict:
        """Resolve external data to tokens."""
        # Add audience to token request
        return await super().async_resolve_external_data(external_data)


async def async_get_auth_implementation(
    hass: HomeAssistant,
    client_id: str,
    client_secret: str,
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return auth implementation."""
    return TradosOAuth2Implementation(
        hass,
        "trados_cloud",
        client_id,
        client_secret,
        AUTH0_AUTHORIZE_URL,
        AUTH0_TOKEN_URL,
    )
