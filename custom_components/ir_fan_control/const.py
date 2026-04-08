from __future__ import annotations

DOMAIN = "ir_fan_control"

CONF_TOPIC = "topic"
CONF_NAME = "name"
CONF_STEP_COUNT = "step_count"
CONF_PULSE_DELAY = "pulse_delay"
CONF_CONTROL_MODE = "control_mode"
CONF_DIRECTION_IDLE = "direction_idle"
CONF_OSC_MODE = "osc_mode"

CONF_POWER_CODE = "power_code"
CONF_SPEED_UP_CODE = "speed_up_code"
CONF_SPEED_DOWN_CODE = "speed_down_code"
CONF_TURBO_CODE = "turbo_code"
CONF_HAS_TURBO = "has_turbo"

CONF_HAS_DIRECTION = "has_direction"
CONF_LOUVER_LEFT = "louver_left_code"
CONF_LOUVER_RIGHT = "louver_right_code"
CONF_LEFT_LABEL = "left_label"
CONF_RIGHT_LABEL = "right_label"
CONF_IDLE_LABEL = "idle_label"

CONF_HAS_OSC = "has_osc"
CONF_OSC_UP = "osc_up_code"
CONF_OSC_DOWN = "osc_down_code"

DEFAULT_NAME = "IR Fan Control"
DEFAULT_STEP_COUNT = 5
DEFAULT_PULSE_DELAY = 0.5
DEFAULT_CONTROL_MODE = "slider"
DEFAULT_DIRECTION_IDLE = True
DEFAULT_OSC_MODE = "toggle"
DEFAULT_LEFT_LABEL = "left"
DEFAULT_RIGHT_LABEL = "right"
DEFAULT_IDLE_LABEL = "idle"
