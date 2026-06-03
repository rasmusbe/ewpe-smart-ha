# Wire parameters reference

All parameters use short string keys in Gree / EWPE Smart UDP packets. Values are
integers unless noted.

**Parameter catalog sources:** [gree-remote README](https://github.com/tomikaa87/gree-remote/blob/master/README.md)
(canonical wire keys), [gree_custom `api.py`](https://github.com/p-monteiro/HomeAssistant-GreeClimateComponent-Rewrite/blob/e5ed1952102c104f0232ca816c87ed8bbd46c9d7/custom_components/gree_custom/aiogree/api.py)
(extended `GreeProp` / swing enums). This integration validates mappings against
live hardware — see [hardware-notes.md](hardware-notes.md) and [references.md](references.md).

**Polling lists** (defined in `params_catalog.py`):

- `ALL_KNOWN_PARAMS` — full catalog (**140** keys on reference hardware;
  maintained in [`wire_params.json`](../custom_components/ewpe_smart/data/wire_params.json)) requested on
  the first status poll when an integration entry starts (or reloads).
- `device.supported_params` — the `cols` the device echoed on that discovery
  poll; used for all subsequent runtime polls.
- Every wire key in the catalog has an **explicit entity mapping** (climate,
  switch, select, number, binary sensor, or named sensor). Generic
  `sensor.<wire_key>` fallback is only used for cols returned by the device
  that are not listed in `wire_params.json` (under `custom_components/ewpe_smart/data/`).
- Metadata / string cols (`mac`, `ver`, `host`, …) use **text sensors** when
  the device echoes non-integer values.

**Transform rule:** temperature-like params listed in `TEMP_OFFSET_PARAMS` are
decoded in `device.get_status()` by adding `TEMP_SENSOR_OFFSET` (−40). Entities
always see Celsius degrees.

---

## Climate core

| Key | Name | Values | HA entity | Writable |
|-----|------|--------|-----------|----------|
| `Pow` | Power | 0=off, 1=on | `climate` (via HVAC mode) | Yes |
| `Mod` | HVAC mode | 0=Auto, 1=Cool, 2=Dry, 3=Fan, 4=Heat | `climate` | Yes |
| `SetTem` | Target temperature | 16–30 (°C on wire) | `climate` | Yes |
| `TemUn` | Temperature unit | 0=°C, 1=°F | *(not exposed)* | — |
| `TemSen` | Indoor temperature sensor | raw; **decoded −40 → °C** | `sensor.indoor_temperature`, `climate.current_temperature` | Read-only |
| `WdSpd` | Fan speed level | see [Wind speed](#wind-speed-wdspd-quiet-tur) | `select.wind_speed` | Yes |

---

## Wind speed (`WdSpd`, `Quiet`, `Tur`)

The native EWPE Smart app treats auto, five fan steps, quiet, and turbo as
**mutually exclusive**. The integration mirrors that in one select entity.

### Fan speed levels (`WdSpd`)

| Wire value | Select option |
|------------|---------------|
| 0 | Auto |
| 1 | Low |
| 2 | Medium low |
| 3 | Medium |
| 4 | Medium high |
| 5 | High |

### Quiet (`Quiet`)

| Wire value | Common meaning | Sources |
|------------|----------------|---------|
| 0 | Off | [gree-remote](https://github.com/tomikaa87/gree-remote/blob/master/README.md) |
| 1 | Legacy “on” / **mode1** | gree-remote documents binary `1=on`; [gree-hvac-client](https://github.com/inwaar/gree-hvac-client) maps `mode1→1` |
| 2 | **mode2** — what modern Gree/EWPE apps send | [greeclimate #87](https://github.com/cmroche/greeclimate/issues/87), [gree-hvac-client](https://github.com/inwaar/gree-hvac-client) `mode2→2` |
| 3 | **mode3** — third quiet level (rare) | [gree-hvac-client](https://github.com/inwaar/gree-hvac-client), [FeranyDev/gree_havc_mqtt_bridge_go](https://github.com/FeranyDev/gree_havc_mqtt_bridge_go) |

**What is the difference between 1 and 2?**

Nobody documents distinct fan behaviour per level in the canonical protocol docs.
The picture from cross-referencing:

- **[gree-remote](https://github.com/tomikaa87/gree-remote/blob/master/README.md)** treats `Quiet` as binary (`0` / `1`). That matches older RE and early clients.
- **[inwaar/gree-hvac-client](https://github.com/inwaar/gree-hvac-client)** treats quiet as **four levels**: `off=0`, `mode1=1`, `mode2=2`, `mode3=3` — but does not define what each level does physically (descriptions are empty in the README).
- **[greeclimate issue #87](https://github.com/cmroche/greeclimate/issues/87)** (Gree Amber, firmware V3.75) is the clearest real-world evidence:
  - HA sent `Quiet=1` → unit entered quiet but **did not stick** reliably.
  - Official Gree app sent `Quiet=2` → status polled back `Quiet=2`.
  - Fixed in greeclimate 1.4.6: `device.quiet = True` now writes **`2`**, not `1` ([commit](https://github.com/cmroche/greeclimate/commit/129a1905940a0c723dce4890e6d567346967137c)).

So **`1` vs `2` is not “off vs on” on newer firmware** — both non-zero values mean “quiet active”, but **`2` is what current Gree/EWPE apps use** and what units report when quiet is properly engaged. Value `1` looks like a **legacy or partial** quiet state (older docs, or clients that only knew binary on).

Value `3` (`mode3`) appears in MQTT bridges ([vsimonaitis/gree-hvac-mqtt-bridge](https://hub.docker.com/r/vsimonaitis/gree-hvac-mqtt-bridge)) but no public source defines a third fan step; treat as **unit-specific** until probed.

**This integration:**

- **Writes** `Quiet=2` when selecting quiet (`QUIET_MODE_ON` in `const.py`), following greeclimate.
- **Reads** any non-zero value (`1`, `2`, or `3`) as quiet active — see `test_select.py`.

When reading state: **turbo beats quiet beats fan speed**.

When writing:

| Select option | Params sent |
|---------------|-------------|
| Auto | `WdSpd=0`, `Quiet=0`, `Tur=0` |
| Low … High | `WdSpd=1…5`, `Quiet=0`, `Tur=0` |
| Quiet | `Quiet=2`, `Tur=0` *(WdSpd left unchanged)* |
| Turbo | `Tur=1`, `Quiet=0` *(WdSpd left unchanged)* |

`Quiet` and `Tur` are **not** exposed as switches (removed to avoid duplication).

---

## Swing

Fixed positions match the native app. Wire value **1 = full swing** for both axes.

### Horizontal (`SwingLfRig`)

| Wire value | Select option |
|------------|---------------|
| 1 | Full swing |
| 2 | Left |
| 3 | Left center |
| 4 | Center |
| 5 | Right center |
| 6 | Right |

### Vertical (`SwUpDn`)

| Wire value | Select option |
|------------|---------------|
| 1 | Full swing |
| 2 | Fixed upper |
| 3 | Fixed upper middle |
| 4 | Fixed middle |
| 5 | Fixed lower middle |
| 6 | Fixed lower |
| 7 | Swing upper |
| 8 | Swing upper middle |
| 9 | Swing middle |
| 10 | Swing lower middle |
| 11 | Swing lower |

Values **7–11** are partial-swing variants from protocol references. They are
exposed in the vertical swing select but marked **experimental** here — on some
units (including tested Daitsu hardware) selecting them causes full-swing
misbehaviour. Prefer fixed positions (2–6) unless you have verified 7–11 on
your firmware.

---

## Switches (binary 0/1)

Each maps to `switch.<name>`. ON = 1, OFF = 0 unless noted.

**One switch per wire key** — if the device echoes several keys that might relate
to the same feature (for example `BuzzerCtrl` and `Buzzer_ON_OFF`), each gets its
own switch so you can see which one actually works on your firmware.

| Key(s) | Entity name | Translation key | Notes |
|--------|-------------|-----------------|-------|
| `SmartSlpMod` | Smart sleep mode | `smart_slp_mod` | |
| `SlpMod` | Sleep mode | `slp_mod` | |
| `SwhSlp` | Sleep mode (legacy) | `swh_slp` | |
| `Emod` | Economy mode | `emod` | |
| `SvSt` | Energy save | `svst` | |
| `NobodySave` | Nobody save | `nobody_save` | |
| `BuzzerCtrl` | Beeper (BuzzerCtrl) | `buzzer_ctrl` | |
| `Buzzer_ON_OFF` | Beeper (Buzzer_ON_OFF) | `buzzer_on_off` | |
| `Blo` | X-Fan | `xfan` | Post-run fan dry |
| `Health` | Health | `health` | Anion / health mode |
| `Lig` | Display light | `display_light` | Panel LED |
| `Air` | Fresh air | `fresh_air` | Fresh-air valve |
| `AntiDirectBlow` | Anti direct blow | `anti_direct_blow` | No direct airflow |
| `LigSen` | Auto display | `sensor_light` | Ambient-light-driven display |
| `StHt` | 8 °C heat | `smart_heat_8c` | Smart heat / anti-freeze |
| `ChildLock` | Child lock | `child_lock` | Panel lock |
| `AutoClean` | Auto clean | `auto_clean` | Self-clean cycle |
| `UvcControl` | UV-C control | `uvc_control` | UV sterilisation |
| `CoolFeel` | Cool feel | `cool_feel` | Feels-like cooling |
| `SmartWind` | Smart wind | `smart_wind` | Smart airflow |
| `AutoPowReduce` | Auto power reduce | `auto_pow_reduce` | Automatic power limiting |
| `UnmanedShutDown` | Unoccupied shutdown | `unoccupied_shutdown` | Auto-off when empty |
| `TmrOn` / `TmrOff` | Timer on / off | `timer_on` / `timer_off` | Built-in timer flags |

All switches use **hide-when-missing**: the entity exists only if the device
returns the key in status `cols`.

---

## Sensors (read-only)

| Key | Entity | Transform | Category |
|-----|--------|-----------|----------|
| `TemSen` | Indoor temperature | −40 → °C | Measurement |
| `OutEnvTem` | Outdoor temperature | −40 → °C | Measurement |
| `DwatSen` | Humidity | Raw 0–100 → % | Measurement |
| `PM2P5` | PM2.5 | Raw integer | Measurement |
| `FaultDisplay` | Fault code | Raw integer | Diagnostic |
| `Dfltr` | Filter status | Raw integer | Diagnostic |
| `AllErr`, `JFErrorCode`, … | Fault aggregates | Raw integer | Diagnostic |
| *(unmapped)* | Raw wire key | Raw integer | Diagnostic fallback |

Unmapped parameters in `supported_params` appear as diagnostic sensors named
after the wire key (for example `sensor.newtimer`).

---

## Numbers (writable)

| Key | Entity | Range | Notes |
|-----|--------|-------|-------|
| `TmrOnMinLf` / `TmrOffMinLf` | Timer minutes left | 0–1440 | On/off countdown |
| `TmrLpTms` | Timer loop times | 0–255 | |
| `UnmanedOffTime` | Unoccupied off time | 0–1440 min | |
| `Slp1L1`–`Slp1L8`, `Slp1H1`–`Slp1H8` | Sleep curve steps | 16–30 °C | Night temperature profile |

---

## Binary sensors (read-only)

| Key | Entity | Notes |
|-----|--------|-------|
| `ReplaceHEPA` | Replace HEPA filter | Maintenance alert |
| `HasTmr` | Has timer | Timer system active |
| `MicroSen` | Motion | Presence / motion flag |
| `Dpump` | Drain pump | Drain pump running |

---

## Undocumented / special parameters

### `Buzzer_ON_OFF` (command append)

Some clients append `Buzzer_ON_OFF=1` to **command** packets to suppress the
physical beep. This is **not** the same as the beeper switch entity — the flag
does not persist across power cycles and must be sent with each command.

A per-entry **silent commands** option was designed in
[PR #15](https://github.com/anaryk/ewpe-smart-ha/pull/15) (default on) but was
later reverted on some forks. The beeper **switch** entity toggles the persisted
panel setting when the firmware supports it; on tested hardware the switch did
not change behaviour — see [hardware-notes.md](hardware-notes.md).

---

## Parameter groups in code

```text
params_catalog.py
  ALL_KNOWN_PARAMS     — requested on first poll / probe status (default)
  SWITCH_DESCRIPTIONS  — one switch per wire key
  EXTRA_SENSOR_DESCRIPTIONS, BINARY_SENSOR_DESCRIPTIONS, NUMBER_DESCRIPTIONS
  diagnostic_params()  — unmapped supported keys → raw diagnostic sensors

device.py
  supported_params     — cached reply cols after first full-catalog poll
  runtime polls        — poll_params(supported_params)
```

---

## Value quick-reference tables

### HVAC mode (`Mod`)

| Value | Mode |
|-------|------|
| 0 | Auto |
| 1 | Cool |
| 2 | Dry |
| 3 | Fan only |
| 4 | Heat |

### Power (`Pow`)

| Value | State |
|-------|-------|
| 0 | Off |
| 1 | On |
