"""Wrapper for dabbler.dk MEP module."""

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
    Primary exported interface for dabbler.dk MEP module wrapper.
    '''
    def __init__(self, target_url):
        self._base_url = target_url.strip("/")
        self._data = None
        self._data_expires = None
        self._lockUpdate = asyncio.Lock()
#        self._fail_count = 0
        self._succeed_timestamp = datetime.utcnow()
        self._connected = False
        self._sticking_with_prev_value = False

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


