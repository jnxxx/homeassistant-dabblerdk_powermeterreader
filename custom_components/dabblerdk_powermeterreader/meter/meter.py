"""Wrapper for connectedcars.io."""

from datetime import datetime
from datetime import timedelta
import json
import aiohttp
import asyncio
import logging
import hashlib

# Test
import random

_LOGGER = logging.getLogger(__name__)

class MeterReader:
    '''
    Primary exported interface for connectedcars.io API wrapper.
    '''
    def __init__(self, email, password, namespace, target_url):
        self._email = email
        self._password = password
        self._namespace = namespace
        self._base_url_auth = 'https://auth-api.connectedcars.io/'
        self._base_url = target_url.strip("/")
        # self._accesstoken = None
        # self._at_expires = None
        self._data = None
        self._data_expires = None
        self._lockUpdate = asyncio.Lock()
#        self._fail_count = 0
        self._succeed_timestamp = datetime.utcnow()
        self._connected = False
        self._sticking_with_prev_value = False

#        self._debugcount = 0
        _LOGGER.debug("Meter init")



    # async def _get_next_service_data_predicted(self, id):
    #   """Calculate number of days until next service. Prodicted."""
    #   ret = None
    #   date_str = await self._get_value(id, ["service", "predictedDate"])

    #   if date_str is not None:
    #     ret = datetime.strptime(date_str, "%Y-%m-%d").date()
    #     #ret = (date - datetime.now().date()).days
    #     #if ret < 0:
    #     #  ret = 0
    #   return(ret)

    # async def _get_value_float(self, id, selector):
    #   ret = None
    #   data = await self._get_value(id, selector)
    #   if type(data) == str:
    #     ret = float(data)
    #   if type(data) == float or type(data) == int:
    #     ret = data
    #   return(ret)

    # async def _get_value(self, id, selector):
    #   """Find vehicle."""
    #   ret = None
    #   data = await self._get_vehicle_data()
    #   vehicles = []
    #   for item in data['data']['viewer']['vehicles']:
    #       vehicle = item['vehicle']
    #       if vehicle['id'] == id:
    #         ret = self._get_vehicle_value(vehicle, selector)
    #   return(ret)

    async def _get_value(self, selector):
      """Get selected attribures in vehicle data."""
      ret = None
      obj = await self._get_meter_data()
      for sel in selector:
        if (obj is not None) and (sel in obj or (isinstance(obj, list) and sel < len(obj))):
          #print(obj)
          #print(sel)
          obj = obj[sel]
        else:
          # Object does not have specified selector(s)
          obj = None
          break
      ret = obj
      return(ret)


    # async def _get_lampstatus(self, id, type):
    #   """Get status of warning lamps."""
    #   ret = None
    #   data = await self._get_vehicle_data()
    #   vehicles = []
    #   for item in data['data']['viewer']['vehicles']:
    #       vehicle = item['vehicle']
    #       if vehicle['id'] == id:
    #         obj = vehicle
    #         for lamp in obj['lampStates']:
    #           #print(lamp)
    #           if (lamp['type'] == type):
    #             ret = lamp['enabled']
    #             break
    #   return(ret)

    # async def _get_voltage(self, id):
    #   ret = None
    #   data = await self._get_vehicle_data()
    #   for item in data['data']['viewer']['vehicles']:
    #       vehicle = item['vehicle']
    #       if vehicle['id'] == id:
    #         ret = vehicle['latestBatteryVoltage']['voltage']
    #   return(ret)

    # async def _get_vehicle_instances(self):
    #   """Get vehicle instances and sensor data available."""
    #   data = await self._get_vehicle_data()
    #   vehicles = []
    #   for item in data['data']['viewer']['vehicles']:
    #       vehicle = item['vehicle']
    #       id = vehicle['id']

    #       # Find lamps for this vehicle
    #       lampstates = []
    #       for lamp in vehicle['lampStates']:
    #         lampstates.append(lamp['type'])

    #       # Find data availability for sensors
    #       has = []
    #       if self._get_vehicle_value(vehicle, ["outdoorTemperatures", 0, "celsius"]) is not None:
    #         has.append("outdoorTemperature")
    #       if self._get_vehicle_value(vehicle, ["latestBatteryVoltage", "voltage"]) is not None:
    #         has.append("BatteryVoltage")
    #       if self._get_vehicle_value(vehicle, ["fuelPercentage", "percent"]) is not None:
    #         has.append("fuelPercentage")
    #       if self._get_vehicle_value(vehicle, ["fuelLevel", "liter"]) is not None:
    #         has.append("fuelLevel")
    #       if self._get_vehicle_value(vehicle, ["odometer", "odometer"]) is not None:
    #         has.append("odometer")
    #       if await self._get_next_service_data_predicted(id) is not None:
    #         has.append("NextServicePredicted")
    #       if self._get_vehicle_value(vehicle, ["chargePercentage", "percent"]) is not None:
    #         has.append("EVchargePercentage")
    #       if self._get_vehicle_value(vehicle, ["highVoltageBatteryTemperature", "celsius"]) is not None:
    #         has.append("EVHVBattTemp")

    #       if self._get_vehicle_value(vehicle, ["ignition", "on"]) is not None:
    #         has.append("Ignition")
    #       if self._get_vehicle_value(vehicle, ["health", "ok"]) is not None:
    #         has.append("Health")
          
    #       if self._get_vehicle_value(vehicle, ["position", "latitude"]) is not None and self._get_vehicle_value(vehicle, ["position", "longitude"]) is not None:
    #         has.append("GeoLocation")
    #       if self._get_vehicle_value(vehicle, ["position", "speed"]) is not None:
    #         has.append("Speed")

    #       # Add vehicle to array
    #       vehicles.append( { "id": id, "vin": vehicle['vin'], "name": vehicle['name'], "make": vehicle['make'], "model": vehicle['model'], "licensePlate": vehicle['licensePlate'], "lampStates": lampstates, "has": has } )

    #   return(vehicles)

    async def _is_connected(self):
      ret = None
      async with self._lockUpdate:
        ret = self._connected
      return(ret)

    async def _is_stuck_with_prev_value(self):
      ret = None
      async with self._lockUpdate:
        ret = self._sticking_with_prev_value
      return(ret)


    async def _get_meter_data(self):
      """Read data from API."""

#      self._debugcount = self._debugcount + 1
#      dbgcnt = self._debugcount

      async with self._lockUpdate:
        if self._data_expires == None or self._data == None or datetime.utcnow() > self._data_expires:
          self._data_expires = None
          #self._data = None
          self._connected = False

#          _LOGGER.debug(f"_get_meter_data: {dbgcnt}, time: {self._data_expires}")

          headers = {
              "Accept": "application/json",
              "User-Agent": "HomeAssistent integration dabblerdk_powermeterreader",
          }

          req_url = f"{self._base_url}/getDashDataWS"

          try:
            async with aiohttp.ClientSession() as session:
              async with session.get(req_url, headers = headers) as response:
                temp = await response.json()
#                temp = json.loads('')
                self._connected = True
                if temp is not None:
                  _LOGGER.debug(f"Got meter data: {json.dumps(temp)}")
                  
                  # Fwd_Act_Wh has been seen to jump temporarily, which messes up the delta when using state_class=total_increasing
                  # Ignore negative or more than 1000 wh increase for an hour or until restarted.
                  self._sticking_with_prev_value = False
                  if self._data is not None:
                    energy_prev = self._data["Fwd_Act_Wh"]
                    energy_now = temp["Fwd_Act_Wh"]

                    if energy_now is None:
                      _LOGGER.warn(f"Fwd_Act_Wh is None, sticking to previous values")
                      self._sticking_with_prev_value = True
                    else:
                      diff = energy_now - energy_prev
                      if energy_prev is None or (diff >= 0 and diff <= 1000) or (datetime.utcnow()-self._succeed_timestamp).seconds >= 3600:
                        self._data = temp
                        self._succeed_timestamp = datetime.utcnow()
                      else:
                        _LOGGER.warn(f"Fwd_Act_Wh changed too much ({diff}), sticking to previous values")
                        self._sticking_with_prev_value = True

                  else:
                    self._data = temp
                    self._succeed_timestamp = datetime.utcnow()
                  self._data_expires = datetime.utcnow()+timedelta(seconds=2)
                else:
                  raise Exception("empty_response")

          except aiohttp.ClientError as client_error:
              _LOGGER.warn(f"Requesting meter values failed: {client_error}")
              raise Exception(f"Requesting meter values failed: {client_error}")

#        _LOGGER.debug(f"_get_meter_data end: {dbgcnt}, time: {self._data_expires}")

      return(self._data)


    # async def _get_access_token(self):
    #     """Authenticate to get access token."""

    #     if self._accesstoken == None or self._at_expires == None or datetime.utcnow() > self._at_expires:
    #         headers = {
    #             "Content-Type": "application/json",
    #             "Accept": "application/json",
    #             "x-organization-namespace": f"semler:{self._namespace}",
    #             "User-Agent": "ConnectedCars/360 CFNetwork/978.0.7 Darwin/18.7.0"
    #         }
    #         body = {
    #             "email": self._email,
    #             "password": self._password
    #         }

    #         # Authenticate
    #         try:
    #             self._accesstoken = None
    #             self._at_expires = None
    #             result_json = None

    #             _LOGGER.debug(f"Getting access token...")

    #             auth_url = self._base_url_auth + "auth/login/email/password"

    #             async with aiohttp.ClientSession() as session:
    #               async with session.post(auth_url, json = body, headers = headers) as response:
    #                 result_json = await response.json()

    #             #result = await requests.post(auth_url, json = body, headers = headers)
    #             #result_json = result.json()
    #             #print(result_json)

    #             if result_json is not None and 'token' in result_json and 'expires' in result_json:
    #                 self._accesstoken = result_json['token']
    #                 self._at_expires = datetime.utcnow()+timedelta(seconds=int(result_json['expires'])-120)
    #                 _LOGGER.debug(f"Got access token: {self._accesstoken[:20]}...")
    #             if result_json is not None and 'error' in result_json and 'message' in result_json:
    #                 raise Exception(result_json['message'])

    #         except aiohttp.ClientError as client_error:
    #             _LOGGER.warn(f"Authentication failed. {client_error}")
    #         # except requests.exceptions.Timeout:
    #         #     _LOGGER.warn("Authentication failed. Timeout")
    #         # except requests.exceptions.HTTPError as e:
    #         #     _LOGGER.warn(f"Authentication failed. HTTP error: {e}.")
    #         # except requests.exceptions.RequestException as e:
    #         #     _LOGGER.warn(f"Authentication failed: {e}.")

    #     #print(self._at_expires)
        
    #     return self._accesstoken

