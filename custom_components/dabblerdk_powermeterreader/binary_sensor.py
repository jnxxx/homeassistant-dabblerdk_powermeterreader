"""Support for dabblerdk_powermeterreader."""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional
import traceback

from homeassistant import config_entries, core
from homeassistant.core import callback
#from homeassistant.const import TEMP_CELSIUS
import homeassistant.helpers.config_validation as cv
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass #,  BinarySensorEntityDescription
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

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    config = hass.data[DOMAIN][config_entry.entry_id]
    #_LOGGER.debug(f"Config: {config}")

    _meterclient = config["meterclient"]

    try:
        sensors = []
        sensors.append(MeterBinaryEntity(config_entry.entry_id, config["name"], "Connection", BinarySensorDeviceClass.CONNECTIVITY, True, True, _meterclient))
        sensors.append(MeterBinaryEntity(config_entry.entry_id, config["name"], "Problem", BinarySensorDeviceClass.PROBLEM, True, True, _meterclient))
        async_add_entities(sensors, update_before_add=True)

    except Exception as e:
        _LOGGER.warning(f"Failed to add sensors: {e}")
        _LOGGER.debug(f"{traceback.format_exc()}")
        raise PlatformNotReady


class MeterBinaryEntity(BinarySensorEntity):
    """Representation of a BinaryEntity."""

    def __init__(self, config_entry_id, meterName, itemName, device_class, is_mep, entity_registry_enabled_default, meterclient):
        self._meterName = meterName if is_mep == False else f"{meterName} MEP"
        self._itemName = itemName
        self._is_mep = is_mep
        self._config_entry_id = config_entry_id
        #self._icon = "mdi:map"
        self._name = f"{self._meterName} {self._itemName}"
        self._unique_id = None # f"{DOMAIN}-{self._meterName.replace(' ', '')}-{self._itemName}"
        self._device_class = device_class
        self._meterclient = meterclient
        self._is_on = None
        self._entity_registry_enabled_default = entity_registry_enabled_default
        self._manufacturer = None
        self._model = None
        self._sw_version = None
        self._prev_time = None

        _LOGGER.debug(f"Adding sensor: {self._name}")

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
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def entity_registry_enabled_default(self):
        return self._entity_registry_enabled_default



    # @property
    # def entity_description(self):
    #     _LOGGER.debug(f"entity_description")
    #     ret =   BinarySensorEntityDescription(key="desc_key", name="desc_name")
    #     return (ret)

    # @property
    # def icon(self):
    #     return self._icon

    @property
    def unique_id(self):
        """The unique id of the sensor."""
        #_LOGGER.debug(f"Returning unique_id: {self._unique_id}")
        return self._unique_id

    @property
    def is_on(self):
        return self._is_on

    @property
    def available(self):
        return (self._is_on is not None)

    @property
    def device_class(self):
        return self._device_class

    async def async_update(self):
        self._is_on = None

        _LOGGER.debug(f"Setting status for {self._name}")

        try:
            # Unique ID
            meter_sn = await self._meterclient._get_value(["Utility_SN"])
            mep = "" if self._is_mep == False else "MEP"
            if meter_sn is not None:
                self._meter_sn = meter_sn
                self._unique_id = f"{DOMAIN}-{self._meter_sn}-{mep}-{self._itemName}".replace('--', '-')

            # elif self._itemName == "Health":
            #     self._is_on = str(await self._meterclient._get_value(["health", "ok"])).lower() != "true"
            # elif self._itemName == "Lamp":
            #     self._is_on = str(await self._meterclient._get_lampstatus(self._subitemName)).lower() == "true"

        except Exception as e:
            _LOGGER.warning(f"Failed to update binary sensor {self._name}: {e}")
            _LOGGER.debug(f"{traceback.format_exc()}")

        if self._itemName == "Connection":
            self._is_on = await self._meterclient._is_connected()

        if self._itemName == "Problem":
            try:
                self._is_on = False
                data = await self._meterclient._get_meter_data()

                if (data is None):
                    self._is_on = True
                    _LOGGER.debug(f"Problem: data is None")
                else:
                    if (data["CurrentDateTime"] != self._prev_time):
                        self._prev_time = data["CurrentDateTime"]
                    else:
                        self._is_on = True
                        _LOGGER.debug(f"Problem: CurrentDateTime is the same as previous")

                    try:
                        for param in ["Fwd_Act_Wh", "Rev_Act_Wh", "L1_RMS_A", "L2_RMS_A", "L3_RMS_A", "L1_RMS_V", "L2_RMS_V", "L3_RMS_V", "Fwd_W", "Rev_W", "L1_Fwd_W", "L2_Fwd_W", "L3_Fwd_W", "L1_Rev_W", "L2_Rev_W", "L3_Rev_W"]:
                            num = int(data[param])
                    except:
                        self._is_on = True
                        _LOGGER.debug(f"Problem: CurrentDateTime has not changed")

                    if (await self._meterclient._is_stuck_with_prev_value()):
                        self._is_on = True
                        _LOGGER.debug(f"Problem: Sticking with previous value")
            except:
                self._is_on = True
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
            _LOGGER.debug(f"Failed to get Manufacturer, Model & SW. Version {self._name}: {e}")
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
