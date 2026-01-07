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

    # Get scan interval (convert from minutes to timedelta)
    scan_interval_minutes = entry.data.get(
        CONF_SCAN_INTERVAL,
        DEFAULT_SCAN_INTERVAL.total_seconds() / 60,
    )
    scan_interval = timedelta(minutes=scan_interval_minutes)

    # Get list of tenants (new multi-tenant structure)
    tenants = entry.data.get("tenants", [])
    
    # Fallback to single tenant for backward compatibility
    if not tenants:
        _LOGGER.debug("No tenants list found, migrating from single tenant format")
        tenants = [
            {
                "id": entry.data[CONF_TENANT_ID],
                "name": entry.data.get("tenant_name", entry.data[CONF_TENANT_ID]),
                "region": entry.data.get(CONF_REGION, "eu"),
            }
        ]
    
    _LOGGER.info("Setting up integration for %d tenant(s): %s", len(tenants), [t.get("name") for t in tenants])

    session = async_get_clientsession(hass)
    coordinators = []
    unsub_refreshes = []

    # Create a coordinator for each tenant
    for tenant in tenants:
        _LOGGER.debug("Creating coordinator for tenant: %s (%s)", tenant.get("name"), tenant["id"])
        
        # Create API client for this tenant
        client = TradosAPIClient(
            session=session,
            client_id=entry.data[CONF_CLIENT_ID],
            client_secret=entry.data[CONF_CLIENT_SECRET],
            tenant_id=tenant["id"],
            region=tenant.get("region", "eu"),
            access_token=entry.data.get(CONF_ACCESS_TOKEN),
            refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
            token_expires=token_expires,
        )

        # Create data coordinator for this tenant
        coordinator = TradosDataCoordinator(
            hass=hass,
            client=client,
            update_interval=scan_interval,
            tenant_name=tenant.get("name"),
        )

        try:
            # Fetch initial data
            await coordinator.async_config_entry_first_refresh()
        except Exception as err:
            _LOGGER.error("Failed to fetch initial data for tenant %s: %s", tenant.get("name"), err)
            # Continue with other tenants even if one fails
            continue

        # Schedule periodic refreshes
        async def _handle_refresh(now, coord=coordinator) -> None:
            await coord.async_request_refresh()

        unsub_refresh = async_track_time_interval(hass, _handle_refresh, scan_interval)
        
        coordinators.append(coordinator)
        unsub_refreshes.append(unsub_refresh)

    if not coordinators:
        _LOGGER.error("No coordinators were successfully created")
        return False

    # Store coordinators
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinators": coordinators,
        "unsub_refreshes": unsub_refreshes,
    }

    # Set up platforms
    _LOGGER.debug("Setting up platforms: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register update listener (this is managed by entry.async_on_unload automatically)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info("Trados Enterprise integration setup complete with %d coordinator(s)", len(coordinators))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Trados Enterprise integration")

    # Unload platforms first
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if not unload_ok:
        _LOGGER.error("Failed to unload platforms")
        return False

    # Remove data and cancel refresh timers
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        for unsub in data.get("unsub_refreshes", []):
            unsub()
        _LOGGER.debug("Cleaned up %d refresh timers", len(data.get("unsub_refreshes", [])))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    _LOGGER.info("Reload requested for Trados Enterprise integration")
    await hass.config_entries.async_reload(entry.entry_id)
