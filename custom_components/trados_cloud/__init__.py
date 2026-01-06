"""The Trados Enterprise integration."""
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TradosAPIClient
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_TENANT_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import TradosDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Trados Enterprise from a config entry."""
    _LOGGER.debug("Setting up Trados Enterprise integration")

    # Create API client
    session = async_get_clientsession(hass)
    client = TradosAPIClient(
        session=session,
        client_id=entry.data[CONF_CLIENT_ID],
        client_secret=entry.data[CONF_CLIENT_SECRET],
        tenant_id=entry.data[CONF_TENANT_ID],
        region=entry.data.get(CONF_REGION, "eu"),
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

    # Store coordinator and client
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
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
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    _LOGGER.debug("Reloading Trados Enterprise integration")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
