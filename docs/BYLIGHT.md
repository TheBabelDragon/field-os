# bylight as a field

`c3-field-swarm/bylight_phy` already exposes analog nodes
(`RX_ANA`, `VREF`, `CMP_OUT`, LED anode/cathode, drain) and measured
idle / illuminated / ambient voltages.

Treat that analog reality as channels, not as a link-layer success bit.

## Suggested channels

```
optical.signal
optical.noise
optical.snr
optical.edge
optical.lock
optical.dropout
optical.confidence
optical.ambient
optical.saturation
optical.pulse_width
```

Plus the reverse path: a FieldDelta on `optical.drive` becomes LED /
laser / modulator output.

## Closed loop

```
Field state
    → field actuator
    → LED / laser / modulator
    → physical optical field
    → photodiode
    → analog waveform
    → Observation {optical.*}
    → FieldDelta
    → Field state
```

A node can say "I can see node 4, but SNR is collapsing" and the swarm
can act on `optical.confidence` the same way it acts on temperature.

Do not hide dropout behind a perfect digital interface.
The PHY *is* a field.
