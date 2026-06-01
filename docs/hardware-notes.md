# Hardware testing notes

Findings from live testing on a **Daitsu** unit controlled via the EWPE Smart
app. Other brands may differ — treat these as data points, not universal rules.

Source: probe snapshots and HA smoke tests documented in project chat sessions
(2026). Cross-check wire keys against
[gree-remote](https://github.com/tomikaa87/gree-remote/blob/master/README.md)
and [gree_custom `api.py`](https://github.com/p-monteiro/HomeAssistant-GreeClimateComponent-Rewrite/blob/e5ed1952102c104f0232ca816c87ed8bbd46c9d7/custom_components/gree_custom/aiogree/api.py);
see [references.md](references.md).

## Unit snapshot (reference)

A tested unit returned 26 of 27 requested discovery columns. Decoded highlights:

| Param | Raw wire | Decoded / meaning |
|-------|----------|-------------------|
| `TemSen` | 61 | 21 °C (offset −40) |
| `OutEnvTem` | 62 | 22 °C (offset −40) |
| `SwingLfRig` | 1 | Full swing |
| `SwUpDn` | 6 | Fixed lower |
| `WdSpd` | 0 | Auto |
| `DwatSen` | 0 | Humidity — always 0 |
| `StHt` | 0 | 8 °C heat — present but ineffective |
| `Buzzer_ON_OFF` | 1 | Beeper on — switch entity did not change behaviour |

`BuzzerCtrl` was absent from the reply.

## Confirmed working

- Outdoor temperature sensor (`OutEnvTem`) with −40 offset
- Horizontal swing fixed positions (left, center, right, full swing)
- Vertical swing fixed positions (upper → lower, full swing)
- Unified wind speed select (auto, five levels, quiet, turbo)
- Standard switches: sleep, X-fan, health, display light, energy save, fresh air,
  sleep mode, anti direct blow, auto display, 8 °C heat (`StHt`)

## Known limitations on tested hardware

These entities are exposed when the device returns the param in status `cols`,
but behaviour on the reference Daitsu unit was unreliable:

### 8 °C heating (`StHt`) — `switch.smart_heat_8c`

Parameter appears in status and the switch reflects the wire value, but toggling
had **no visible effect** in the native app or HA on tested hardware. The entity
is still useful for monitoring and for units where the feature works.

### Humidity (`DwatSen`) — `sensor.humidity`

Parameter appears in status but value stayed **0** on tested hardware — likely
no physical sensor despite the key being present. The entity reports the wire
value literally (including `0 %`).

### Beeper switch (`Buzzer_ON_OFF`)

Entity was implemented but **did not control the panel beep** on tested hardware.
A separate design explored appending `Buzzer_ON_OFF=1` to every HA **command**
(silent commands option) — that suppresses beeps on some firmware but is distinct
from a persistent beeper toggle.

### Vertical swing values 7–11 — experimental

Partial-swing wire values are available in `select.swing_vertical` but caused
**full-swing misbehaviour** when selected on this unit. Prefer fixed positions
(2–6) unless verified on your firmware. See [parameters.md](parameters.md).

## Native app parity decisions

### Wind speed unification

The EWPE Smart app shows one control: Auto, Quiet, Turbo, or Low → High — never
multiple at once. The integration removed:

- Climate **fan mode** dropdown
- Separate **Quiet** and **Turbo** switches

…in favour of `select.wind_speed`. Reading priority: turbo > quiet > `WdSpd`.

When setting quiet/turbo, **`WdSpd` is not written** — the unit keeps the last
fan step internally (verified with probe experiments).

### Swing labels

Fixed vertical and horizontal positions were mapped from native app screenshots:

- Horizontal: Left, Left center, Center, Right center, Right + Full swing
- Vertical: Fixed upper through Fixed lower + Full swing
- Wire value **1 = full swing** on both axes

## Bind / discovery issues

### Scan works, bind times out

Observed on V3.4M-style firmware when scan and bind used **separate UDP
sockets**. Fix: `scan_then_bind()` sends both on one socket (same as greeclimate
session behaviour).

### Docker Home Assistant

Host networking is required for reliable UDP/7000 if HA runs in Docker. Bridge
mode may break broadcast discovery and sometimes unicast bind.

### Discovery vs setup

Network scan (broadcast) can succeed while manual setup (unicast bind to chosen
IP) fails if bind handshake timing or protocol version is wrong — these are
separate code paths; use `probe.py scan --bind` to isolate.

## Hide-when-missing validation

Entity discovery is driven by the **first successful status poll** after setup.
If a param is in the device's capability set but missing from that poll's
`cols`, no entity is created. Re-add the integration after firmware updates that
expose new parameters.

## Contributing new mappings

When adding support for a parameter:

1. Capture `probe.py status` output (discovery mode).
2. Confirm read values and test `probe.py set`.
3. Compare with the native app UI labels.
4. Document wire value → UI label mapping in [parameters.md](parameters.md).
5. Add a row to `tests/test_entity_discovery.py` if the param should create an
   entity on reference hardware.
