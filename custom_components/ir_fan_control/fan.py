from __future__ import annotations

import asyncio
from time import monotonic

from homeassistant.components import mqtt
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

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
    CONF_OSC_DOWN,
    CONF_OSC_MODE,
    CONF_OSC_UP,
    CONF_POWER_CODE,
    CONF_PULSE_DELAY,
    CONF_RIGHT_LABEL,
    CONF_SPEED_DOWN_CODE,
    CONF_SPEED_UP_CODE,
    CONF_STEP_COUNT,
    CONF_TOPIC,
    CONF_TURBO_CODE,
    DEFAULT_CONTROL_MODE,
    DEFAULT_DIRECTION_IDLE,
    DEFAULT_IDLE_LABEL,
    DEFAULT_LEFT_LABEL,
    DEFAULT_OSC_MODE,
    DEFAULT_PULSE_DELAY,
    DEFAULT_RIGHT_LABEL,
    DEFAULT_STEP_COUNT,
    DOMAIN,
)

FEATURE_NONE = FanEntityFeature(0)
FEATURE_SET_PERCENTAGE = getattr(
    FanEntityFeature,
    "SET_PERCENTAGE",
    getattr(FanEntityFeature, "SET_SPEED", FEATURE_NONE),
)
FEATURE_PRESET_MODE = getattr(FanEntityFeature, "PRESET_MODE", FEATURE_NONE)
FEATURE_OSCILLATE = getattr(FanEntityFeature, "OSCILLATE", FEATURE_NONE)
FEATURE_TURN_ON = getattr(FanEntityFeature, "TURN_ON", FEATURE_NONE)
FEATURE_TURN_OFF = getattr(FanEntityFeature, "TURN_OFF", FEATURE_NONE)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([IRFanControl(hass, entry)], True)


class IRFanControl(FanEntity, RestoreEntity):
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry_id = entry.entry_id
        data = {**entry.data, **entry.options}
        self._attr_name = data.get(CONF_NAME)
        self._attr_unique_id = f"{entry.entry_id}_fan"
        name_lower = str(self._attr_name or "").lower()
        self._attr_icon = "mdi:radiator" if "heater" in name_lower else "mdi:fan"
        self._topic = data.get(CONF_TOPIC)
        self._step_count = int(data.get(CONF_STEP_COUNT, DEFAULT_STEP_COUNT))
        self._pulse_delay = float(data.get(CONF_PULSE_DELAY, DEFAULT_PULSE_DELAY))
        self._control_mode = str(data.get(CONF_CONTROL_MODE, DEFAULT_CONTROL_MODE))

        self._power = data.get(CONF_POWER_CODE)
        self._up = data.get(CONF_SPEED_UP_CODE)
        self._down = data.get(CONF_SPEED_DOWN_CODE)

        self._has_turbo = data.get(CONF_HAS_TURBO, False)
        self._turbo = data.get(CONF_TURBO_CODE) if self._has_turbo else None

        self._has_dir = data.get(CONF_HAS_DIRECTION, False)
        self._direction_idle = bool(
            data.get(CONF_DIRECTION_IDLE, DEFAULT_DIRECTION_IDLE)
        )
        self._left = data.get(CONF_LOUVER_LEFT)
        self._right = data.get(CONF_LOUVER_RIGHT)
        self._left_label = (
            str(data.get(CONF_LEFT_LABEL, DEFAULT_LEFT_LABEL)).strip()
            or DEFAULT_LEFT_LABEL
        )
        self._right_label = (
            str(data.get(CONF_RIGHT_LABEL, DEFAULT_RIGHT_LABEL)).strip()
            or DEFAULT_RIGHT_LABEL
        )
        self._idle_label = (
            str(data.get(CONF_IDLE_LABEL, DEFAULT_IDLE_LABEL)).strip()
            or DEFAULT_IDLE_LABEL
        )

        self._has_osc = data.get(CONF_HAS_OSC, False)
        self._osc_mode = str(data.get(CONF_OSC_MODE, DEFAULT_OSC_MODE))
        self._osc_up = data.get(CONF_OSC_UP)
        self._osc_down = data.get(CONF_OSC_DOWN)

        self._preset_actions: dict[str, str | None] = {}
        self._attr_supported_features = FEATURE_TURN_ON | FEATURE_TURN_OFF
        if self._control_mode != "buttons":
            self._attr_supported_features |= FEATURE_SET_PERCENTAGE

        self._attr_preset_mode = None
        self._attr_oscillating = False

        if self._has_dir and (self._left or self._right):
            if self._direction_idle:
                self._preset_actions[self._idle_label] = None
            if self._left:
                self._preset_actions[self._left_label] = self._left
            if self._right:
                self._preset_actions[self._right_label] = self._right

        if self._control_mode == "buttons" and self._up and self._down:
            self._preset_actions["decrease"] = self._down
            self._preset_actions["increase"] = self._up

        if self._control_mode == "buttons" and self._has_turbo and self._turbo:
            self._preset_actions["turbo"] = self._turbo

        if (
            self._has_osc
            and self._osc_up
            and self._osc_down
            and self._osc_mode == "toggle"
        ):
            self._attr_supported_features |= FEATURE_OSCILLATE
        elif (
            self._has_osc
            and self._osc_up
            and self._osc_down
            and self._osc_mode == "levels"
        ):
            self._preset_actions["osc_less"] = self._osc_down
            self._preset_actions["osc_more"] = self._osc_up

        if self._preset_actions:
            self._attr_supported_features |= FEATURE_PRESET_MODE
            self._attr_preset_modes = list(self._preset_actions.keys())

        self._attr_speed_count = max(1, self._step_count)
        self._attr_percentage = 0
        self._attr_percentage_step = max(1, int(round(100 / max(1, self._step_count))))
        self._current_step = 0
        self._attr_is_on = False
        self._suppress_turn_off_until = 0.0
        self._turbo_active = False
        self._pre_turbo_step = 1
        self._op_generation = 0

        # Stable pacing profile to avoid delayed/stale command bursts.
        self._pacing_profile = "stable-v1"
        self._tx_clear_delay = min(0.08, max(0.02, self._pulse_delay / 4))
        self._step_delay_slider = max(0.45, self._pulse_delay)
        self._step_delay_buttons = max(
            0.25, min(self._step_delay_slider, self._pulse_delay * 0.7)
        )
        self._mode_settle_delay = max(0.35, self._step_delay_buttons)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if not last_state:
            return

        self._attr_is_on = last_state.state == "on"
        restored_step = last_state.attributes.get("ir_current_step")
        restored_pct = last_state.attributes.get("percentage")
        restored_preset = last_state.attributes.get("preset_mode")
        restored_pre_turbo = last_state.attributes.get("ir_pre_turbo_step")

        if isinstance(restored_step, (int, float)):
            self._current_step = int(restored_step)
        if isinstance(restored_pct, (int, float)):
            self._attr_percentage = int(restored_pct)
        if isinstance(restored_preset, str):
            self._attr_preset_mode = restored_preset
        if isinstance(restored_pre_turbo, (int, float)):
            self._pre_turbo_step = int(restored_pre_turbo)

        if self._attr_is_on:
            if self._control_mode == "buttons":
                self._current_step = max(1, self._current_step or 1)
                if int(self._attr_percentage or 0) <= 0:
                    self._attr_percentage = self._step_to_pct(self._current_step)
            else:
                if self._has_turbo and self._current_step == self._step_count + 1:
                    self._attr_percentage = 100
                else:
                    if int(self._attr_percentage or 0) <= 0:
                        self._attr_percentage = 15
                    self._current_step = self._pct_to_step(self._attr_percentage)
        else:
            self._current_step = 0
            self._attr_percentage = 0

        self._pre_turbo_step = max(1, min(self._step_count, self._pre_turbo_step))
        self._turbo_active = bool(
            self._has_turbo
            and self._turbo
            and self._attr_is_on
            and self._current_step == self._step_count + 1
        )

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, int | bool | str]:
        return {
            "ir_current_step": int(self._current_step),
            "ir_turbo_active": bool(self._turbo_active),
            "ir_pre_turbo_step": int(self._pre_turbo_step),
            "ir_pacing_profile": self._pacing_profile,
        }

    async def async_update(self) -> None:
        return

    @property
    def percentage_step(self) -> int:
        return max(1, int(round(100 / max(1, self._step_count))))

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="Tipana",
            model="IR Fan Controller",
        )

    def _start_operation(self) -> int:
        self._op_generation += 1
        return self._op_generation

    def _is_stale(self, op_token: int | None) -> bool:
        return op_token is not None and op_token != self._op_generation

    async def _sleep_step(self, mode: str, op_token: int | None = None) -> bool:
        delay = (
            self._step_delay_buttons if mode == "buttons" else self._step_delay_slider
        )
        await asyncio.sleep(delay)
        return not self._is_stale(op_token)

    async def _send_ir(self, code: str) -> None:
        payload = f'{{"ir_code_to_send":"{code}"}}'
        await mqtt.async_publish(self._hass, self._topic, payload, qos=0, retain=False)
        await asyncio.sleep(self._tx_clear_delay)
        await mqtt.async_publish(
            self._hass,
            self._topic,
            '{"ir_code_to_send":null}',
            qos=0,
            retain=False,
        )

    def _pct_to_step(self, pct: int) -> int:
        if pct >= 100 and self._has_turbo and self._turbo:
            return self._step_count + 1
        step_pct = max(15, min(100, pct))
        step_width = 100 / self._step_count
        bucket = int((step_pct - 1) / step_width) + 1
        return max(1, min(self._step_count, bucket))

    def _step_to_pct(self, step: int) -> int:
        if step <= 0:
            return 0
        if self._has_turbo and self._turbo and step >= self._step_count + 1:
            return 100
        if self._step_count <= 1:
            return 100
        if step <= 1:
            return 15
        if step >= self._step_count:
            return 100
        return int(round(15 + ((step - 1) * 85) / (self._step_count - 1)))

    def _ensure_on_step(self) -> None:
        if self._attr_is_on and self._current_step <= 0:
            self._current_step = 1
        if self._attr_is_on and int(self._attr_percentage or 0) <= 0:
            self._attr_percentage = self._step_to_pct(max(1, self._current_step))

    async def _enter_turbo(self, op_token: int | None = None) -> bool:
        if not (self._has_turbo and self._turbo):
            return False
        if self._is_stale(op_token):
            return False
        if not self._turbo_active:
            self._pre_turbo_step = max(
                1, min(self._step_count, self._current_step or 1)
            )
        await self._send_ir(self._turbo)
        if self._is_stale(op_token):
            return False
        self._turbo_active = True
        self._current_step = self._step_count + 1
        self._attr_percentage = 100
        self._attr_is_on = True
        return True

    async def _exit_turbo(self, op_token: int | None = None) -> bool:
        if not (self._has_turbo and self._turbo and self._turbo_active):
            return True
        if self._is_stale(op_token):
            return False
        await self._send_ir(self._turbo)
        if self._is_stale(op_token):
            return False
        await asyncio.sleep(self._mode_settle_delay)
        if self._is_stale(op_token):
            return False
        restored = max(1, min(self._step_count, self._pre_turbo_step or 1))
        self._turbo_active = False
        self._current_step = restored
        self._attr_percentage = self._step_to_pct(restored)
        self._attr_is_on = True
        return True

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ):
        op_token = self._start_operation()
        self._attr_is_on = True
        await self._send_ir(self._power)
        if self._is_stale(op_token):
            return

        if self._control_mode == "buttons":
            self._turbo_active = False
            if self._current_step <= 0:
                self._current_step = 1
            if int(self._attr_percentage or 0) <= 0:
                self._attr_percentage = self._step_to_pct(self._current_step)
            self.async_write_ha_state()
            return

        pct = percentage if percentage is not None else kwargs.get("percentage", 15)
        await self.async_set_percentage(pct, _op_token=op_token)
        if self._is_stale(op_token):
            return
        if preset_mode:
            await self.async_set_preset_mode(preset_mode, _op_token=op_token)
        if self._is_stale(op_token):
            return
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._start_operation()
        if (
            self._control_mode != "buttons"
            and monotonic() < self._suppress_turn_off_until
        ):
            self._suppress_turn_off_until = 0.0
            self._attr_is_on = True
            self._ensure_on_step()
            self.async_write_ha_state()
            return

        self._suppress_turn_off_until = 0.0
        self._turbo_active = False
        self._attr_is_on = False
        self._attr_percentage = 0
        self._current_step = 0
        self._attr_preset_mode = (
            self._idle_label if self._idle_label in self._preset_actions else None
        )
        self.async_write_ha_state()
        await self._send_ir(self._power)

    async def async_set_percentage(self, percentage: int, _op_token: int | None = None):
        if self._control_mode == "buttons" or percentage is None:
            return

        op_token = _op_token if _op_token is not None else self._start_operation()
        prev_pct = int(self._attr_percentage or 0)
        pct = max(0, min(100, percentage))

        if not self._attr_is_on:
            self._attr_percentage = 0
            self._current_step = 0
            self._turbo_active = False
            self.async_write_ha_state()
            return

        if pct <= 0:
            if self._step_count >= 5:
                pct = 15
                self._suppress_turn_off_until = monotonic() + 0.45
            else:
                self._attr_percentage = 0
                self._current_step = 0
                self._attr_is_on = False
                self._turbo_active = False
                self.async_write_ha_state()
                return

        target_step = self._pct_to_step(pct)

        if target_step == self._step_count + 1 and self._has_turbo and self._turbo:
            if not self._turbo_active:
                ok = await self._enter_turbo(op_token=op_token)
                if not ok:
                    return
            else:
                self._current_step = self._step_count + 1
                self._attr_percentage = 100
                self._attr_is_on = True
            if self._is_stale(op_token):
                return
            self.async_write_ha_state()
            return

        if self._turbo_active:
            ok = await self._exit_turbo(op_token=op_token)
            if not ok:
                return

        if self._is_stale(op_token):
            return

        self._ensure_on_step()
        current_step = max(1, self._current_step)
        delta = target_step - current_step

        if (
            delta == 0
            and pct != prev_pct
            and prev_pct > 0
            and self._attr_is_on
            and target_step <= self._step_count
        ):
            if pct > prev_pct and current_step < self._step_count:
                delta = 1
                target_step = current_step + 1
            elif pct < prev_pct and current_step > 1:
                delta = -1
                target_step = current_step - 1

        if delta > 0:
            for _ in range(delta):
                if self._is_stale(op_token):
                    return
                await self._send_ir(self._up)
                if self._is_stale(op_token):
                    return
                ok = await self._sleep_step("slider", op_token=op_token)
                if not ok:
                    return
        elif delta < 0:
            for _ in range(abs(delta)):
                if self._is_stale(op_token):
                    return
                await self._send_ir(self._down)
                if self._is_stale(op_token):
                    return
                ok = await self._sleep_step("slider", op_token=op_token)
                if not ok:
                    return

        if self._is_stale(op_token):
            return

        self._current_step = target_step
        self._attr_percentage = pct
        self._attr_is_on = True
        self._turbo_active = False
        self.async_write_ha_state()

    async def async_set_preset_mode(
        self, preset_mode: str, _op_token: int | None = None
    ):
        if preset_mode not in self._preset_actions:
            return

        op_token = _op_token if _op_token is not None else self._start_operation()

        if (
            preset_mode == "turbo"
            and self._control_mode == "buttons"
            and self._has_turbo
            and self._turbo
        ):
            if self._turbo_active:
                ok = await self._exit_turbo(op_token=op_token)
                if not ok:
                    return
            else:
                ok = await self._enter_turbo(op_token=op_token)
                if not ok:
                    return
        elif (
            preset_mode in ("increase", "decrease") and self._control_mode == "buttons"
        ):
            self._ensure_on_step()
            if self._turbo_active:
                ok = await self._exit_turbo(op_token=op_token)
                if not ok:
                    return

            if self._is_stale(op_token):
                return

            if preset_mode == "increase" and self._current_step < self._step_count:
                await self._send_ir(self._up)
                if self._is_stale(op_token):
                    return
                self._current_step += 1
                self._attr_percentage = self._step_to_pct(self._current_step)
                self._attr_is_on = True
            elif preset_mode == "decrease" and self._current_step > 1:
                await self._send_ir(self._down)
                if self._is_stale(op_token):
                    return
                self._current_step -= 1
                self._attr_percentage = self._step_to_pct(self._current_step)
                self._attr_is_on = True

            ok = await self._sleep_step("buttons", op_token=op_token)
            if not ok:
                return
        else:
            code = self._preset_actions[preset_mode]
            if code:
                await self._send_ir(code)
            if self._is_stale(op_token):
                return

        if self._idle_label in self._preset_actions and preset_mode != self._idle_label:
            self._attr_preset_mode = self._idle_label
        elif self._control_mode == "buttons":
            self._attr_preset_mode = None
        else:
            self._attr_preset_mode = preset_mode

        self.async_write_ha_state()

    async def async_oscillate(self, oscillating: bool, *args, **kwargs) -> None:
        try:
            if not self._has_osc:
                return
            code = self._osc_up if oscillating else self._osc_down
            await self._send_ir(code)
            self._attr_oscillating = oscillating
            self.async_write_ha_state()
        except Exception as err:
            self._hass.states.async_set(
                f"sensor.ir_fan_control_osc_{self._entry_id[:6]}",
                f"{type(err).__name__}:{str(err)[:120]}",
            )
            raise

    async def async_set_oscillating(self, oscillating: bool, *args, **kwargs) -> None:
        await self.async_oscillate(oscillating, *args, **kwargs)

    def oscillate(self, oscillating: bool) -> None:
        self._hass.add_job(self.async_oscillate(oscillating))

    def set_oscillating(self, oscillating: bool) -> None:
        self._hass.add_job(self.async_oscillate(oscillating))
