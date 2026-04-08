# IR Fan Control (Custom Integration)

Repository: https://github.com/Tipana/ir_fan_control

Native Home Assistant fan entity that sends IR codes through Zigbee2MQTT.

## What's New in v0.1.6
- Added `stable-v1` pacing profile inside the fan entity runtime.
- Added stale-command cancellation so older queued actions cannot overwrite newer presses.
- Improved button/slider timing separation for more predictable command flow on busy Zigbee networks.

It supports:
- Variable speed fan control (2-6 steps)
- Optional turbo/boost
- Optional action buttons (for left/right, timer/sensor, etc.)
- Optional oscillation in `toggle` or `levels` mode
- `slider` or `buttons` control style

## Requirements
- Home Assistant with MQTT configured
- Zigbee2MQTT IR sender working
- MQTT topic for IR send, usually `zigbee2mqtt/<device_name>/set`
- Base64 IR codes for each function you want to expose

## Installation
1. Copy `custom_components/ir_fan_control/` into `/config/custom_components/`.
2. Restart Home Assistant.
3. Go to Settings -> Devices and Services -> Add Integration -> `IR Fan Control`.

## Configuration Reference
Required fields:
- `name`
- `topic`
- `power_code`
- `speed_up_code`
- `speed_down_code`

Main options:
- `control_mode`
  - `slider`: normal percentage slider UI
  - `buttons`: single-press `increase`/`decrease` actions in preset list
- `step_count`: number of discrete speed steps (`2-6`)
- `pulse_delay`: base delay between repeated pulses (recommended `0.5` to `1.0` on busy Zigbee)
- `has_turbo` + `turbo_code`: optional boost mode
- `has_direction`: enables action A/B buttons
  - `louver_left_code` and `louver_right_code` are generic single-press action codes
  - `left_label` and `right_label` rename these buttons (example: `Timer`, `Sensor`)
- `direction_idle`: if enabled, preset returns to `idle` after action button press
- `has_osc` + `osc_mode`
  - `none`: hide oscillation controls
  - `toggle`: use oscillate on/off behavior
  - `levels`: show only `osc_less` and `osc_more` presets
- `osc_up_code` / `osc_down_code`: oscillation codes

## Pacing Profile
`stable-v1` is always enabled in this release.

It applies:
- fast clear delay for each publish (`ir_code_to_send` -> `null`)
- slower repeated-step pacing for slider mode
- slightly faster repeated-step pacing for buttons mode
- stale-operation cancellation whenever a newer command arrives

This is designed to reduce delayed command replay under high UI/event load.

## Recommended Profiles
### Fan (5 speeds + turbo)
- `control_mode`: `buttons` or `slider` (your preference)
- `step_count`: `5`
- `has_turbo`: `true`
- `has_osc`: `true`
- `osc_mode`: `levels`
- `has_direction`: `true` if you want extra action buttons

### Heater (power + increase + decrease)
- `control_mode`: `buttons`
- `step_count`: `3` (or device equivalent)
- `has_turbo`: `false`
- `has_osc`: `false`
- Optional `has_direction`: `true` for `Timer` / `Sensor` single-press buttons

## UI Behavior Notes
- Preset label text (`Preset mode`) is defined by Home Assistant frontend and cannot be renamed by integration code.
- If `direction_idle` is enabled, action presets return to `idle` after firing.
- In `osc_mode: levels`, `osc_on` and `osc_off` are hidden by design.
- If fan and heater tile heights look different, verify both entries use the same `control_mode`.

## Automation Examples
Turn on:
```yaml
- service: fan.turn_on
  target:
    entity_id: fan.parents_bedroom_fan_ir
```

Set speed:
```yaml
- service: fan.set_percentage
  target:
    entity_id: fan.parents_bedroom_fan_ir
  data:
    percentage: 60
```

Turn off:
```yaml
- service: fan.turn_off
  target:
    entity_id: fan.parents_bedroom_fan_ir
```

## Troubleshooting
- No IR response:
  - Verify MQTT topic points to `/set`
  - Confirm codes are valid base64 strings
  - Increase `pulse_delay` to reduce Zigbee congestion
- Delayed or out-of-order actions:
  - Close duplicate HA dashboard sessions/tabs
  - Confirm system has no websocket overload warnings
- Config dialog error:
  - Restart HA and reopen integration options
- Entity missing controls:
  - Check corresponding `has_*` flags and code fields are populated

## Screenshots
Preset menu with action controls:

![Preset mode menu](docs/fan-preset-mode-menu.png)

Dashboard example with fan + heater entities:

![Fan and heater tiles](docs/fan-heater-tile-size.png)
