# Home Assistant integration — Pill Dispenser

The ESPHome firmware in [`../esphome/pill-dispenser.yaml`](../esphome/pill-dispenser.yaml)
exposes the physical device to Home Assistant via the ESPHome native API. The
files here wire that device into a usable HA surface: a dashboard card, helper
entities, and the dose / refill / mismatch automations.

## Files

| File | Purpose |
|------|---------|
| `pill-dispenser-package.yaml` | All helpers, template sensors, scripts, and automations bundled as an HA [package](https://www.home-assistant.io/docs/configuration/packages/). |
| `dashboard.yaml` | A self-contained Lovelace `vertical-stack` card. No HACS dependencies. |

## Install

1. **Adopt the ESPHome device.** Flash `../esphome/pill-dispenser.yaml`, then
   in HA → *Settings → Devices & Services* accept the ESPHome discovery prompt
   for `pill-dispenser`. Confirm these entities exist:

   - `sensor.pill_dispenser_current_compartment`
   - `sensor.pill_dispenser_pills_dispensed`
   - `sensor.pill_dispenser_last_dispense_status`
   - `binary_sensor.pill_dispenser_drum_homed`
   - `number.pill_dispenser_pills_per_dose`
   - `switch.pill_dispenser_buzzer_mute`
   - `button.pill_dispenser_dispense_next`
   - `button.pill_dispenser_home_drum`
   - `button.pill_dispenser_dispense_compartment_1` … `_9`

2. **Enable packages** (one-time) in `/config/configuration.yaml`:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

3. **Drop the package in place:**

   ```bash
   mkdir -p /config/packages
   cp pill-dispenser-package.yaml /config/packages/
   ```

   Then *Developer Tools → YAML → Check Configuration → Reload All YAML*.

4. **Add the dashboard.** Open the dashboard you want to host the card on,
   choose *Edit Dashboard → ⋮ → Raw configuration editor*, and paste the
   contents of `dashboard.yaml` under `views: → cards:`. Save.

5. **Tune `notify.notify`.** The automations target the default `notify.notify`
   group. If you use a specific mobile target (e.g.
   `notify.mobile_app_pixel_8`), search-and-replace `notify.notify` in
   `pill-dispenser-package.yaml`.

## Helpers created

| Entity | Default | Notes |
|--------|---------|-------|
| `input_datetime.pill_dispenser_morning_time` | 08:00 | Morning dose time. |
| `input_datetime.pill_dispenser_evening_time` | 20:00 | Evening dose time. |
| `input_datetime.pill_dispenser_last_dispense_at` | — | Stamped by the dispense script. |
| `input_boolean.pill_dispenser_morning_enabled` | on | Morning automation toggle. |
| `input_boolean.pill_dispenser_evening_enabled` | off | Evening automation toggle. |
| `input_boolean.pill_dispenser_dose_pending_ack` | off | Set on dispense, cleared on ack. |
| `input_number.pill_dispenser_last_refill_compartment` | 9 | Highest compartment that still has pills. Reset to 9 on refill. |

## Derived sensors

- `sensor.pill_dispenser_compartments_remaining` — pills-remaining count
  (1..9) walking forward from the current compartment to the last refilled
  one. `unknown` until the drum is homed.
- `sensor.pill_dispenser_needs_refill` — `on` when ≤2 compartments remain.

## Automations

| ID | What it does |
|----|--------------|
| `pill_dispenser_morning_dose` | Dispenses + notifies at the configured morning time when enabled. |
| `pill_dispenser_evening_dose` | Same for evening (off by default). |
| `pill_dispenser_missed_dose_escalation` | If the dose is unacknowledged after 30 / 60 / 120 min, escalating push notifications, ending in a critical alarm-stream alert. |
| `pill_dispenser_refill_reminder` | Push notification when `needs_refill` flips to `on`. |
| `pill_dispenser_count_mismatch` | High-priority alert when the IR-counted pill count differs from the expected dose. |
| `pill_dispenser_ack_action` | Handles the `PILL_DISPENSER_ACK` mobile notification action and clears the pending flag. |

## Refill workflow

The package treats the drum like a one-way odometer: compartments 1→2→…→9→1,
each "spent" after it's dispensed. After physically refilling the drum, tap
**Mark fully refilled** on the dashboard (or call
`input_number.set_value` with `value: 9`) to reset the remaining counter.

If you ever partially refill, set
`input_number.pill_dispenser_last_refill_compartment` to the highest
compartment that now holds pills.

## Notes

- The dose-time triggers fire on a `sensor.time` template comparison —
  HA's built-in 1-minute clock sensor. No `time` platform configuration is
  required because `sensor.time` is provided by the default `time_date` setup.
  If your HA install lacks it, add `sensor: [{ platform: time_date, display_options: ['time'] }]`
  to `configuration.yaml`.
- The morning/evening automations refuse to fire while the drum is unhomed
  (`current_compartment == 0`). Re-home from the dashboard and they'll resume.
- `priority: high`, `ttl: 0`, and `channel: alarm_stream` are
  [Android-specific mobile_app keys](https://companion.home-assistant.io/docs/notifications/critical-notifications/);
  they are harmless on iOS but iOS critical alerts use a different mechanism
  (`push.sound.critical: 1` under `data:`).
