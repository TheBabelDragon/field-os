from __future__ import annotations

from collections import defaultdict

from .types import CONSERVED, DECAYING, DIFFUSING, FieldDelta, OPTICAL_PREFIX, SourceClass


def _family(channel: str) -> str:
    return channel.split(".", 1)[0]


def audit_tick(
    deltas: list[FieldDelta],
    allow_information_create: bool = False,
) -> list[str]:
    """Return audit findings. Empty list means the tick looks legal.

    Conservation is an audit, not an automatic rollback.
    """
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
                findings.append(f"conflict {cell}/{channel} writers={','.join(writers)}")

    for channel, group in by_channel.items():
        family = _family(channel)
        net = sum(d.new - d.old for d in group)

        if channel.startswith(OPTICAL_PREFIX):
            continue

        if family in CONSERVED or channel in CONSERVED:
            if abs(net) > 1e-6:
                findings.append(f"conservation {channel} net={net:.6g}")

        if family in DECAYING or channel in DECAYING:
            created = [
                d
                for d in group
                if d.new > d.old
                and d.provenance.cls in (SourceClass.SYNTHETIC, SourceClass.UNKNOWN)
            ]
            if created and net > 1e-6 and not allow_information_create:
                findings.append(f"information-from-nowhere {channel} net={net:.6g}")

        if family in DIFFUSING or channel in DIFFUSING:
            physical = any(d.provenance.is_physical for d in group)
            olds = [d.old for d in group]
            news = [d.new for d in group]
            if len(olds) >= 2 and not physical:
                old_var = _variance(olds)
                new_var = _variance(news)
                if new_var > old_var + 1e-9:
                    findings.append(f"temperature-variance-up {channel}")

    return findings


def _variance(values: list[float]) -> float:
    n = len(values)
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n
