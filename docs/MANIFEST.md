# Manifest — field operating system

Written against the live trees of 2026-09-03:
`metafield-engine` (substrate, fields, world, ecs, scheduler, hardware,
networking, physics, renderer, fabric, ingest) and `c3-field-swarm`
(field, swarm, systems, transport, telemetry, `bylight_phy`).

## 1. The interesting abstraction is not a game engine

```
physical substrate → measurable fields → state transitions
        → distributed observers → actuators
```

A cell can be a point or volume in space, an optical measurement,
temperature, pressure, acoustic energy, electromagnetic state, charge,
information, mechanical displacement, sensor confidence, or hardware
availability.

Rule: the engine never knows what a *thing* is. It only knows what
state exists and what transformations are permitted. "Thing" is a
schema layered above.

## 2. Measurement is the killer primitive

Invert `ESP32 → sensor → value → packet → swarm` into
`phenomenon → observation → field contribution`.

Sensors become field writers. Simulation systems already emit deltas
instead of mutating state. That symmetry is the whole architecture.

## 3. `bylight_phy` is the first real field

Not a comms gimmick. A measurement channel and an actuator channel:

```
photodiode → waveform → edge → decoder → Observation → FieldDelta → swarm
Field state → actuator → LED / laser / modulator → physical optical field
```

Closed loop: Field → physical world → Field.
A tiny distributed cyber-physical substrate.

## 4. Keep the physical channel ugly on purpose

Expose signal, noise, threshold, edge_time, pulse_width, confidence,
dropout, lock_state, ambient, saturation as fields:

`optical.signal` `optical.noise` `optical.snr` `optical.edge`
`optical.lock` `optical.dropout` `optical.confidence`

The swarm reasons about the quality of its own nervous system.
"I can see node 4, but the channel is degrading" is more useful than
`LINK_UP`.

## 5. Optional conservation laws

Candidate channels: matter, energy, temperature, pressure, charge,
momentum, entropy, information.

Optional invariants, not mandatory physics:

- energy / matter / charge: Δtotal ≈ 0
- information: decay unless refreshed
- temperature: diffusion toward equilibrium

`FieldDeltaList` is then an audit trail, not a bag of mutations.

## 6. Provenance is a first-class property

Every transition carries `class ∈ {physical, derived, synthetic, remote, replayed}`
plus source, instrument, node, sequence, confidence.

The world may mix REAL / SIMULATED / INFERRED / REMOTE / REPLAYED.
It must not pretend they are equivalent. Unlabeled is synthetic.
Synthetic cannot silently become measured. Matches
`metafield-engine/docs/FOUNDATION.md`.

## 7. Replay is the debugger

Record FieldTick 10491, 10492, 10493… plus the observations that
produced them. A physical failure becomes:

> Given this exact sequence of observations, this system produced a
> divergent state at tick 18,442.

Not: "the ESP32 did something weird."

## 8. Logical field time ≠ wall-clock time

```
FieldEpoch
FieldSequence
NodeSequence
ObservationSequence
```

Physical timestamps stay metadata. Canonical order is deterministic.
Eight cheap C3s behave like one distributed instrument.

Already foreshadowed by `c3-field-swarm` tests:
`test_determinism`, `test_election`, `test_join`, `test_field`,
`test_protocol`.

## 9. Demo is a room, not a Minecraft world

Six ESP32-C3s, photodiodes, LEDs, temperature, accelerometers,
microphones, maybe ultrasonics. MetaField reconstructs a continuously
evolving field. The renderer is a viewer of the field, not the owner
of the universe.

`examples/room_loop.py` is the software stand-in for that room.

## 10. Tear down synthetic blocks, keep addressing

Do not delete spatial discretization.
Delete `space = Minecraft cubes`.

```
Space
 └── substrate
      └── cells          (addressing primitive)
           └── channels
                └── values
                     └── provenance
```

A cell may be simulated, physically measured, occupied by hardware,
empty, continuous or quantized, virtual, or experimentally calibrated.

The Minecraft-esque frontend, if it ever exists, is one visualization
of the substrate. The same engine can drive a game, a physics
experiment, an optical instrument, a robot swarm, a sensor network,
or a physical installation.
