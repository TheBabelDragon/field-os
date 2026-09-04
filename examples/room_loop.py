#!/usr/bin/env python3
"""Software stand-in for the six-node room demo.

Six addresses write thermal + optical fields. Diffusion is a system:
FieldView -> FieldDelta. The renderer would only view the snapshot.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fieldos import (
    FieldKernel,
    Location,
    Observation,
    OpticalSample,
    Provenance,
    ReplayLog,
    SourceClass,
    optical_observations,
    replay,
)
from fieldos.types import FieldDelta


NODES = [f"c3-{i:02d}" for i in range(1, 7)]


def physical_tick(kernel: FieldKernel, seq: int, temps: dict[str, float]) -> None:
    obs = []
    for node, temp in temps.items():
        obs.append(
            Observation(
                field="temperature",
                channel="temperature",
                value=temp,
                provenance=Provenance(
                    cls=SourceClass.PHYSICAL,
                    source="sensor",
                    instrument="sht31",
                    node_id=node,
                ),
                location=Location(kind="node", id=node),
                node_id=node,
                unit="degC",
                uncertainty=0.3,
                field_epoch=0,
                field_sequence=seq,
                sequence=seq,
            )
        )
    sample = OpticalSample(
        node_id="c3-03",
        peer_id="c3-04",
        signal=0.82 - 0.04 * (seq % 5),
        noise=0.05 + 0.01 * (seq % 3),
        lock=1.0 if seq % 7 else 0.0,
        dropout=0.0 if seq % 7 else 1.0,
        ambient=0.12,
        field_epoch=0,
        field_sequence=seq,
        sequence=seq,
    )
    obs.extend(optical_observations(sample))
    kernel.ingest(obs)


def diffuse_temperature(kernel: FieldKernel) -> list[FieldDelta]:
    """System: frozen view -> deltas. Never writes state directly."""
    values = [kernel.get(n, "temperature") for n in NODES]
    mean = sum(values) / len(values)
    deltas = []
    for node, value in zip(NODES, values):
        nxt = value + 0.15 * (mean - value)
        deltas.append(
            FieldDelta(
                cell=node,
                channel="temperature",
                old=value,
                new=nxt,
                provenance=Provenance(
                    cls=SourceClass.DERIVED,
                    source="system",
                    system="diffusion",
                    node_id=node,
                ),
                source="diffusion",
            )
        )
    return deltas


def main() -> None:
    kernel = FieldKernel(allow_synthetic=False)
    temps = {n: 21.0 + i * 0.8 for i, n in enumerate(NODES)}
    for seq in range(1, 9):
        temps["c3-01"] += 0.4
        physical_tick(kernel, seq, temps)
        kernel.tick(diffuse_temperature(kernel))

    print("snapshot")
    for key, value in kernel.snapshot().items():
        print(f"  {key:40s} {value:8.4f}")
    print(f"ticks={kernel.sequence} hash={kernel.hash_state()}")
    last = kernel.log[-1]
    if last.audits:
        print("audits:", "; ".join(last.audits))

    log = ReplayLog.capture(kernel)
    replayed, diffs = replay(log)
    print(f"replay hash={replayed.hash_state()} diffs={len(diffs)}")
    if diffs:
        raise SystemExit("replay diverged:\n" + "\n".join(diffs))
    print("ok")


if __name__ == "__main__":
    main()
