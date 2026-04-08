from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

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
    CONF_NAME,
    CONF_RIGHT_LABEL,
    CONF_OSC_DOWN,
    CONF_OSC_UP,
    CONF_POWER_CODE,
    CONF_PULSE_DELAY,
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
    DEFAULT_OSC_MODE,
    DEFAULT_PULSE_DELAY,
    DEFAULT_RIGHT_LABEL,
    DEFAULT_STEP_COUNT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.FAN]


def _normalize_import_data(raw: Mapping[str, Any]) -> dict[str, Any] | None:
    """Normalize YAML/import data into config-entry shape."""
    name = raw.get(CONF_NAME)
    topic = raw.get(CONF_TOPIC)
    power_code = raw.get(CONF_POWER_CODE)
    speed_up = raw.get(CONF_SPEED_UP_CODE)
    speed_down = raw.get(CONF_SPEED_DOWN_CODE)

    if not all([name, topic, power_code, speed_up, speed_down]):
        return None

    return {
        CONF_NAME: str(name),
        CONF_TOPIC: str(topic),
        CONF_POWER_CODE: str(power_code),
        CONF_SPEED_UP_CODE: str(speed_up),
        CONF_SPEED_DOWN_CODE: str(speed_down),
        CONF_HAS_TURBO: bool(raw.get(CONF_HAS_TURBO, False)),
        CONF_TURBO_CODE: str(raw.get(CONF_TURBO_CODE, "")),
        CONF_STEP_COUNT: int(raw.get(CONF_STEP_COUNT, DEFAULT_STEP_COUNT)),
        CONF_CONTROL_MODE: str(raw.get(CONF_CONTROL_MODE, DEFAULT_CONTROL_MODE)),
        CONF_PULSE_DELAY: float(raw.get(CONF_PULSE_DELAY, DEFAULT_PULSE_DELAY)),
        CONF_HAS_DIRECTION: bool(raw.get(CONF_HAS_DIRECTION, False)),
        CONF_DIRECTION_IDLE: bool(raw.get(CONF_DIRECTION_IDLE, DEFAULT_DIRECTION_IDLE)),
        CONF_LOUVER_LEFT: str(raw.get(CONF_LOUVER_LEFT, "")),
        CONF_LOUVER_RIGHT: str(raw.get(CONF_LOUVER_RIGHT, "")),
        CONF_LEFT_LABEL: str(raw.get(CONF_LEFT_LABEL, DEFAULT_LEFT_LABEL)),
        CONF_RIGHT_LABEL: str(raw.get(CONF_RIGHT_LABEL, DEFAULT_RIGHT_LABEL)),
        CONF_IDLE_LABEL: str(raw.get(CONF_IDLE_LABEL, DEFAULT_IDLE_LABEL)),
        CONF_HAS_OSC: bool(raw.get(CONF_HAS_OSC, False)),
        CONF_OSC_MODE: str(raw.get(CONF_OSC_MODE, DEFAULT_OSC_MODE)),
        CONF_OSC_UP: str(raw.get(CONF_OSC_UP, "")),
        CONF_OSC_DOWN: str(raw.get(CONF_OSC_DOWN, "")),
    }


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    # Optional YAML import path. If users define `ir_fan_control:` in
    # configuration.yaml, create config entries from those blocks.
    configured = config.get(DOMAIN, [])
    if isinstance(configured, Mapping):
        configured = [configured]

    for raw in configured:
        if not isinstance(raw, Mapping):
            continue

        payload = _normalize_import_data(raw)
        if payload is None:
            continue

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=payload,
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {**entry.data, **entry.options}
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    try:
        # Backwards-compatible platform forwarding across HA core versions.
        if hasattr(hass.config_entries, "async_forward_entry_setups"):
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        else:
            await hass.config_entries.async_forward_entry_setup(entry, Platform.FAN)
    except Exception as err:  # pragma: no cover - debug visibility
        _LOGGER.exception("ir_fan_control setup failed for %s", entry.entry_id)
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if hasattr(hass.config_entries, "async_unload_platforms"):
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    else:
        unload_ok = await hass.config_entries.async_forward_entry_unload(entry, Platform.FAN)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    hass.data[DOMAIN][entry.entry_id] = {**entry.data, **entry.options}
    await hass.config_entries.async_reload(entry.entry_id)
