from __future__ import annotations

from dataclasses import dataclass

from .types import Location, Observation, Provenance, SourceClass


@dataclass
class OpticalSample:
    """Ugly analog PHY sample. None of these are LINK_UP."""

    node_id: str
    peer_id: str = ""
    signal: float = 0.0
    noise: float = 0.0
    edge_time: float = 0.0
    pulse_width: float = 0.0
    ambient: float = 0.0
    saturation: float = 0.0
    dropout: float = 0.0
    lock: float = 0.0
    field_epoch: int = 0
    field_sequence: int = 0
    sequence: int = 0
    timestamp_ns: int = 0

    @property
    def snr(self) -> float:
        return self.signal / self.noise if self.noise > 0 else 0.0

    @property
    def confidence(self) -> float:
        if self.dropout >= 1.0 or self.saturation >= 1.0:
            return 0.0
        raw = self.lock * (1.0 - self.dropout) * min(self.snr / 10.0, 1.0)
        return max(0.0, min(1.0, raw))


def optical_observations(sample: OpticalSample) -> list[Observation]:
    loc = Location(kind="link", id=f"{sample.node_id}->{sample.peer_id or '*'}")
    prov = Provenance(
        cls=SourceClass.PHYSICAL,
        source="bylight_phy",
        instrument="photodiode",
        node_id=sample.node_id,
    )
    channels = {
        "optical.signal": sample.signal,
        "optical.noise": sample.noise,
        "optical.snr": sample.snr,
        "optical.edge": sample.edge_time,
        "optical.pulse_width": sample.pulse_width,
        "optical.ambient": sample.ambient,
        "optical.saturation": sample.saturation,
        "optical.dropout": sample.dropout,
        "optical.lock": sample.lock,
        "optical.confidence": sample.confidence,
    }
    out = []
    for name, value in channels.items():
        out.append(
            Observation(
                field=name,
                channel=name,
                value=value,
                provenance=prov,
                location=loc,
                node_id=sample.node_id,
                field_epoch=sample.field_epoch,
                field_sequence=sample.field_sequence,
                sequence=sample.sequence,
                timestamp_ns=sample.timestamp_ns,
                confidence=sample.confidence,
                unit="",
            )
        )
    return out
