"""Platform to locally control Tuya-based climate devices."""
import logging
import json
from functools import partial

import voluptuous as vol
from homeassistant.components.climate import (
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
    ClimateEntity,
)
from homeassistant.components.climate.const import (  # HVAC_MODE_COOL,; HVAC_MODE_FAN_ONLY,; SUPPORT_TARGET_HUMIDITY,; SUPPORT_PRESET_MODE,; SUPPORT_SWING_MODE,; SUPPORT_AUX_HEAT,
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_HEAT,
    PRESET_ECO,
    PRESET_COMFORT,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_TEMPERATURE_UNIT,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_FAN_MODE_DP,
    CONF_HVAC_MODE_DP,
    CONF_MAX_TEMP_DP,
    CONF_MIN_TEMP_DP,
    CONF_TARGET_TEMPERATURE_DP,
    CONF_TEMPERATURE_STEP,
    CONF_PRESET_MODE_DP,
    CONF_HVAC_MODES,
    CONF_CURRENT_TEMPERATURE_MULTIPLIER,
    CONF_TARGET_TEMPERATURE_MULTIPLIER,
)

from . import pytuya

_LOGGER = logging.getLogger(__name__)

TEMPERATURE_CELSIUS = "celsius"
TEMPERATURE_FAHRENHEIT = "fahrenheit"
DEFAULT_TEMPERATURE_UNIT = TEMPERATURE_CELSIUS
DEFAULT_CURRENT_TEMPERATURE_MULTIPLIER = PRECISION_TENTHS
DEFAULT_TARGET_TEMPERATURE_MULTIPLIER = PRECISION_WHOLE
DEFAULT_TEMPERATURE_STEP = PRECISION_HALVES


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_TARGET_TEMPERATURE_DP): vol.In(dps),
        vol.Optional(CONF_TARGET_TEMPERATURE_MULTIPLIER): vol.In(
            [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]
        ),
        vol.Optional(CONF_CURRENT_TEMPERATURE_DP): vol.In(dps),
        vol.Optional(CONF_CURRENT_TEMPERATURE_MULTIPLIER): vol.In(
            [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]
        ),
        vol.Optional(CONF_TEMPERATURE_STEP): vol.In(
            [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]
        ),
        vol.Optional(CONF_HVAC_MODE_DP): vol.In(dps),
        vol.Optional(CONF_PRESET_MODE_DP): vol.In(dps),
        vol.Optional(CONF_FAN_MODE_DP): vol.In(dps),
        vol.Optional(CONF_MAX_TEMP_DP): vol.In(dps),
        vol.Optional(CONF_MIN_TEMP_DP): vol.In(dps),
        vol.Optional(CONF_TEMPERATURE_UNIT): vol.In(
            [TEMPERATURE_CELSIUS, TEMPERATURE_FAHRENHEIT]
        ),
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
        self._hvac_mode = None
        self._preset_mode = None
        self._hvac_action = None
        self._precision = self._config.get(
            CONF_CURRENT_TEMPERATURE_MULTIPLIER, DEFAULT_CURRENT_TEMPERATURE_MULTIPLIER)
        self._target_temperature_precision = self._config.get(
            CONF_TARGET_TEMPERATURE_MULTIPLIER, DEFAULT_TARGET_TEMPERATURE_MULTIPLIER)
        print("Initialized climate [{}]".format(self.name))

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = 0
        if self.has_config(CONF_TARGET_TEMPERATURE_DP):
            supported_features = supported_features | SUPPORT_TARGET_TEMPERATURE
        if self.has_config(CONF_MAX_TEMP_DP):
            supported_features = supported_features | SUPPORT_TARGET_TEMPERATURE_RANGE
        if self.has_config(CONF_FAN_MODE_DP):
            supported_features = supported_features | SUPPORT_FAN_MODE
        if list(presets):
            supported_features = supported_features | SUPPORT_PRESET_MODE
        return supported_features

    @property
    def precision(self):
        """Return the precision of the system."""
        return self._precision

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        if (
            self._config.get(CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT)
            == TEMPERATURE_FAHRENHEIT
        ):
            return TEMP_FAHRENHEIT
        return TEMP_CELSIUS

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return (list(modes))

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported.
        Need to be one of CURRENT_HVAC_*.
        """
        if self._hvac_mode == HVAC_MODE_HEAT:
            if self._current_temperature < (self._target_temperature - self._precision):
                self._hvac_action = CURRENT_HVAC_HEAT
            if self._current_temperature == (self._target_temperature - self._precision):
                if self._hvac_action == CURRENT_HVAC_HEAT:
                    self._hvac_action = CURRENT_HVAC_HEAT
                if self._hvac_action == CURRENT_HVAC_OFF:
                    self._hvac_action = CURRENT_HVAC_OFF
            if (self._current_temperature + self._precision) > self._target_temperature:
                self._hvac_action = CURRENT_HVAC_OFF
        return self._hvac_action

    @property
    def preset_mode(self):
        """Return current preset"""
        return self._preset_mode

    @property
    def preset_modes(self):
        """Return the list of available presets modes."""
        # return ["Eco", "Off"]
        return (list(presets))

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
        return self._config.get(CONF_TEMPERATURE_STEP, DEFAULT_TEMPERATURE_STEP)

    @property
    def fan_mode(self):
        """Return the fan setting."""
        return NotImplementedError()

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return NotImplementedError()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs and self.has_config(CONF_TARGET_TEMPERATURE_DP):
            temperature = round(kwargs[ATTR_TEMPERATURE] / self._target_temperature_precision)
            await self._device.set_dp(temperature, self._config[CONF_TARGET_TEMPERATURE_DP])

    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        return NotImplementedError()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target operation mode."""
        for hvac_mode_key in modes[hvac_mode].keys():
            hvac_mode_value = modes[hvac_mode].get(hvac_mode_key)
            await self._device.set_dp(hvac_mode_value, hvac_mode_key)

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        for preset_key in presets[preset_mode].keys():
            preset_value = presets[preset_mode].get(preset_key)
            await self._device.set_dp(preset_value, preset_key)

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        if self.has_config(CONF_MIN_TEMP_DP):
            return self.dps_conf(CONF_MIN_TEMP_DP)
        return DEFAULT_MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        if self.has_config(CONF_MAX_TEMP_DP):
            return self.dps_conf(CONF_MAX_TEMP_DP)
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

        alldps = {1: self.dps(1), 4: self.dps(4), 5: self.dps(5)}

        for mode in modes:
            if alldps.items() & modes[mode].items() == modes[mode].items():
                self._hvac_mode = mode

        for preset in presets:
            if alldps.items() & presets[preset].items() == presets[preset].items():
                self._preset_mode = preset


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaClimate, flow_schema)

modes = {
    HVAC_MODE_OFF: {
        1: False
    },
    HVAC_MODE_HEAT: {
        1: True,
        4: "1"
    },
    HVAC_MODE_AUTO: {
        1: True,
        4: "0"
    }
}

# presets={
#     PRESET_ECO: {
#         5: True
#     },
#     PRESET_COMFORT: {
#         5: False
#     }
# }

presets = {
    "Eco On": {
        5: True
    },
    "Eco Off": {
        5: False
    }
}
