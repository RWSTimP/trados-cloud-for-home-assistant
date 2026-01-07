"""The Trados Enterprise integration."""
from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TradosAPIClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_TENANT_ID,
    CONF_TOKEN_EXPIRES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import TradosDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Trados Enterprise from a config entry."""
    _LOGGER.debug("Setting up Trados Enterprise integration")

    # Parse token expiry
    token_expires = None
    if CONF_TOKEN_EXPIRES in entry.data:
        try:
            token_expires = datetime.fromisoformat(entry.data[CONF_TOKEN_EXPIRES])
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid token expiry format")

    # Create API client
    session = async_get_clientsession(hass)
    client = TradosAPIClient(
        session=session,
        client_id=entry.data[CONF_CLIENT_ID],
        client_secret=entry.data[CONF_CLIENT_SECRET],
        tenant_id=entry.data[CONF_TENANT_ID],
        region=entry.data.get(CONF_REGION, "eu"),
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        token_expires=token_expires,
    )

    # Get scan interval (convert from minutes to timedelta)
    scan_interval_minutes = entry.data.get(
        CONF_SCAN_INTERVAL,
        DEFAULT_SCAN_INTERVAL.total_seconds() / 60,
    )
    scan_interval = timedelta(minutes=scan_interval_minutes)

    # Create data coordinator
    coordinator = TradosDataCoordinator(
        hass=hass,
        client=client,
        update_interval=scan_interval,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Explicitly schedule periodic refreshes (belt-and-braces)
    async def _handle_refresh(now) -> None:
        await coordinator.async_request_refresh()

    unsub_refresh = async_track_time_interval(hass, _handle_refresh, scan_interval)

    # Store coordinator and client
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
        "unsub_refresh": unsub_refresh,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info("Trados Enterprise integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Trados Enterprise integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove data
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        if (unsub := data.get("unsub_refresh")):
            unsub()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    _LOGGER.debug("Reloading Trados Enterprise integration")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
