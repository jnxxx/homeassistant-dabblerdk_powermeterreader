"""Support for dabblerdk_powermeterreader."""

from enum import IntEnum
import logging
import traceback

from homeassistant import config_entries, core
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import callback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .meter import MeterReader

_LOGGER = logging.getLogger(__name__)


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
    """Set up the dabblerdk_powermeterreader binary_sensor platform."""
    config = hass.data[DOMAIN][config_entry.entry_id]

    _meterclient: MeterReader = config["meterclient"]

    # Make sure we can get meter SN as it is part of the unique_id
    try:
        meter_sn = await _meterclient.get_metersn()
        if meter_sn is None:
            raise PlatformNotReady
    except Exception as err:
        raise PlatformNotReady from err

    try:
        # fmt: off
        sensors = []
        sensors.append(MeterBinaryEntity(config_entry.entry_id, config["name"], True, _meterclient, SENSORS[EchelonBinarySensorType.MEP_CONNECTIVITY], meter_sn))
        sensors.append(MeterBinaryEntity(config_entry.entry_id, config["name"], True, _meterclient, SENSORS[EchelonBinarySensorType.MEP_PROBLEM], meter_sn))
        async_add_entities(sensors, update_before_add=True)
        # fmt: on

    except Exception as err:
        _LOGGER.warning("Failed to add sensors: %s", err)
        _LOGGER.debug("%s", traceback.format_exc())
        raise PlatformNotReady from err


class MeterBinaryEntity(BinarySensorEntity):
    """Representation of a BinaryEntity."""

    def __init__(
        self,
        config_entry_id,
        meterName,
        is_mep,
        meterclient,
        description: BinarySensorEntityDescription,
        meter_sn,
    ) -> None:
        """Initialize the binarysensor."""
        self.entity_description = description
        self._meterName = meterName if is_mep is False else f"{meterName} MEP"
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
        mep = "" if not self._is_mep else "MEP"
        self._attr_unique_id = (
            f"{DOMAIN}-{self._meter_sn}-{mep}-{self.entity_description.name}".replace(
                "--", "-"
            )
        )
        _LOGGER.debug(
            "Adding sensor: %s, unique_id: %s", self._attr_name, self._attr_unique_id
        )

    @property
    def device_info(self):
        """Device properties."""
        identifier = self._meter_sn if not self._is_mep else f"{self._meter_sn}_MEP"
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, identifier)
            },
            "name": self._meterName,
            "manufacturer": self._manufacturer,
            "model": self._model,
            "sw_version": self._sw_version,
            # "entry_type": DeviceEntryType.DEVICE,
            # "via_device": (hue.DOMAIN, self.api.bridgeid),
        }

    @property
    def available(self):
        """Device availability."""
        return self._attr_is_on is not None

    async def async_update(self):
        """Fetch new state data for the sensor."""
        self._attr_is_on = None

        _LOGGER.debug("Setting status for %s", self._attr_name)

        try:
            # Unique ID
            meter_sn = await self._meterclient.get_metersn()
            if meter_sn is not None:
                if self._meter_sn != meter_sn:
                    self._meter_sn = meter_sn
                    mep = "" if not self._is_mep else "MEP"
                    self._attr_unique_id = f"{DOMAIN}-{self._meter_sn}-{mep}-{self.entity_description.name}".replace(
                        "--", "-"
                    )

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning(
                "Failed to update binary sensor %s: %s", self._attr_name, err
            )
            _LOGGER.debug("%s", traceback.format_exc())

        if self._itemName == "Connection":
            self._attr_is_on = await self._meterclient.is_connected()

        if self._itemName == "Problem":
            try:
                self._attr_is_on = False
                data = await self._meterclient.get_meter_data()

                if data is None:
                    self._attr_is_on = True
                    _LOGGER.debug("Problem: data is None")
                else:
                    if data["CurrentDateTime"] != self._prev_time:
                        self._prev_time = data["CurrentDateTime"]
                    else:
                        self._attr_is_on = True
                        _LOGGER.debug(
                            "Problem: CurrentDateTime is the same as previous"
                        )

                    try:
                        for param in [
                            "Fwd_Act_Wh",
                            "Rev_Act_Wh",
                            "L1_RMS_A",
                            "L2_RMS_A",
                            "L3_RMS_A",
                            "L1_RMS_V",
                            "L2_RMS_V",
                            "L3_RMS_V",
                            "Fwd_W",
                            "Rev_W",
                            "L1_Fwd_W",
                            "L2_Fwd_W",
                            "L3_Fwd_W",
                            "L1_Rev_W",
                            "L2_Rev_W",
                            "L3_Rev_W",
                        ]:
                            int(data[param])
                    except Exception:  # pylint: disable=broad-except
                        self._attr_is_on = True
                        _LOGGER.debug("Problem: CurrentDateTime has not changed")

                    if await self._meterclient.is_stuck_with_prev_value():
                        self._attr_is_on = True
                        _LOGGER.debug("Problem: Sticking with previous value")
            except Exception:  # pylint: disable=broad-except
                self._attr_is_on = True
                _LOGGER.debug("Problem: Exception")

        try:
            if self._is_mep:
                self._manufacturer = await self._meterclient.get_value(["ESP_SW_By"])
                self._model = await self._meterclient.get_value(["ESP_SW"])
                self._sw_version = await self._meterclient.get_value(["ESP_SW_Version"])
            else:
                self._manufacturer = await self._meterclient.get_value(
                    ["Meter_Manufacturer"]
                )
                self._model = await self._meterclient.get_value(["Meter_Model"])
                self._sw_version = await self._meterclient.get_value(
                    ["Meter_SW_Version"]
                )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.debug(
                "Failed to get Manufacturer, Model & SW. Version %s: %s",
                self._attr_name,
                err,
            )
            _LOGGER.debug("%s", traceback.format_exc())

    @property
    def should_poll(self):
        """Should Home Assistant check with the entity for an updated state?."""
        return False

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._config_entry_id}_refresh",
                self._update_callback,
            )
        )

    @callback
    def _update_callback(self):
        """Call update method."""
        self.async_schedule_update_ha_state(True)
