# Stack map

```
                    ┌───────────────────────────┐
                    │  viewers / HUD / room    │
                    │  metafield-engine/renderer
                    └────────────┬─────────────┘
                                 │ observes
                    ┌───────────┬─────────────┐
                    │         field-os         │
                    │  Observation / FieldDelta│
                    │  Provenance / FieldTick  │
                    │  conservation / replay   │
                    └──────┬─────────────┬─────┘
           host substrate  │             │  edge substrate
    ┌──────────────────────┬──┘     ┌────┬───────────────────────┐
    │    metafield-engine     │     │     c3-field-swarm       │
    │ kernel, VoxelField, ECS │     │ FieldView → FieldDelta   │
    │ CSI ingest, world hash  │     │ swarm time, election     │
    └────────────┬────────────┘     │ bylight_phy analog       │
                 │                  └────────────┬─────────────┘
                 │                               │
         wifi-sensing-system              ESP-NOW + optical PHY
         optical-body-s3                  six C3 Super Mini
         echo-grid-ultrasonic-os
         field-bus / CAN-FD
```

## Boundary rules

- `field-os` does not flash firmware and does not own voxels.
- `c3-field-swarm` does not implement CAN-FD or the host world kernel.
- `metafield-engine` does not own ESP-NOW membership.
- Bridges translate. They do not invent a third state language.

The missing piece called out in `c3-field-swarm/docs/METAFIELD_BRIDGE.md`
should speak *this* schema, not an ad-hoc JSONL dump.
