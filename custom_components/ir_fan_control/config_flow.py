from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_CONTROL_MODE,
    CONF_DIRECTION_IDLE,
    CONF_HAS_DIRECTION,
    CONF_HAS_OSC,
    CONF_HAS_TURBO,
    CONF_IDLE_LABEL,
    CONF_LEFT_LABEL,
    CONF_LOUVER_LEFT,
    CONF_LOUVER_RIGHT,
    CONF_OSC_DOWN,
    CONF_OSC_UP,
    CONF_POWER_CODE,
    CONF_PULSE_DELAY,
    CONF_RIGHT_LABEL,
    CONF_OSC_MODE,
    CONF_SPEED_DOWN_CODE,
    CONF_SPEED_UP_CODE,
    CONF_STEP_COUNT,
    CONF_TOPIC,
    CONF_TURBO_CODE,
    DEFAULT_IDLE_LABEL,
    DEFAULT_LEFT_LABEL,
    DEFAULT_CONTROL_MODE,
    DEFAULT_DIRECTION_IDLE,
    DEFAULT_NAME,
    DEFAULT_OSC_MODE,
    DEFAULT_PULSE_DELAY,
    DEFAULT_RIGHT_LABEL,
    DEFAULT_STEP_COUNT,
DOMAIN,
)

CONF_SETUP_MODE = "setup_mode"
SETUP_MODE_NEW = "Create new entry (blank)"


def _build_schema(defaults=None) -> vol.Schema:
    if defaults is None:
        defaults = {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): cv.string,
            vol.Required(CONF_TOPIC, default=defaults.get(CONF_TOPIC, "")): cv.string,
            vol.Required(
                CONF_POWER_CODE, default=defaults.get(CONF_POWER_CODE, "")
            ): cv.string,
            vol.Required(
                CONF_SPEED_UP_CODE, default=defaults.get(CONF_SPEED_UP_CODE, "")
            ): cv.string,
            vol.Required(
                CONF_SPEED_DOWN_CODE, default=defaults.get(CONF_SPEED_DOWN_CODE, "")
            ): cv.string,
            vol.Optional(
                CONF_HAS_TURBO, default=defaults.get(CONF_HAS_TURBO, True)
            ): cv.boolean,
            vol.Optional(CONF_TURBO_CODE, default=defaults.get(CONF_TURBO_CODE, "")): cv.string,
            vol.Optional(
                CONF_STEP_COUNT, default=defaults.get(CONF_STEP_COUNT, DEFAULT_STEP_COUNT)
            ): vol.All(int, vol.Range(min=2, max=6)),
            vol.Optional(
                CONF_CONTROL_MODE, default=defaults.get(CONF_CONTROL_MODE, DEFAULT_CONTROL_MODE)
            ): vol.In({"slider": "slider", "buttons": "buttons"}),
            vol.Optional(
                CONF_PULSE_DELAY,
                default=defaults.get(CONF_PULSE_DELAY, DEFAULT_PULSE_DELAY),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=5.0)),
            vol.Optional(
                CONF_HAS_DIRECTION, default=defaults.get(CONF_HAS_DIRECTION, False)
            ): cv.boolean,
            vol.Optional(
                CONF_DIRECTION_IDLE,
                default=defaults.get(CONF_DIRECTION_IDLE, DEFAULT_DIRECTION_IDLE),
            ): cv.boolean,
            vol.Optional(CONF_LOUVER_LEFT, default=defaults.get(CONF_LOUVER_LEFT, "")): cv.string,
            vol.Optional(
                CONF_LOUVER_RIGHT, default=defaults.get(CONF_LOUVER_RIGHT, "")
            ): cv.string,
            vol.Optional(
                CONF_LEFT_LABEL, default=defaults.get(CONF_LEFT_LABEL, DEFAULT_LEFT_LABEL)
            ): cv.string,
            vol.Optional(
                CONF_RIGHT_LABEL, default=defaults.get(CONF_RIGHT_LABEL, DEFAULT_RIGHT_LABEL)
            ): cv.string,
            vol.Optional(
                CONF_IDLE_LABEL, default=defaults.get(CONF_IDLE_LABEL, DEFAULT_IDLE_LABEL)
            ): cv.string,
            vol.Optional(CONF_HAS_OSC, default=defaults.get(CONF_HAS_OSC, False)): cv.boolean,
            vol.Optional(
                CONF_OSC_MODE, default=defaults.get(CONF_OSC_MODE, DEFAULT_OSC_MODE)
            ): vol.In({"none": "none", "toggle": "toggle", "levels": "levels"}),
            vol.Optional(CONF_OSC_UP, default=defaults.get(CONF_OSC_UP, "")): cv.string,
            vol.Optional(CONF_OSC_DOWN, default=defaults.get(CONF_OSC_DOWN, "")): cv.string,
        }
    )


def _make_unique_id(data: dict) -> str:
    name = str(data.get(CONF_NAME, "")).strip().lower()
    topic = str(data.get(CONF_TOPIC, "")).strip().lower()
    return f"{name}|{topic}"


class IRFanControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._defaults: dict = {}
        self._copy_defaults_by_label: dict[str, dict] = {}

    def _build_setup_mode_schema(self) -> vol.Schema:
        self._copy_defaults_by_label = {}
        choices = [SETUP_MODE_NEW]
        for entry in self._async_current_entries():
            defaults = {**entry.data, **entry.options}
            base_name = str(defaults.get(CONF_NAME, DEFAULT_NAME)).strip()
            if base_name:
                defaults[CONF_NAME] = f"{base_name} Copy"
            label = f"Duplicate: {entry.title}"
            self._copy_defaults_by_label[label] = defaults
            choices.append(label)

        return vol.Schema(
            {
                vol.Required(
                    CONF_SETUP_MODE,
                    default=SETUP_MODE_NEW,
                ): vol.In(choices)
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return IRFanControlOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        # If no existing entries, go straight to the full config form.
        if not self._async_current_entries():
            return await self.async_step_configure()

        errors = {}
        if user_input is not None:
            selected = user_input.get(CONF_SETUP_MODE, SETUP_MODE_NEW)
            self._defaults = self._copy_defaults_by_label.get(selected, {})
            return await self.async_step_configure()

        return self.async_show_form(
            step_id="user", data_schema=self._build_setup_mode_schema(), errors=errors
        )

    async def async_step_configure(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(_make_unique_id(user_input))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="configure", data_schema=_build_schema(self._defaults), errors=errors
        )

    async def async_step_import(self, user_input=None):
        if user_input is None:
            return self.async_abort(reason="invalid_import")

        await self.async_set_unique_id(_make_unique_id(user_input))
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)


class IRFanControlOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__()
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self._entry.data, **self._entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_build_schema(defaults), errors=errors
        )
