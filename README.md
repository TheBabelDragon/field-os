# field-os

**v0.1 — admitted field contract.**

The engine should never know what a *thing* is.
It should only know what state exists and what transformations are permitted.

`field-os` is the shared language sitting between
[`metafield-engine`](https://github.com/TheBabelDragon/metafield-engine)
(host substrate, world kernel, renderer-as-viewer) and
[`c3-field-swarm`](https://github.com/TheBabelDragon/c3-field-swarm)
(ESP32-C3 wireless edge, `FieldView → FieldDelta`, `bylight_phy`).

It is not a game engine. It is not a wireless sensor network.
It is a field operating system:

```
physical substrate → measurable fields → state transitions → distributed observers → actuators
```

A cell is an address, not a Minecraft cube.
A sensor is a field writer.
A simulation system is also a field writer.
Both emit the same object: `FieldDelta`.

## Why this repo exists

The two live trees already have the pieces:

| Tree | Already has |
| --- | --- |
| `metafield-engine` | substrate / fields / world / kernel / provenance / replay stubs |
| `c3-field-swarm` | FieldView, FieldDelta, swarm time, bylight analog PHY |

What they do not yet share is one *admitted* packet language, one conservation
audit, and one replay log that can mix physical observations with simulated
deltas without pretending they are the same.

This repository owns that contract. Implementations stay in their trees.

## Killer primitive: measurement, not simulation

A node does not report `temperature = 31.2`.
It reports an observation. Same machinery ingests optical intensity, audio,
accelerometer vectors, photodiode waveforms, motor position, CAN telemetry,
ultrasonic echo, WiFi CSI. The kernel does not care.

```
SIMULATION     FieldView  → System → FieldDelta
PHYSICAL       Sensor     → Observation → FieldDelta
```

## v0.1 contract

```
Observation → admission + validation → FieldDelta
    → deterministic ordering → FieldTick → replay
```

The test suite must prove:

- Observation → FieldDelta
- deterministic FieldDelta ordering
- provenance survives transitions
- synthetic ≠ physical
- FieldTick replay is deterministic
- conservation audit works
- invalid observations are rejected
- bylight observations enter the kernel

See [docs/CONTRACT.md](docs/CONTRACT.md). Schemas in `schema/` are locked.

## Install / run

Stdlib only.

```bash
cd field-os
python3 -m unittest discover -s tests -v
python3 examples/room_loop.py
```

## Layout

```
docs/          manifesto, v0.1 contract, vocabulary, conservation, replay, bylight
schema/        locked JSON Schema (Observation / FieldDelta / FieldTick / …)
fieldos/       host reference kernel (Python)
examples/      six-node room as a software field computer
tests/         v0.1 contract suite
```

## Non-goals

- Do not replace `metafield-engine` or `c3-field-swarm`.
- Do not hide analog PHY behind `LINK_UP`.
- Do not let synthetic values silently become measured.
- Do not make the cell a block type.
- No ECS, renderer, world, network stack, or scheduler in this repo.

See [docs/MANIFEST.md](docs/MANIFEST.md) and [docs/STACK.md](docs/STACK.md).
