# EWPE Smart — developer documentation

This folder documents how the Home Assistant integration works today: wire
protocol, device parameters, entity mapping, and the standalone probe tool.

The user-facing install guide remains in the [repository README](../README.md).
The original Phase 1 design spec lives in
[superpowers/specs/2026-04-28-ewpe-smart-ha-integration-design.md](superpowers/specs/2026-04-28-ewpe-smart-ha-integration-design.md)
and is partially outdated — prefer the docs below for current behaviour.

## Contents

| Document | What it covers |
|----------|----------------|
| [integration.md](integration.md) | Architecture, setup flow, polling, entity discovery |
| [parameters.md](parameters.md) | Every known wire parameter — values, transforms, HA mapping |
| [protocol.md](protocol.md) | UDP transport, V1/V2 encryption, packet types, bind handshake |
| [probe.md](probe.md) | `tools/probe.py` — scan, status, set for hardware debugging |
| [hardware-notes.md](hardware-notes.md) | Findings from live unit testing (Daitsu / EWPE Smart app parity) |
| [references.md](references.md) | External protocol docs, comparable integrations, upstream PRs |

## Quick reference

**Platforms:** `climate`, `sensor`, `select`, `switch`

**Discovery rule:** entities appear only when the device includes the
corresponding parameter in a status reply (`hide-when-missing`). There is no
entity churn after the first successful poll.

**Temperature decoding:** `TemSen` and `OutEnvTem` raw wire values are offset
by **−40 °C** in `device.get_status()` before entities see them.

**Wind speed:** fan level (`WdSpd`), quiet (`Quiet`), and turbo (`Tur`) are
mutually exclusive and exposed as a single `select.wind_speed` entity — not as
climate fan modes or separate quiet/turbo switches.
