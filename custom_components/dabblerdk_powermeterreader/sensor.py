"""Support for dabblerdk_powermeterreader."""

from enum import IntEnum
import logging
import traceback

from homeassistant import config_entries, core
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
)
from homeassistant.core import callback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .meter import MeterReader

_LOGGER = logging.getLogger(__name__)


class EchelonSensorType(IntEnum):
    """Supported sensor types."""

    ENERGY_FWD = 0
    ENERGY_REV = 1
    VOLTAGE = 2
    CURRENT = 3
    POWER = 4
    POWER_PHASE = 5
    POWER_REV = 6
    FREQUENCY = 7


SENSORS = [
    SensorEntityDescription(
        key=EchelonSensorType.ENERGY_FWD,
        device_class=SensorDeviceClass.ENERGY,
        entity_category=None,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=True,
        icon="mdi:home-import-outline",
        name="energy consumption",
    ),
    SensorEntityDescription(
        key=EchelonSensorType.ENERGY_REV,
        device_class=SensorDeviceClass.ENERGY,
        entity_category=None,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
        icon="mdi:home-export-outline",
        name="energy returned",
    ),
    SensorEntityDescription(
        key=EchelonSensorType.VOLTAGE,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_category=None,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_registry_enabled_default=False,
        icon="mdi:lightning-bolt",
        name="voltage",
    ),
    SensorEntityDescription(
        key=EchelonSensorType.CURRENT,
        device_class=SensorDeviceClass.CURRENT,
        entity_category=None,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_registry_enabled_default=False,
        icon="mdi:current-ac",
        name="current",
    ),
    SensorEntityDescription(
        key=EchelonSensorType.POWER,
        device_class=SensorDeviceClass.POWER,
        entity_category=None,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=True,
        icon="mdi:flash",
        name="power",
    ),
    SensorEntityDescription(
        key=EchelonSensorType.POWER_PHASE,
        device_class=SensorDeviceClass.POWER,
        entity_category=None,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        icon="mdi:flash",
        name="power",
    ),
    SensorEntityDescription(
        key=EchelonSensorType.POWER_REV,
        device_class=SensorDeviceClass.POWER,
        entity_category=None,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        icon="mdi:flash",
        name="power returned",
    ),
    SensorEntityDescription(
        key=EchelonSensorType.FREQUENCY,
        device_class=SensorDeviceClass.FREQUENCY,
        entity_category=None,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        entity_registry_enabled_default=False,
        icon="mdi:sine-wave",
        name="frequency",
    ),
]


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Set up the dabblerdk_powermeterreader sensor platform."""
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
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "",   False,  _meterclient, SENSORS[EchelonSensorType.ENERGY_FWD],    meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "",   True,   _meterclient, SENSORS[EchelonSensorType.ENERGY_REV],    meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "L1", False,  _meterclient, SENSORS[EchelonSensorType.VOLTAGE],       meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "L2", False,  _meterclient, SENSORS[EchelonSensorType.VOLTAGE],       meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "L3", False,  _meterclient, SENSORS[EchelonSensorType.VOLTAGE],       meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "L1", False,  _meterclient, SENSORS[EchelonSensorType.CURRENT],       meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "L2", False,  _meterclient, SENSORS[EchelonSensorType.CURRENT],       meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "L3", False,  _meterclient, SENSORS[EchelonSensorType.CURRENT],       meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "",   False,  _meterclient, SENSORS[EchelonSensorType.POWER],         meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "L1", False,  _meterclient, SENSORS[EchelonSensorType.POWER_PHASE],   meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "L2", False,  _meterclient, SENSORS[EchelonSensorType.POWER_PHASE],   meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "L3", False,  _meterclient, SENSORS[EchelonSensorType.POWER_PHASE],   meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "",   True,   _meterclient, SENSORS[EchelonSensorType.POWER_REV],     meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "L1", True,   _meterclient, SENSORS[EchelonSensorType.POWER_REV],     meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "L2", True,   _meterclient, SENSORS[EchelonSensorType.POWER_REV],     meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "L3", True,   _meterclient, SENSORS[EchelonSensorType.POWER_REV],     meter_sn))
        sensors.append(MeterEntity(config_entry.entry_id, config["name"], "",   False,  _meterclient, SENSORS[EchelonSensorType.FREQUENCY],     meter_sn))
        async_add_entities(sensors, update_before_add=True)
        # fmt: on

    except Exception as err:
        _LOGGER.warning("Failed to add sensors: %s", err)
        _LOGGER.debug("%s", traceback.format_exc())
        raise PlatformNotReady from err

    # # Build array of devices to keep
    # devices = []
    # devices.append((DOMAIN, meter_sn))
    # devices.append((DOMAIN, meter_sn + "_MEP"))

    # # Remove devices no longer reported
    # device_registry = dr.async_get(hass)
    # for device_entry in dr.async_entries_for_config_entry(
    #     device_registry, config_entry.entry_id
    # ):
    #     for identifier in device_entry.identifiers:
    #         _LOGGER.warning("Device: %s", identifier)
    #         if identifier not in devices:
    #             _LOGGER.warning("Removing device: %s", identifier)
    #             device_registry.async_remove_device(device_entry.id)


class MeterEntity(SensorEntity):
    """Representation of a Sensor."""

    def __init__(
        self,
        config_entry_id,
        meterName,
        phase,
        returned,
        meterclient,
        description: SensorEntityDescription,
        meter_sn,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._config_entry_id = config_entry_id
        self._meterName = meterName
        self._manufacturer = None
        self._model = None
        self._sw_version = None
        self._itemName = self.entity_description.name
        self._phase = phase
        self._returned = returned
        self._meter_sn = meter_sn
        self._meterclient = meterclient

        self._attr_native_value = None
        self._attr_name = (
            f"{self._meterName} {self._phase} {self.entity_description.name}".replace(
                "  ", " "
            )
        )
        self._attr_unique_id = f"{DOMAIN}-{self._meter_sn}-{self._phase}-{self.entity_description.name}".replace(
            "--", "-"
        )
        _LOGGER.debug(
            "Adding sensor: %s, unique_id: %s", self._attr_name, self._attr_unique_id
        )

    @property
    def device_info(self):
        """Device properties."""
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._meter_sn)
            },
            "name": self._meterName,
            "manufacturer": self._manufacturer,
            "model": self._model,
            "sw_version": self._sw_version,
            # "entry_type": DeviceEntryType.SERVICE,
            "via_device": (DOMAIN, f"{self._meter_sn}_MEP"),
        }

    @property
    def available(self):
        """Device availability."""
        return self._attr_native_value is not None

    async def async_update(self):
        """Fetch new state data for the sensor."""
        _LOGGER.debug("Setting status for %s", self._attr_name)

        self._attr_native_value = None

        try:
            # Unique ID
            meter_sn = await self._meterclient.get_metersn()
            if meter_sn is not None:
                if self._meter_sn != meter_sn:
                    self._meter_sn = meter_sn
                    self._attr_unique_id = f"{DOMAIN}-{self._meter_sn}-{self._phase}-{self.entity_description.name}".replace(
                        "--", "-"
                    )

            # Measurement
            if self._itemName == "energy consumption":
                energy = await self._meterclient.get_value(["Fwd_Act_Wh"])
                if energy is not None:
                    self._attr_native_value = int(energy) / 1000
                    # _LOGGER.warning(f"state: {self._attr_native_value}, attrib: {self.extra_state_attributes}")
            if self._itemName == "energy returned":
                energy = await self._meterclient.get_value(["Rev_Act_Wh"])
                if energy is not None:
                    self._attr_native_value = int(energy) / 1000
            if self._itemName == "voltage":
                voltage = await self._meterclient.get_value([self._phase + "_RMS_V"])
                if voltage is not None:
                    self._attr_native_value = int(voltage) / 1000
            if self._itemName == "current":
                current = await self._meterclient.get_value([self._phase + "_RMS_A"])
                if current is not None:
                    self._attr_native_value = int(current) / 1000
            if self._itemName in ("power", "power returned"):
                prop = "Fwd_W" if not self._returned else "Rev_W"
                if self._phase != "":
                    prop = f"{self._phase}_{prop}"
                power = await self._meterclient.get_value([prop])
                if power is not None:
                    self._attr_native_value = int(power)
                # current = await self._meterclient.get_value([ self._phase + "_RMS_A"])
                # voltage = await self._meterclient.get_value([ self._phase + "_RMS_V"])
                # if (current is not None and voltage is not None):
                #     self._attr_native_value = round((int(current) / 1000) * (int(voltage) / 1000), 3)
            if self._itemName == "frequency":
                frequency = await self._meterclient.get_value(["Freq_mHz"])
                if frequency is not None:
                    self._attr_native_value = int(frequency) / 1000

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Failed to update sensor %s: %s", self._attr_name, err)
            _LOGGER.debug("%s", traceback.format_exc())

        try:
            self._manufacturer = await self._meterclient.get_value(
                ["Meter_Manufacturer"]
            )
            self._model = await self._meterclient.get_value(["Meter_Model"])
            self._sw_version = await self._meterclient.get_value(["Meter_SW_Version"])
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
