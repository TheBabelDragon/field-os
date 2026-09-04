# Conservation

Systems are not arbitrary algorithms with a field-shaped API.
They may declare invariants. The kernel audits `FieldDeltaList`
against those invariants after every tick.

## Built-in policies

| Channel family | Policy |
| --- | --- |
| `energy`, `matter`, `charge` | Σ(new − old) ≈ 0 across the tick |
| `information` | may decay; may not appear from nowhere without a writer |
| `temperature` | no hard conservation; diffusion is allowed |
| `optical.*` | no conservation; analog reality is lossy on purpose |

A policy failure does not automatically roll back.
It is recorded on the tick as an audit finding so replay can show
exactly which system invented energy.

## Why this exists

Then you can ask:

- Did the system conserve energy?
- Did the optical measurement originate from a real sensor?
- Did two systems produce contradictory deltas for the same cell?
- Did a node fabricate an impossible observation?
- Can this world state be replayed exactly?
