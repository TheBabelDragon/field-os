# Vocabulary

Aligned with `metafield-engine/engine/kernel` and
`c3-field-swarm/include/field`.

## Admitted objects

| Object | Role |
| --- | --- |
| **Channel** | Named scalar field (`temperature`, `energy`, `optical.signal`, …) |
| **Cell** | Address. Not an object type. |
| **Observation** | A measurement or claim about a channel at a location. |
| **FieldDelta** | Proposed `(cell, channel, old → new)` written by one source. |
| **FieldView** | Frozen read of state. Systems never write through it. |
| **FieldTick** | One atomic application of a sorted `FieldDeltaList`. |
| **Provenance** | How a value came to exist. |
| **FieldEpoch / FieldSequence** | Canonical distributed time. |
| **Log** | Append-only history of ticks + admitted observations. |

## Source class

| Class | Meaning |
| --- | --- |
| `physical` | Instrument, sensor, analog PHY |
| `derived` | Computed from physical observations |
| `synthetic` | Simulated / modeled. Rejected unless explicitly allowed. |
| `remote` | Arrived over a network from another node |
| `replayed` | Read back from a log; not a new measurement |
| `unknown` | Treated as synthetic |

Unlabeled values are synthetic. That is an invariant, not a default of convenience.

## Clocks

Keep them separate. Mixing them is how distributed instruments die.

| Clock | Used for |
| --- | --- |
| wall / `timestamp_ns` | metadata, human UX, timeout |
| network arrival | never canonical |
| `field_epoch` + `field_sequence` | ordering, replay, determinism |
| `node_sequence` / `observation_sequence` | per-writer uniqueness |

## Every admitted value answers

WHAT? WHERE? WHEN? FROM WHAT? MEASURED OR DERIVED? BY WHOM? WITH WHAT UNCERTAINTY?
