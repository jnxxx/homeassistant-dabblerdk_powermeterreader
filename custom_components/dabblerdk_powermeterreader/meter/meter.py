"""Wrapper for dabbler.dk MEP module."""

from datetime import datetime
from datetime import timedelta
import json
import aiohttp
import asyncio
import logging
import hashlib
from homeassistant.components import zeroconf
from zeroconf.asyncio import AsyncServiceInfo
from urllib.parse import urlparse

# Test
import random

_LOGGER = logging.getLogger(__name__)

class MeterReader:
    '''
    Primary exported interface for dabbler.dk MEP module wrapper.
    '''
    def __init__(self, target_url, hass):
        self._base_url = target_url.strip("/")
        self._data = None
        self._data_expires = None
        self._lockUpdate = asyncio.Lock()
#        self._fail_count = 0
        self._succeed_timestamp = datetime.utcnow()
        self._connected = False
        self._sticking_with_prev_value = False
        self._hass = hass

#        self._debugcount = 0
        _LOGGER.debug("Meter init")


    async def _get_metersn(self):
      meter_sn = None
      if self._data is not None:
        meter_sn = self._data["Utility_SN"]
      else:
        meter_sn = await self._get_value(["Utility_SN"])
      return(meter_sn)

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

          url = urlparse(self._base_url)
          try:
            aryhost = url.netloc.split(':')
            host = aryhost[0]

            # Resolve local names using mdns
            if (host.rstrip('.').endswith(".local")):
              _LOGGER.debug(f"Resolving name: {host}")
              #logging.getLogger('zeroconf').setLevel(logging.DEBUG)
              aiozc = await zeroconf.async_get_async_instance(self._hass)

              info = AsyncServiceInfo("local.", f"{host.rstrip('.')}.")
              bFound = await info.async_request(aiozc.zeroconf, 3000)

              if info and bFound:
                  for addr in info.parsed_addresses():
                    host = addr if (len(aryhost) == 1) else f"{addr}:{aryhost[1]}"
                    url = url._replace(netloc=host)
                    _LOGGER.debug(f"  Url: {url.geturl()}")
                    break
          except BaseException as err:
            _LOGGER.warning(f"Zeroconf failed. {err}")
          #logging.getLogger('zeroconf').setLevel(logging.WARNING)

          headers = {
              "Accept": "application/json",
              "User-Agent": "HomeAssistent integration dabblerdk_powermeterreader",
          }

          req_url = f"{url.geturl()}/getDashDataWS"

          temp = None
          try:
            async with aiohttp.ClientSession() as session:
              async with session.get(req_url, headers = headers) as response:
                temp = await response.json()

              # temp = json.loads('')
              self._connected = True
              if temp is not None:
                _LOGGER.debug(f"Got meter data: {json.dumps(temp)}")

                # Fwd_Act_Wh has been seen to jump temporarily, which messes up the delta when using state_class=total_increasing
                # Ignore negative or more than 1000 wh increase for an hour or until restarted.
                stuck_with_prev_value = self._sticking_with_prev_value
                self._sticking_with_prev_value = False
                if self._data is not None:
                  energy_prev = self._data["Fwd_Act_Wh"]
                  energy_now = temp["Fwd_Act_Wh"]

                  if not isinstance(energy_now, int):   # energy_now is None
                    _LOGGER.warning(f"Fwd_Act_Wh is None, sticking to previous values")
                    self._sticking_with_prev_value = True
                  else:
                    diff = energy_now - energy_prev
                    # _LOGGER.warning(f"(isinstance(energy_prev, int)): { (isinstance(energy_prev, int)) }")
                    # _LOGGER.warning(f"(diff >= 0 and diff <= 1000): { (diff >= 0 and diff <= 1000) }")
                    # _LOGGER.warning(f"((datetime.utcnow()-self._succeed_timestamp).seconds < 3600): { ((datetime.utcnow()-self._succeed_timestamp).seconds < 3600) }")

                    elapsed_time = 60 if (self._succeed_timestamp is None) else (datetime.utcnow()-self._succeed_timestamp).total_seconds()
                    if (elapsed_time < 60):
                      elapsed_time = 60
                    wh_limit = 16*3*230/3600 * 3 * elapsed_time
                    _LOGGER.debug("wh_limit: %f", wh_limit)

                    if ((isinstance(energy_prev, int)) and (diff >= 0 and diff <= wh_limit)) or elapsed_time > 1800:
                      sum_power = temp["L1_Fwd_W"] + temp["L2_Fwd_W"] + temp["L3_Fwd_W"]
                      sum_power -= (temp["L1_Rev_W"] + temp["L2_Rev_W"] + temp["L3_Rev_W"])
                      total_power = temp["Fwd_W"] - temp["Rev_W"]
                      if (total_power <= sum_power+3 and total_power >= sum_power-3):
                        self._data = temp
                        self._succeed_timestamp = datetime.utcnow()
                        if stuck_with_prev_value:
                          _LOGGER.warning(f"Resume-read meter data: {json.dumps(temp)}")
                      else:
                        _LOGGER.warning(f"L1 [W] + L2 [W] + L3 [W] does not equal Total [W] ({sum_power} != {total_power}), sticking to previous values")
                        _LOGGER.warning(f"data: {json.dumps(temp)}")
                        self._sticking_with_prev_value = True
                    else:
                      _LOGGER.warning(f"Fwd_Act_Wh changed too much ({diff}), sticking to previous values. wh_limit: {wh_limit}")
                      self._sticking_with_prev_value = True

                else:
                  self._data = temp
                  self._succeed_timestamp = datetime.utcnow()
                  _LOGGER.warning(f"First meter data: {json.dumps(temp)}")
                self._data_expires = datetime.utcnow()+timedelta(seconds=2)
              else:
                raise Exception("empty_response")

          except aiohttp.ClientError as client_error:
              _LOGGER.warning(f"Requesting meter values failed: {client_error}")
              raise Exception(f"Requesting meter values failed: {client_error}")

#        _LOGGER.debug(f"_get_meter_data end: {dbgcnt}, time: {self._data_expires}")

      return(self._data)


