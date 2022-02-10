"""Support for connectedcars.io / Min Volkswagen integration."""

import logging
import asyncio
from datetime import timedelta

from homeassistant import config_entries, core
from .meter import MeterReader
from .const import DOMAIN
from homeassistant.helpers.dispatcher import async_dispatcher_send, dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.const import CONF_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "binary_sensor"]

#SIGNAL_UPDATE_REFRESH = "dabblerdk_powermeterreader"

async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug(f"async_setup_entry: [{DOMAIN}][{entry.entry_id}]")

    data = dict(entry.data)

    # Registers update listener to update config entry when options are updated, and store a reference to the unsubscribe function
    data["unsub_options_update_listener"] = entry.add_update_listener(options_update_listener)

    # Custom function to trigger polling
    async def signal_refresh(event_time=None):
        """Call ArloHub to refresh information."""
        signal = f"{DOMAIN}_{entry.entry_id}_refresh"
        _LOGGER.debug(f"Signal_refresh: {signal}")
        #hass.data[DATA_ARLO].update(update_cameras=True, update_base_station=True)
        dispatcher_send(hass, signal)
    # Setup repeating timer
    scan_interval = timedelta(seconds= entry.options.get(CONF_SCAN_INTERVAL, 300) )
    data["timer_remove"] = async_track_time_interval(hass, signal_refresh, scan_interval)


    # data["email"] = entry.data["email"]
    # data["password"] = entry.data["password"]
    # data["namespace"] = entry.data["namespace"]
    data["name"] = entry.data["name"]
    data["url"] = entry.data["url"]
    data["meterclient"] = MeterReader("", "", "", entry.data["url"])
    hass.data[DOMAIN][entry.entry_id] = data #entry.data

    # Forward the setup to the sensor platform.
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

#    await signal_refresh()
    return True


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the GitHub Custom component from yaml configuration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def options_update_listener(
    hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""

    data = hass.data[DOMAIN][entry.entry_id]
    
    # Cancel previous timer
    if (('timer_remove' in data) and (data["timer_remove"] is not None)):
        _LOGGER.debug("Remove timer")
        data["timer_remove"]()


    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, "sensor")]
        )
    )
    # Remove options_update_listener.
    hass.data[DOMAIN][entry.entry_id]["unsub_options_update_listener"]()

    # Remove config entry from domain.
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
    
