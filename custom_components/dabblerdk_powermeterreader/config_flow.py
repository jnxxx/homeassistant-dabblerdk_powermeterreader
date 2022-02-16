"""Support for dabblerdk_powermeterreader."""

import logging
from typing import Any, Dict, Optional

#from gidgethub import BadRequest
#from gidgethub.aiohttp import GitHubAPI
from homeassistant import config_entries, core
from homeassistant.const import CONF_EMAIL, CONF_NAME, CONF_URL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import re

from .const import DOMAIN
from .meter import MeterReader

_LOGGER = logging.getLogger(__name__)

CONN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="Echelon"): cv.string,
        vol.Required(CONF_URL, default="http://module_ip"): cv.string,
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Github Custom config flow."""

    data: Optional[Dict[str, Any]]

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_NAME] == "":
                errors[CONF_NAME] = "empty_name"
            
            # Check url
            await fnCheckUrl(user_input[CONF_URL], errors)

            # try:
            #     client = MeterReader("", "", "", user_input[CONF_URL])
            #     token = await client._get_meter_data()
            # except Exception as err:
            #     _LOGGER.debug(err)
            #     if str(err) == "empty_response":
            #         errors[CONF_URL] = "empty_response"
            #     else:
            #         errors["base"] = err

            if not errors:
                # Input is valid, set data.
                self.data = user_input

                # User is done, create the config entry.
                return self.async_create_entry(title=user_input[CONF_NAME], data=self.data)

        return self.async_show_form(
            step_id="user", data_schema=CONN_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)




class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
        errors: Dict[str, str] = {}

        """Manage the options."""
        if user_input is not None:

            # Check url
            await fnCheckUrl(user_input[CONF_URL], errors)

            # Check scan_interval
            try:
                val = int(user_input[CONF_SCAN_INTERVAL])
                if (val < 5 or val > 3600):
                    errors[CONF_SCAN_INTERVAL] = "scan_interval_outofbounds"
            except:
                errors[CONF_SCAN_INTERVAL] = "scan_interval_integer"

            if not errors:
                data = dict(self.config_entry.data)
                data[CONF_URL] = user_input[CONF_URL]

                options = {}
                options[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]

                self.hass.config_entries.async_update_entry(self.config_entry, data=data, options=options)
                return self.async_create_entry(title="", data=options)

        options_schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=self.config_entry.data[CONF_URL]): cv.string,
                vol.Required(CONF_SCAN_INTERVAL, default=self.config_entry.options.get(CONF_SCAN_INTERVAL, 300)): cv.positive_int
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )


async def fnCheckUrl(url, errors: Dict[str, str]):
    if re.search("^http(s){0,1}:\/\/[a-zA-Z0-9_\-\.]+(:\d+){0,1}\/{0,1}$", url) is None:
        errors[CONF_URL] = "invalid_url"
    else:
        try:
            client = MeterReader(url)
            data = await client._get_meter_data()

            try:
                for param in ["Fwd_Act_Wh", "Rev_Act_Wh", "L1_RMS_A", "L2_RMS_A", "L3_RMS_A", "L1_RMS_V", "L2_RMS_V", "L3_RMS_V", "Fwd_W", "Rev_W", "L1_Fwd_W", "L2_Fwd_W", "L3_Fwd_W", "L1_Rev_W", "L2_Rev_W", "L3_Rev_W"]:
                    num = int(data[param])
            except:
                errors[CONF_URL] = "unexpected_response"

        except Exception as err:
            #_LOGGER.debug(err)
            print(err)
            if str(err) == "empty_response":
                errors[CONF_URL] = "empty_response"
            #elif str(err).startswith("Requesting meter values failed:"):
            else:
                errors[CONF_URL] = "request_failed"


