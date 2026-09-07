from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .types import BYLIGHT_CHANNELS, Location, Observation, Provenance, SourceClass


@dataclass
class BylightSample:
    """Ugly analog PHY sample. None of these are LINK_UP."""

    node_id: str
    peer_id: str = ""
    signal: float = 0.0
    noise: float = 0.0
    edge: float = 0.0
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

    def channels(self) -> dict[str, float]:
        return {
            "optical.signal": self.signal,
            "optical.noise": self.noise,
            "optical.snr": self.snr,
            "optical.edge": self.edge,
            "optical.pulse_width": self.pulse_width,
            "optical.ambient": self.ambient,
            "optical.saturation": self.saturation,
            "optical.dropout": self.dropout,
            "optical.lock": self.lock,
            "optical.confidence": self.confidence,
        }


def from_phy(frame: dict[str, Any]) -> BylightSample:
    """Accept a raw bylight_phy / analog frame and keep channel quality."""
    node = str(frame.get("node_id") or frame.get("node") or "")
    if not node:
        raise ValueError("bylight-missing-node")
    return BylightSample(
        node_id=node,
        peer_id=str(frame.get("peer_id") or frame.get("peer") or ""),
        signal=float(frame.get("signal") or frame.get("rx_ana_illuminated_v") or 0.0),
        noise=float(frame.get("noise") or 0.0),
        edge=float(frame.get("edge") or frame.get("edge_time") or 0.0),
        pulse_width=float(frame.get("pulse_width") or 0.0),
        ambient=float(frame.get("ambient") or frame.get("rx_ana_idle_v") or 0.0),
        saturation=float(frame.get("saturation") or 0.0),
        dropout=float(frame.get("dropout") or 0.0),
        lock=float(frame.get("lock") if frame.get("lock") is not None else 1.0),
        field_epoch=int(frame.get("field_epoch") or 0),
        field_sequence=int(frame.get("field_sequence") or 0),
        sequence=int(frame.get("sequence") or 0),
        timestamp_ns=int(frame.get("timestamp_ns") or 0),
    )


def bylight_observations(sample: BylightSample) -> list[Observation]:
    loc = Location(kind="link", id=f"{sample.node_id}->{sample.peer_id or '*'}")
    prov = Provenance(
        cls=SourceClass.PHYSICAL,
        source="bylight_phy",
        instrument="photodiode",
        node_id=sample.node_id,
    )
    out = []
    for name, value in sample.channels().items():
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
            )
        )
    return out


def validate_bylight_bundle(observations: list[Observation]) -> Optional[str]:
    names = {o.channel_name for o in observations}
    missing = [c for c in BYLIGHT_CHANNELS if c not in names]
    if missing:
        return "bylight-missing-channels:" + ",".join(missing)
    if not all(o.provenance.is_physical for o in observations):
        return "bylight-not-physical"
    if not all(o.provenance.source == "bylight_phy" for o in observations):
        return "bylight-wrong-source"
    return None


OpticalSample = BylightSample
optical_observations = bylight_observations
