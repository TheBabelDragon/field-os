from __future__ import annotations

import hashlib
import json
import os
from typing import Iterable

from .conservation import audit_tick
from .types import CONTRACT_VERSION, FieldDelta, FieldTick, Observation, Provenance
from .validate import may_apply, validate_delta, validate_observation


def _synthetic_allowed() -> bool:
    flag = os.getenv("FIELD_OS_ALLOW_SYNTHETIC") or os.getenv("METAFIELD_ALLOW_SYNTHETIC")
    return bool(flag) and flag not in ("0", "false", "False")


class FieldKernel:
    """Authoritative host reference for the v0.1 admitted-field contract.

    Observation -> admission + validation -> FieldDelta -> deterministic
    ordering -> FieldTick -> replay.
    """

    def __init__(self, allow_synthetic: bool | None = None) -> None:
        self.state: dict[tuple[str, str], float] = {}
        self.provenance: dict[tuple[str, str], Provenance] = {}
        self.epoch = 0
        self.sequence = 0
        self.log: list[FieldTick] = []
        self.observations: list[Observation] = []
        self.rejects: list[str] = []
        self.allow_synthetic = (
            _synthetic_allowed() if allow_synthetic is None else allow_synthetic
        )
        self.contract = CONTRACT_VERSION

    def get(self, cell: str, channel: str) -> float:
        return self.state.get((cell, channel), 0.0)

    def admit(self, obs: Observation) -> FieldDelta | None:
        """Turn one observation into a FieldDelta, or reject it."""
        reason = validate_observation(obs)
        if reason is None:
            reason = may_apply(
                self.provenance.get((obs.cell, obs.channel_name)),
                obs.provenance,
                self.allow_synthetic,
            )
        if reason is not None:
            self.rejects.append(f"{obs.cell}/{obs.channel_name}:{reason}")
            return None
        cell = obs.cell
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
        pending = list(deltas)
        applied: list[FieldDelta] = []
        rejected: list[str] = []

        for d in pending:
            reason = validate_delta(d)
            if reason is None:
                reason = may_apply(
                    self.provenance.get((d.cell, d.channel)),
                    d.provenance,
                    self.allow_synthetic,
                )
            if reason is not None:
                rejected.append(f"{d.cell}/{d.channel}:{reason}")
                continue
            first_touch = (d.cell, d.channel) not in self.state
            if d.old == d.new and not first_touch:
                continue
            applied.append(d)

        applied.sort(key=lambda d: d.sort_key())
        self.sequence += 1
        live_applied: list[FieldDelta] = []
        for d in applied:
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
            self.state[(d.cell, d.channel)] = live.new
            self.provenance[(d.cell, d.channel)] = live.provenance
            live_applied.append(live)

        self.rejects.extend(rejected)
        record = FieldTick(
            epoch=self.epoch,
            sequence=self.sequence,
            deltas=live_applied,
            dt=dt,
            audits=audit_tick(live_applied),
            rejected=rejected,
            contract=self.contract,
        )
        record.state_hash = self.hash_state()
        self.log.append(record)
        return record

    def ingest(self, observations: Iterable[Observation], dt: float = 0.0) -> FieldTick:
        before = len(self.rejects)
        deltas = []
        for obs in observations:
            d = self.admit(obs)
            if d is not None:
                deltas.append(d)
        tick = self.tick(deltas, dt=dt)
        extra = self.rejects[before:]
        if extra:
            seen = set(tick.rejected)
            tick.rejected = extra + [r for r in tick.rejected if r not in seen]
        return tick

    def hash_state(self) -> str:
        items = sorted(
            (cell, channel, f"{value:.9g}")
            for (cell, channel), value in self.state.items()
        )
        blob = json.dumps(
            {"contract": self.contract, "state": items},
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]

    def snapshot(self) -> dict[str, float]:
        return {f"{c}/{ch}": v for (c, ch), v in sorted(self.state.items())}
