from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .kernel import FieldKernel
from .types import FieldDelta, FieldTick, Observation


@dataclass
class ReplayLog:
    observations: list[Observation] = field(default_factory=list)
    ticks: list[FieldTick] = field(default_factory=list)
    hashes: list[str] = field(default_factory=list)

    @classmethod
    def capture(cls, kernel: FieldKernel) -> "ReplayLog":
        return cls(
            observations=list(kernel.observations),
            ticks=list(kernel.log),
            hashes=[t.state_hash for t in kernel.log],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observations": [o.to_dict() for o in self.observations],
            "ticks": [t.to_dict() for t in self.ticks],
            "hashes": list(self.hashes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReplayLog":
        return cls(
            observations=[Observation.from_dict(o) for o in data.get("observations") or []],
            ticks=[FieldTick.from_dict(t) for t in data.get("ticks") or []],
            hashes=list(data.get("hashes") or []),
        )


def _replayed_delta(d: FieldDelta) -> FieldDelta:
    return FieldDelta(
        cell=d.cell,
        channel=d.channel,
        old=d.old,
        new=d.new,
        provenance=d.provenance.as_replayed(),
        source=d.source,
        sequence=d.sequence,
        tick=d.tick,
        confidence=d.confidence,
    )


def replay(log: ReplayLog, allow_synthetic: bool = True) -> tuple[FieldKernel, list[str]]:
    """Feed recorded FieldTicks back into a fresh kernel.

    Identical ticks must produce identical state_hash values.
    Replayed provenance is never a new physical measurement.
    """
    kernel = FieldKernel(allow_synthetic=allow_synthetic)
    diffs: list[str] = []
    if log.ticks:
        for tick in log.ticks:
            kernel.epoch = tick.epoch
            got = kernel.tick([_replayed_delta(d) for d in tick.deltas], dt=tick.dt)
            if got.state_hash != tick.state_hash:
                diffs.append(
                    f"tick {tick.epoch}.{tick.sequence} hash {got.state_hash} != {tick.state_hash}"
                )
        return kernel, diffs

    ordered = sorted(
        log.observations,
        key=lambda o: (o.field_epoch, o.field_sequence, o.node_id, o.sequence),
    )
    groups: dict[tuple[int, int], list[Observation]] = {}
    for obs in ordered:
        groups.setdefault((obs.field_epoch, obs.field_sequence), []).append(obs)
    expected = list(log.hashes)
    for (epoch, seq), bundle in groups.items():
        kernel.epoch = epoch
        replayed_obs = []
        for obs in bundle:
            replayed_obs.append(
                Observation(
                    field=obs.field,
                    value=obs.value,
                    provenance=obs.provenance.as_replayed(),
                    channel=obs.channel,
                    location=obs.location,
                    unit=obs.unit,
                    uncertainty=obs.uncertainty,
                    confidence=obs.confidence,
                    timestamp_ns=obs.timestamp_ns,
                    field_epoch=obs.field_epoch,
                    field_sequence=obs.field_sequence,
                    node_id=obs.node_id,
                    sequence=obs.sequence,
                )
            )
        tick = kernel.ingest(replayed_obs)
        if expected:
            want = expected.pop(0)
            if tick.state_hash != want:
                diffs.append(f"tick {epoch}.{seq} hash {tick.state_hash} != {want}")
    return kernel, diffs
