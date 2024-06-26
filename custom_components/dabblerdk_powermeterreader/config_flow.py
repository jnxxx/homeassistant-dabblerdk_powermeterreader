"""Support for dabblerdk_powermeterreader."""

import logging
import re
from typing import Any, Optional  # , Dict

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL, CONF_URL
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .meter import MeterReader

_LOGGER = logging.getLogger(__name__)

CONN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="Echelon"): cv.string,
        vol.Required(CONF_URL, default="http://esp32-mep.local/"): cv.string,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """dabblerdk_powermeterreader config flow."""

    data: Optional[dict[str, Any]]

    async def async_step_user(self, user_input: Optional[dict[str, Any]] = None):
        """User initiates a flow via the user interface."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_NAME] == "":
                errors[CONF_NAME] = "empty_name"

            # Check url
            await fnCheckUrl(user_input[CONF_URL], self.hass, errors)

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
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=self.data
                )

        return self.async_show_form(
            step_id="user", data_schema=CONN_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Initiate options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """dabblerdk_powermeterreader options flow."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check url
            await fnCheckUrl(user_input[CONF_URL], self.hass, errors)

            # Check scan_interval
            try:
                val = int(user_input[CONF_SCAN_INTERVAL])
                if val < 5 or val > 3600:
                    errors[CONF_SCAN_INTERVAL] = "scan_interval_outofbounds"
            except Exception:  # pylint: disable=broad-except
                errors[CONF_SCAN_INTERVAL] = "scan_interval_integer"

            if not errors:
                data = dict(self.config_entry.data)
                data[CONF_URL] = user_input[CONF_URL]

                options = {}
                options[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]

                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=data, options=options
                )
                return self.async_create_entry(title="", data=options)

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_URL, default=self.config_entry.data[CONF_URL]
                ): cv.string,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(CONF_SCAN_INTERVAL, 300),
                ): cv.positive_int,
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )


async def fnCheckUrl(url, hass: HomeAssistant, errors: dict[str, str]):
    """Check if url is working."""
    if (
        re.search(r"^http(s){0,1}:\/\/[a-zA-Z0-9_\-\.]+(:\d+){0,1}\/{0,1}$", url)
        is None
    ):
        errors[CONF_URL] = "invalid_url"
    else:
        try:
            client = MeterReader(url, hass)
            data = await client.get_meter_data()

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
                errors[CONF_URL] = "unexpected_response"

        except Exception as err:  # pylint: disable=broad-except
            # _LOGGER.debug(err)
            # print(err)
            if str(err) == "empty_response":
                errors[CONF_URL] = "empty_response"
            # elif str(err).startswith("Requesting meter values failed:"):
            else:
                errors[CONF_URL] = "request_failed"
