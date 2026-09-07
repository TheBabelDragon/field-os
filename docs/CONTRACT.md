# field-os v0.1 — admitted field contract

This is the spine. Not an engine.

```
Observation
    → admission + validation
    → FieldDelta
    → deterministic ordering
    → FieldTick
    → replay
```

Schemas in `schema/` are locked for `0.1`. Changing a required field
or the delta sort key is a contract bump, not a quiet edit.

## Locked objects

- Observation
- FieldDelta
- FieldTick
- Provenance
- Location
- FieldTime (`epoch`, `field_sequence`, `node_sequence`, `observation_sequence`)

Wall-clock `timestamp_ns` is metadata. It does not order a tick.

## Admission

An observation is rejected, never coerced, when:

- `field`/`channel` is missing
- value is non-finite
- uncertainty < 0 or confidence ∉ [0, 1]
- field time is negative
- class is physical but has no instrument, source, or node
- class is unlabeled / unknown (treated as synthetic)
- synthetic is not explicitly allowed
- synthetic would overwrite physical
- synthetic would be relabeled physical

Rejected observations produce no delta. The reason is recorded on the
FieldTick as `rejected`.

## Provenance

| class | meaning |
| --- | --- |
| physical | instrument / sensor / analog PHY |
| derived | computed from admitted values |
| synthetic | simulated; rejected unless allowed |
| remote | arrived from another node |
| replayed | read back from a log |
| unknown | unlabeled = synthetic |

Invariant: synthetic must never silently become physical.
`original_class` survives replay so a physical measurement replayed
from a log is `replayed` with origin `physical`, not a new measurement.

## Ordering

FieldDelta sort key, locked:

```
(cell, channel, source, sequence)
```

Same observations in any arrival order must hash to the same tick.

## state_hash

`state_hash` is a digest of the *committed field state after the tick*,
not a digest of the FieldTick JSON.

```
state_hash = SHA-256(canonical(committed state))[:16]
```

Committed state is the set of `(cell, channel, value)` triples that
survived admission. Canonical form, locked for v0.1:

```json
{"contract":"0.1","state":[["c3-01","temperature","21.5"], ...]}
```

- rows sorted by `(cell, channel)`
- values rendered with `.9g`
- JSON separators `,` and `:`, object keys sorted

Not in the digest:

- FieldTick JSON shape or key order
- `deltas` list order (the kernel re-sorts before apply)
- `rejected`, `audits`, `dt`, `epoch`, `sequence`
- wall-clock timestamps
- provenance metadata
- the previous hash
- the `state_hash` field itself

Invariant:

```
same initial state + same admitted deltas = same state_hash
```

Replay checks that invariant at every tick. Changing a committed value
must change the hash. Changing envelope fields must not.

## Conservation audit

Optional, recorded, not a rollback.

- energy / matter / charge: Σ(new − old) ≈ 0
- information: may decay; may not appear from synthetic nowhere
- temperature: diffusion may not increase variance unless a physical writer is in the tick
- optical.*: lossy on purpose; no conservation

## bylight_phy

A physical optical frame enters only as Observations with
`provenance.source = bylight_phy` and the locked channel set:

```
optical.signal noise snr edge pulse_width ambient saturation dropout lock confidence
```

No `LINK_UP`. Channel quality is the field.

## Non-goals (still)

No ECS, renderer, world, network stack, or scheduler in this repo.
Those stay in `metafield-engine` and `c3-field-swarm`.

## First integration

```
ESP32 / c3-field-swarm
        → real optical observation
        → field-os FieldTick
        → metafield-engine
```
