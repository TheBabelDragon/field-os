# Replay

The log is the debugger.

```
LIVE HARDWARE
     ↓
  record observations + FieldTicks
     ↓
  deterministic field log
     ↓
  replay
     ↓
  (optionally) modify one system
     ↓
  compare hashes
```

## Rules

1. Replay consumes the same observation sequence, in field-time order.
2. Wall-clock timestamps are ignored for ordering.
3. `replayed` provenance replaces the original class on the *read path*
   so a replay cannot be mistaken for a fresh measurement.
4. Same observations + same systems + same epoch → same state hash.
5. Divergence is reported as `(tick, cell, channel, expected, actual)`.

`fieldos.replay` implements this for the host reference kernel.
`c3-field-swarm` already has `test_determinism`. The engine kernel
already hashes world state. This repo is the contract those two
should agree on.
