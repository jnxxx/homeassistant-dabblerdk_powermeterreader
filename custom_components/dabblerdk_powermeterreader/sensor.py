"""Support for dabblerdk_powermeterreader."""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional
import traceback

from homeassistant import config_entries, core
from homeassistant.core import callback
from homeassistant.const import UnitOfEnergy, ELECTRIC_POTENTIAL_VOLT, ELECTRIC_CURRENT_AMPERE, POWER_WATT, FREQUENCY_HERTZ
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
from homeassistant.helpers.device_registry import DeviceEntryType
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorDeviceClass
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
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "energy consumption", "", False, True, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "energy returned", "", True, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "voltage", "L1", False, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "voltage", "L2", False, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "voltage", "L3", False, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "current", "L1", False, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "current", "L2", False, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "current", "L3", False, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "power", "", False, True, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "power", "L1", False, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "power", "L2", False, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "power", "L3", False, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "power returned", "", True, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "power returned", "L1", True, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "power returned", "L2", True, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "power returned", "L3", True, False, _meterclient))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "frequency", "", False, False, _meterclient))
        async_add_entities(sensors, update_before_add=True)

    except Exception as e:
        _LOGGER.warning(f"Failed to add sensors: {e}")
        _LOGGER.debug(f"{traceback.format_exc()}")
        raise PlatformNotReady


class MeterEntity(Entity):
    """Representation of a Sensor."""

    def __init__(self, config_entry_id, meterName, itemName, phase, returned, entity_registry_enabled_default, meterclient):
        """Initialize the sensor."""
        self._state = None
        self._data_date = None
        self._unit = None
        self._config_entry_id = config_entry_id
        self._meterName = meterName
        self._manufacturer = None
        self._model = None
        self._sw_version = None
        self._itemName = itemName
        self._phase = phase
        self._returned = returned
        self._icon = "mdi:home-import-outline"
        self._name = f"{self._meterName} {self._phase} {self._itemName}".replace('  ', ' ')
        self._unique_id = None # f"{DOMAIN}-{self._meterName.replace(' ', '')}-{self._phase}-{self._itemName}".replace('--', '-')
        self._meter_sn = None
        self._device_class = None
        self._meterclient = meterclient
        self._entity_registry_enabled_default = entity_registry_enabled_default
        self._dict = dict()

        if self._itemName == "energy consumption":
            self._unit = UnitOfEnergy.KILO_WATT_HOUR
            self._icon = "mdi:home-import-outline"
            self._device_class = SensorDeviceClass.ENERGY
            self._dict["state_class"] = "total_increasing"
        elif self._itemName == "energy returned":
            self._unit = UnitOfEnergy.KILO_WATT_HOUR
            self._icon = "mdi:home-export-outline"
            self._device_class = SensorDeviceClass.ENERGY
            self._dict["state_class"] = "total_increasing"
        elif self._itemName == "voltage":
            self._unit = ELECTRIC_POTENTIAL_VOLT
            self._icon = "mdi:lightning-bolt"
            self._device_class = SensorDeviceClass.VOLTAGE
        elif self._itemName == "current":
            self._unit = ELECTRIC_CURRENT_AMPERE
            self._icon = "mdi:current-ac"
            self._device_class = SensorDeviceClass.CURRENT
        elif self._itemName == "power" or self._itemName == "power returned":
            self._unit = POWER_WATT
            self._icon = "mdi:flash"
            self._device_class = SensorDeviceClass.POWER
            self._dict["state_class"] = "measurement"
        elif self._itemName == "frequency":
            self._unit = FREQUENCY_HERTZ
            self._icon = "mdi:sine-wave"
            self._device_class = SensorDeviceClass.FREQUENCY 

        _LOGGER.debug(f"Adding sensor: {self._name}")


    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._meter_sn)
            },
            "name": self._meterName,
            "manufacturer": self._manufacturer,
            "model":  self._model,
            "sw_version":  self._sw_version,
            #"entry_type": DeviceEntryType.SERVICE,
            "via_device": (DOMAIN, f"{self._meter_sn}_MEP"),
        }

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def entity_registry_enabled_default(self):
        return self._entity_registry_enabled_default

    @property
    def icon(self):
        return self._icon

    @property
    def unique_id(self):
        """The unique id of the sensor."""
        #_LOGGER.debug(f"Returning unique_id: {self._unique_id}")
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def available(self):
        return (self._state is not None)

    @property
    def device_class(self):
        return self._device_class

    @property
    def extra_state_attributes(self):
        """Return state attributes."""
        attributes = dict()
        #attributes['state_class'] = self._state_class
#        if self._device_class is not None:
#            attributes['device_class'] = self._device_class
        for key in self._dict:
            attributes[key] = self._dict[key]
        return attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    async def async_update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.debug(f"Setting status for {self._name}")

        self._state = None

        try:
            # Unique ID
            meter_sn = await self._meterclient._get_value(["Utility_SN"])
            if meter_sn is not None:
                self._meter_sn = meter_sn
                self._unique_id = f"{DOMAIN}-{self._meter_sn}-{self._phase}-{self._itemName}".replace('--', '-')

            # Measurement
            if self._itemName == "energy consumption":
                energy = await self._meterclient._get_value(["Fwd_Act_Wh"])
                if (energy is not None):
                    self._state = int(energy) / 1000
            if self._itemName == "energy returned":
                energy = await self._meterclient._get_value(["Rev_Act_Wh"])
                if (energy is not None):
                    self._state = int(energy) / 1000
            if self._itemName == "voltage":
                voltage = await self._meterclient._get_value([ self._phase + "_RMS_V"])
                if (voltage is not None):
                    self._state = int(voltage) / 1000
            if self._itemName == "current":
                current = await self._meterclient._get_value([ self._phase + "_RMS_A"])
                if (current is not None):
                    self._state = int(current) / 1000
            if self._itemName == "power" or self._itemName == "power returned":
                prop = "Fwd_W" if self._returned == False else "Rev_W"
                if (self._phase != ""):
                    prop = f"{self._phase}_{prop}"
                power = await self._meterclient._get_value([prop])
                if (power is not None):
                    self._state = int(power)
                # current = await self._meterclient._get_value([ self._phase + "_RMS_A"])
                # voltage = await self._meterclient._get_value([ self._phase + "_RMS_V"])
                # if (current is not None and voltage is not None):
                #     self._state = round((int(current) / 1000) * (int(voltage) / 1000), 3)
            if self._itemName == "frequency":
                frequency = await self._meterclient._get_value(["Freq_mHz"])
                if (frequency is not None):
                    self._state = int(frequency) / 1000

        except Exception as e:
            _LOGGER.warning(f"Failed to update sensor {self._name}: {e}")
            _LOGGER.debug(f"{traceback.format_exc()}")

        try:
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
