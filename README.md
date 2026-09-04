# field-os

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
It reports an observation:

```json
{
  "field": "temperature",
  "channel": "temperature",
  "location": {"kind": "node", "id": "c3-04"},
  "value": 31.2,
  "unit": "degC",
  "uncertainty": 0.4,
  "timestamp_ns": 1756930000000000000,
  "field_epoch": 12,
  "field_sequence": 18442,
  "node_id": "c3-04",
  "sequence": 901,
  "provenance": {
    "class": "physical",
    "source": "sensor",
    "instrument": "sht31",
    "node_id": "c3-04"
  }
}
```

Same machinery ingests optical intensity, audio amplitude, accelerometer
vectors, photodiode waveforms, motor position, CAN telemetry, ultrasonic
echo, WiFi CSI. The kernel does not care.

```
SIMULATION     FieldView  → System → FieldDelta
PHYSICAL       Sensor     → Observation → FieldDelta
```

Two sources. One state-transition language.

## Install / run

Stdlib only.

```bash
cd field-os
python3 -m unittest discover -s tests -v
python3 examples/room_loop.py
```

## Layout

```
docs/          manifesto, vocabulary, conservation, replay, bylight, stack map
schema/        JSON Schema for Observation / FieldDelta / FieldTick
fieldos/       host reference kernel (Python)
examples/      six-node room as a software field computer
tests/         determinism, provenance, conservation, replay
```

## Non-goals

- Do not replace `metafield-engine` or `c3-field-swarm`.
- Do not hide analog PHY behind `LINK_UP`.
- Do not let synthetic values silently become measured.
- Do not make the cell a block type.

See [docs/MANIFEST.md](docs/MANIFEST.md) and [docs/STACK.md](docs/STACK.md).
