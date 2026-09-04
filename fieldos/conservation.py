from __future__ import annotations

from collections import defaultdict

from .types import CONSERVED, DECAYING, FieldDelta, OPTICAL_PREFIX


def audit_tick(deltas: list[FieldDelta], allow_information_create: bool = False) -> list[str]:
    """Return audit findings. Empty list means the tick looks legal."""
    findings: list[str] = []
    by_channel: dict[str, list[FieldDelta]] = defaultdict(list)
    by_cell_channel: dict[tuple[str, str], list[FieldDelta]] = defaultdict(list)

    for d in deltas:
        by_channel[d.channel].append(d)
        by_cell_channel[(d.cell, d.channel)].append(d)

    for (cell, channel), group in by_cell_channel.items():
        if len(group) > 1:
            writers = sorted({d.source or d.provenance.system or "?" for d in group})
            if len(writers) > 1:
                findings.append(
                    f"conflict {cell}/{channel} writers={','.join(writers)}"
                )

    for channel, group in by_channel.items():
        family = channel.split(".", 1)[0]
        net = sum(d.new - d.old for d in group)
        if family in CONSERVED or channel in CONSERVED:
            if abs(net) > 1e-6:
                findings.append(f"conservation {channel} net={net:.6g}")
        if (family in DECAYING or channel in DECAYING) and not allow_information_create:
            created = [d for d in group if d.new > d.old and d.provenance.is_synthetic]
            if created and net > 1e-6:
                findings.append(f"information-from-nowhere {channel} net={net:.6g}")
        if channel.startswith(OPTICAL_PREFIX):
            continue

    return findings
