"""Platform to locally control Tuya-based climate devices."""
import logging
import json
from functools import partial

import voluptuous as vol
from homeassistant.components.climate import (
    DOMAIN,
    ClimateEntity,
)
from homeassistant.components.climate.const import (  # HVAC_MODE_COOL,; HVAC_MODE_FAN_ONLY,; SUPPORT_TARGET_HUMIDITY,; SUPPORT_PRESET_MODE,; SUPPORT_SWING_MODE,; SUPPORT_AUX_HEAT,
    HVAC_MODE_HEAT,
    SUPPORT_TARGET_TEMPERATURE
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_TEMPERATURE_UNIT,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    TEMP_CELSIUS
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_TARGET_TEMPERATURE_DP,
)

from . import pytuya

_LOGGER = logging.getLogger(__name__)

DEFAULT_MAX_TEMP = 30
DEFAULT_MIN_TEMP = 5

def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_TARGET_TEMPERATURE_DP): vol.In(dps),
        vol.Optional(CONF_CURRENT_TEMPERATURE_DP): vol.In(dps)
    }

class LocaltuyaClimate(LocalTuyaEntity, ClimateEntity):
    """Tuya climate device."""

    def __init__(
        self,
        device,
        config_entry,
        switchid,
        **kwargs,
    ):
        """Initialize a new LocaltuyaClimate."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._state = None
        self._target_temperature = None
        self._current_temperature = None
        self._hvac_mode = HVAC_MODE_HEAT
        self._precision = PRECISION_TENTHS
        self._target_temperature_precision = PRECISION_WHOLE
        print("Initialized climate [{}]".format(self.name))

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def precision(self):
        """Return the precision of the system."""
        return self._precision

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return [HVAC_MODE_HEAT]

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return PRECISION_WHOLE

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs:
            temperature = round(kwargs[ATTR_TEMPERATURE] / self._target_temperature_precision)
            await self._device.set_dp(temperature, self._config[CONF_TARGET_TEMPERATURE_DP])

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target operation mode."""
        return NotImplementedError()

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return DEFAULT_MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return DEFAULT_MAX_TEMP

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dp_id)

        if self.has_config(CONF_TARGET_TEMPERATURE_DP):
            self._target_temperature = (
                self.dps_conf(CONF_TARGET_TEMPERATURE_DP)
                * self._target_temperature_precision
            )

        if self.has_config(CONF_CURRENT_TEMPERATURE_DP):
            self._current_temperature = (
                self.dps_conf(CONF_CURRENT_TEMPERATURE_DP) * self._precision
            )
        
async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaClimate, flow_schema)
