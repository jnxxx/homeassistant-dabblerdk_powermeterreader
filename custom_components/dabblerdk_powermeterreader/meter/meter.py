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
            _LOGGER.warn(f"Zeroconf failed. {err}")
          #logging.getLogger('zeroconf').setLevel(logging.WARNING)

          headers = {
              "Accept": "application/json",
              "User-Agent": "HomeAssistent integration dabblerdk_powermeterreader",
          }

          req_url = f"{url.geturl()}/getDashDataWS"

          try:
            async with aiohttp.ClientSession() as session:
              async with session.get(req_url, headers = headers) as response:
                temp = await response.json()
#                temp = json.loads('')
                self._connected = True
                if temp is not None:
                  _LOGGER.debug(f"Got meter data: {json.dumps(temp)}")

                  # Debug: Log received data when L3 power is above 10000
                  if (temp["L3_Fwd_W"] > 10000):
                    _LOGGER.warn(f"L3_Fwd_W > 10000: {json.dumps(temp)}")

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


