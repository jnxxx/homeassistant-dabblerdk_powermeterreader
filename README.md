
# Dabbler.dk reader for Echelon/NES smart power meters

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

This is a companion integration to the [Dabbler.dk](http://dabbler.dk/) MEP module for reading out power consumption values from the `Echelon/NES smart meter`. At least from model 83331-3I, which among others is used quite a lot in Denmark. 
![Echelon Smart Meter](https://github.com/jnxxx/homeassistant-dabblerdk_powermeterreader/raw/main/images/meter.png) ![NES brand](https://github.com/jnxxx/homeassistant-dabblerdk_powermeterreader/raw/main/images/nes.png)

## Hardware
Communication is done through a hardware module built by the two enthusiasts, Gert and Graves, at Dabbler.dk, which plugs into the MEP port of the meter.
Read more about it at [their blog](https://www.dabbler.dk/index.php/blog/).

The protocol is still covered by NDA, but a prototype is working.
This integration consumes a web service exposed from an ESP32 on the MEP module. It does not reveal any part of the protocol. 


## Installation
---
### Manual Installation
  1. Copy  `dabblerdk_powermeterreader`  folder into your custom_components folder in your hass configuration directory.
  2. Restart Home Assistant.

### Installation with HACS (Home Assistant Community Store)
  1. Ensure that [HACS](https://hacs.xyz/) is installed.
  2. In HACS / Integrations / Kebab menu / Custom repositories, add the url the this repository.
  3. Search for and install the `Dabbler.dk reader for Echelon/NES smart power meter` integration.
  4. Restart Home Assistant.


## Configuration

It is configurable through config flow, meaning it will popup a dialog after adding the integration.
  1. Head to Configuration --> Integrations
  2. Add new and search for `Dabbler.dk reader for Echelon/NES smart power meter` 
  3. Enter a name for your meter. It suggests "Echelon" by default, but if you plan to read multiple make it a unique name.
  4. Enter a url to the MEP module. For example: "http://" followed by its IP or name.

#### Options
By utilizing options flow it allows for updating the url to the MEP module and adjusting the scan interval / update frequency.
Default scan interval is 300 seconds, 5 minutes.
Adjustable from 5 seconds to an hour (maybe even lower when tested better).

## State and attributes
For each MEP modules connected to, it presents two devices. One to represent the MEP module and one to represent the meter.

MEP module sensors:
* MEP Connection (true if latest request succeeded)
* MEP Problem (true if the data returned is not as expected)
  
Meter sensors, consumption:
* Energy consumption [kWh] (same value as in the display)
* Power [W] (total, all phases)
* L1 power [W]
* L2 power [W]
* L3 power [W]
* L1 current [A]
* L2 current [A]
* L3 current [A]
* L1 voltage [V]
* L2 voltage [V]
* L3 voltage [V]

Meter sensors, returned to grid:
* Energy returned [kWh]
* Power returned (all phases) [W]
* L1 power returned [W]
* L2 power returned [W]
* L3 power returned [W]

Only energy consumption and total power are enabled by default, but you can enable and disable as you wish.


## Debugging
It is possible to debug log the raw response from the web service. This is done by setting up logging like below in configuration.yaml in Home Assistant. It is also possible to set the log level through a service call in UI.  

```
logger: 
  default: info
  logs: 
    custom_components.dabblerdk_powermeterreader: debug
```

## Screenshots

Configuration  
![Config](https://github.com/jnxxx/homeassistant-dabblerdk_powermeterreader/raw/main/images/config.png)

Integration  
![Config](https://github.com/jnxxx/homeassistant-dabblerdk_powermeterreader/raw/main/images/integration.png)

Devices  
![Config](https://github.com/jnxxx/homeassistant-dabblerdk_powermeterreader/raw/main/images/devicelist.png)

![Config](https://github.com/jnxxx/homeassistant-dabblerdk_powermeterreader/raw/main/images/meterdevice.png)

![Config](https://github.com/jnxxx/homeassistant-dabblerdk_powermeterreader/raw/main/images/metermep.png)

Readings

![Config](https://github.com/jnxxx/homeassistant-dabblerdk_powermeterreader/raw/main/images/graphconsumption.png)

![Config](https://github.com/jnxxx/homeassistant-dabblerdk_powermeterreader/raw/main/images/graphpower.png)

Energy dashboard
![Config](https://github.com/jnxxx/homeassistant-dabblerdk_powermeterreader/raw/main/images/energyday.png)

![Config](https://github.com/jnxxx/homeassistant-dabblerdk_powermeterreader/raw/main/images/energyweek.png)

