from __future__ import annotations

import hashlib
import json
import os
from typing import Iterable

from .conservation import audit_tick
from .types import FieldDelta, FieldTick, Observation, Provenance, SourceClass


def _synthetic_allowed() -> bool:
    flag = os.getenv("FIELD_OS_ALLOW_SYNTHETIC") or os.getenv("METAFIELD_ALLOW_SYNTHETIC")
    return bool(flag) and flag not in ("0", "false", "False")


class FieldKernel:
    """Host reference: cells x channels -> values, with provenance and a log."""

    def __init__(self, allow_synthetic: bool | None = None) -> None:
        self.state: dict[tuple[str, str], float] = {}
        self.provenance: dict[tuple[str, str], Provenance] = {}
        self.epoch = 0
        self.sequence = 0
        self.log: list[FieldTick] = []
        self.observations: list[Observation] = []
        self.allow_synthetic = (
            _synthetic_allowed() if allow_synthetic is None else allow_synthetic
        )

    def get(self, cell: str, channel: str) -> float:
        return self.state.get((cell, channel), 0.0)

    def admit(self, obs: Observation) -> FieldDelta | None:
        """Turn one observation into a FieldDelta. Reject illegal synthetic."""
        if obs.provenance.is_synthetic and not self.allow_synthetic:
            return None
        cell = obs.node_id or obs.location.key()
        channel = obs.channel_name
        old = self.get(cell, channel)
        delta = FieldDelta(
            cell=cell,
            channel=channel,
            old=old,
            new=float(obs.value),
            provenance=obs.provenance,
            source=obs.provenance.source or obs.node_id,
            sequence=obs.sequence,
            tick=self.sequence + 1,
            confidence=obs.confidence,
        )
        self.observations.append(obs)
        return delta

    def tick(self, deltas: Iterable[FieldDelta], dt: float = 0.0) -> FieldTick:
        items = [d for d in deltas if d.old != d.new]
        items.sort(key=lambda d: d.sort_key())
        self.sequence += 1
        applied: list[FieldDelta] = []
        for d in items:
            if d.provenance.is_synthetic and not self.allow_synthetic:
                continue
            key = (d.cell, d.channel)
            current = self.get(d.cell, d.channel)
            live = FieldDelta(
                cell=d.cell,
                channel=d.channel,
                old=current,
                new=d.new,
                provenance=d.provenance,
                source=d.source,
                sequence=d.sequence,
                tick=self.sequence,
                confidence=d.confidence,
            )
            self.state[key] = live.new
            self.provenance[key] = live.provenance
            applied.append(live)
        audits = audit_tick(applied)
        record = FieldTick(
            epoch=self.epoch,
            sequence=self.sequence,
            deltas=applied,
            dt=dt,
            audits=audits,
        )
        record.state_hash = self.hash_state()
        self.log.append(record)
        return record

    def ingest(self, observations: Iterable[Observation], dt: float = 0.0) -> FieldTick:
        deltas = []
        for obs in observations:
            d = self.admit(obs)
            if d is not None:
                deltas.append(d)
        return self.tick(deltas, dt=dt)

    def hash_state(self) -> str:
        items = sorted(
            (cell, channel, f"{value:.9g}")
            for (cell, channel), value in self.state.items()
        )
        blob = json.dumps(items, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]

    def snapshot(self) -> dict[str, float]:
        return {f"{c}/{ch}": v for (c, ch), v in sorted(self.state.items())}
