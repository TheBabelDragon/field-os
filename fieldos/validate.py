from __future__ import annotations

import math
from typing import Optional

from .types import FieldDelta, Observation, Provenance, SourceClass


def finite(value: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def validate_observation(obs: Observation) -> Optional[str]:
    if not obs.field and not obs.channel:
        return "missing-field"
    if not finite(obs.value):
        return "non-finite-value"
    if not finite(obs.uncertainty) or obs.uncertainty < 0:
        return "invalid-uncertainty"
    if not finite(obs.confidence) or obs.confidence < 0 or obs.confidence > 1:
        return "invalid-confidence"
    if obs.field_epoch < 0 or obs.field_sequence < 0 or obs.sequence < 0:
        return "invalid-field-time"
    if obs.timestamp_ns < 0:
        return "invalid-timestamp"
    return validate_provenance(obs.provenance, require_writer=True)


def validate_delta(delta: FieldDelta) -> Optional[str]:
    if not delta.cell:
        return "missing-cell"
    if not delta.channel:
        return "missing-channel"
    if not finite(delta.old) or not finite(delta.new):
        return "non-finite-value"
    if not finite(delta.confidence) or delta.confidence < 0 or delta.confidence > 1:
        return "invalid-confidence"
    if delta.sequence < 0 or delta.tick < 0:
        return "invalid-field-time"
    return validate_provenance(delta.provenance, require_writer=False)


def validate_provenance(prov: Provenance, require_writer: bool) -> Optional[str]:
    if prov.cls is SourceClass.PHYSICAL:
        if not (prov.instrument or prov.source or prov.node_id):
            return "physical-missing-instrument"
    if require_writer and prov.cls is SourceClass.DERIVED and not (prov.system or prov.source):
        return "derived-missing-system"
    return None


def may_apply(
    current: Optional[Provenance],
    incoming: Provenance,
    allow_synthetic: bool,
) -> Optional[str]:
    """Provenance transition rules. Synthetic must never become physical."""
    if incoming.cls is SourceClass.PHYSICAL and incoming.is_synthetic:
        return "class-contradiction"
    if incoming.is_synthetic and not allow_synthetic:
        return "synthetic-not-allowed"
    if incoming.cls is SourceClass.PHYSICAL and incoming.origin is SourceClass.SYNTHETIC:
        return "synthetic-cannot-become-physical"
    if incoming.cls is SourceClass.PHYSICAL and incoming.origin is SourceClass.UNKNOWN:
        return "unlabeled-cannot-become-physical"
    if current is None:
        return None
    if current.is_physical and incoming.is_synthetic:
        return "synthetic-cannot-overwrite-physical"
    if current.is_physical and incoming.cls is SourceClass.REPLAYED:
        return None
    if (
        incoming.cls is SourceClass.PHYSICAL
        and current.origin in (SourceClass.SYNTHETIC, SourceClass.UNKNOWN)
        and incoming.origin in (SourceClass.SYNTHETIC, SourceClass.UNKNOWN)
    ):
        return "synthetic-cannot-become-physical"
    return None
