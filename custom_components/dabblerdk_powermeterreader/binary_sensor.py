"""Support for dabblerdk_powermeterreader."""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional
import traceback

from enum import IntEnum
from homeassistant import config_entries, core
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription, BinarySensorDeviceClass
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
from homeassistant.helpers.device_registry import DeviceEntryType
import voluptuous as vol
from homeassistant.exceptions import PlatformNotReady
from .meter import MeterReader

_LOGGER = logging.getLogger(__name__)
from .const import DOMAIN

#SCAN_INTERVAL = timedelta(minutes=5)

_meterclient = None


class EchelonBinarySensorType(IntEnum):
    """Supported sensor types."""

    MEP_CONNECTIVITY = 0
    MEP_PROBLEM = 1

SENSORS = [
    BinarySensorEntityDescription(
        key=EchelonBinarySensorType.MEP_CONNECTIVITY,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=None,
        entity_registry_enabled_default=True,
        name="Connection",
    ),
    BinarySensorEntityDescription(
        key=EchelonBinarySensorType.MEP_PROBLEM,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=None,
        entity_registry_enabled_default=True,
        name="Problem",
    ),
]


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    config = hass.data[DOMAIN][config_entry.entry_id]
    #_LOGGER.debug(f"Config: {config}")

    _meterclient = config["meterclient"]

    # Make sure we can get meter SN as it is part of the unique_id
    try:
        meter_sn = await _meterclient._get_metersn()
        if meter_sn is None:
            raise PlatformNotReady
    except Exception as e:
        raise PlatformNotReady

    try:
        sensors = []
        sensors.append(MeterBinaryEntity(config_entry.entry_id, config["name"], True, _meterclient, SENSORS[EchelonBinarySensorType.MEP_CONNECTIVITY], meter_sn))
        sensors.append(MeterBinaryEntity(config_entry.entry_id, config["name"], True, _meterclient, SENSORS[EchelonBinarySensorType.MEP_PROBLEM], meter_sn))
        async_add_entities(sensors, update_before_add=True)

    except Exception as e:
        _LOGGER.warning(f"Failed to add sensors: {e}")
        _LOGGER.debug(f"{traceback.format_exc()}")
        raise PlatformNotReady


class MeterBinaryEntity(BinarySensorEntity):
    """Representation of a BinaryEntity."""

    def __init__(self, config_entry_id, meterName, is_mep, meterclient, description: BinarySensorEntityDescription, meter_sn):
        self.entity_description = description
        self._meterName = meterName if is_mep == False else f"{meterName} MEP"
        self._itemName = self.entity_description.name
        self._is_mep = is_mep
        self._config_entry_id = config_entry_id
        self._meterclient = meterclient
        self._manufacturer = None
        self._model = None
        self._sw_version = None
        self._prev_time = None
        self._meter_sn = meter_sn

        self._attr_is_on = None
        self._attr_name = f"{self._meterName} {self.entity_description.name}"
        mep = "" if self._is_mep == False else "MEP"
        self._attr_unique_id = f"{DOMAIN}-{self._meter_sn}-{mep}-{self.entity_description.name}".replace('--', '-')
        _LOGGER.debug(f"Adding sensor: {self._attr_name}, unique_id: {self._attr_unique_id}")

    @property
    def device_info(self):
        identifier = self._meter_sn if self._is_mep == False else f"{self._meter_sn}_MEP"
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, identifier)
            },
            "name": self._meterName,
            "manufacturer": self._manufacturer,
            "model":  self._model,
            "sw_version":  self._sw_version,
            #"entry_type": DeviceEntryType.DEVICE,
            #"via_device": (hue.DOMAIN, self.api.bridgeid),
        }

    @property
    def available(self):
        return (self._attr_is_on is not None)

    async def async_update(self):
        self._attr_is_on = None

        _LOGGER.debug(f"Setting status for {self._attr_name}")

        try:
            # Unique ID
            meter_sn = await self._meterclient._get_metersn()
            if meter_sn is not None:
                if self._meter_sn != meter_sn:
                    self._meter_sn = meter_sn
                    mep = "" if self._is_mep == False else "MEP"
                    self._attr_unique_id = f"{DOMAIN}-{self._meter_sn}-{mep}-{self.entity_description.name}".replace('--', '-')


        except Exception as e:
            _LOGGER.warning(f"Failed to update binary sensor {self._attr_name}: {e}")
            _LOGGER.debug(f"{traceback.format_exc()}")

        if self._itemName == "Connection":
            self._attr_is_on = await self._meterclient._is_connected()

        if self._itemName == "Problem":
            try:
                self._attr_is_on = False
                data = await self._meterclient._get_meter_data()

                if (data is None):
                    self._attr_is_on = True
                    _LOGGER.debug(f"Problem: data is None")
                else:
                    if (data["CurrentDateTime"] != self._prev_time):
                        self._prev_time = data["CurrentDateTime"]
                    else:
                        self._attr_is_on = True
                        _LOGGER.debug(f"Problem: CurrentDateTime is the same as previous")

                    try:
                        for param in ["Fwd_Act_Wh", "Rev_Act_Wh", "L1_RMS_A", "L2_RMS_A", "L3_RMS_A", "L1_RMS_V", "L2_RMS_V", "L3_RMS_V", "Fwd_W", "Rev_W", "L1_Fwd_W", "L2_Fwd_W", "L3_Fwd_W", "L1_Rev_W", "L2_Rev_W", "L3_Rev_W"]:
                            num = int(data[param])
                    except:
                        self._attr_is_on = True
                        _LOGGER.debug(f"Problem: CurrentDateTime has not changed")

                    if (await self._meterclient._is_stuck_with_prev_value()):
                        self._attr_is_on = True
                        _LOGGER.debug(f"Problem: Sticking with previous value")
            except:
                self._attr_is_on = True
                _LOGGER.debug(f"Problem: Exception")

        try:
            if self._is_mep:
                self._manufacturer = await self._meterclient._get_value(["ESP_SW_By"])
                self._model = await self._meterclient._get_value(["ESP_SW"])
                self._sw_version = await self._meterclient._get_value(["ESP_SW_Version"])
            else:
                self._manufacturer = await self._meterclient._get_value(["Meter_Manufacturer"])
                self._model = await self._meterclient._get_value(["Meter_Model"])
                self._sw_version = await self._meterclient._get_value(["Meter_SW_Version"])
        except Exception as e:
            _LOGGER.debug(f"Failed to get Manufacturer, Model & SW. Version {self._attr_name}: {e}")
            _LOGGER.debug(f"{traceback.format_exc()}")



    @property
    def should_poll(self):
        """Should Home Assistant check with the entity for an updated state?"""
        return False

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_{self._config_entry_id}_refresh", self._update_callback
            )
        )

    @callback
    def _update_callback(self):
        """Call update method."""
        self.async_schedule_update_ha_state(True)
