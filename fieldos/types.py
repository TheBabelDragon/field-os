from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class SourceClass(str, Enum):
    PHYSICAL = "physical"
    DERIVED = "derived"
    SYNTHETIC = "synthetic"
    REMOTE = "remote"
    REPLAYED = "replayed"
    UNKNOWN = "unknown"

    @classmethod
    def parse(cls, raw: Optional[str]) -> "SourceClass":
        if raw is None or raw == "":
            return cls.UNKNOWN
        aliases = {
            "sensor": cls.PHYSICAL,
            "instrument": cls.PHYSICAL,
            "inferred": cls.DERIVED,
            "interpolated": cls.DERIVED,
            "simulated": cls.SYNTHETIC,
            "model": cls.SYNTHETIC,
            "network": cls.REMOTE,
        }
        key = raw.lower()
        if key in aliases:
            return aliases[key]
        try:
            return cls(key)
        except ValueError:
            return cls.UNKNOWN


@dataclass(frozen=True)
class Provenance:
    cls: SourceClass = SourceClass.UNKNOWN
    source: str = ""
    instrument: str = ""
    node_id: str = ""
    system: str = ""

    @property
    def is_synthetic(self) -> bool:
        return self.cls in (SourceClass.SYNTHETIC, SourceClass.UNKNOWN)

    @property
    def is_physical(self) -> bool:
        return self.cls is SourceClass.PHYSICAL

    def as_replayed(self) -> "Provenance":
        return Provenance(
            cls=SourceClass.REPLAYED,
            source=self.source,
            instrument=self.instrument,
            node_id=self.node_id,
            system=self.system,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "class": self.cls.value,
            "source": self.source,
            "instrument": self.instrument,
            "node_id": self.node_id,
            "system": self.system,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> "Provenance":
        data = data or {}
        return cls(
            cls=SourceClass.parse(data.get("class")),
            source=str(data.get("source") or ""),
            instrument=str(data.get("instrument") or ""),
            node_id=str(data.get("node_id") or ""),
            system=str(data.get("system") or ""),
        )


@dataclass(frozen=True)
class Location:
    kind: str = "cell"
    id: str = ""
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None

    def key(self) -> str:
        if self.id:
            return f"{self.kind}:{self.id}"
        coords = ",".join(
            "" if c is None else f"{c:g}" for c in (self.x, self.y, self.z)
        )
        return f"{self.kind}@({coords})"


@dataclass(frozen=True)
class Observation:
    field: str
    value: float
    provenance: Provenance
    channel: str = ""
    location: Location = field(default_factory=Location)
    unit: str = ""
    uncertainty: float = 0.0
    confidence: float = 1.0
    timestamp_ns: int = 0
    field_epoch: int = 0
    field_sequence: int = 0
    node_id: str = ""
    sequence: int = 0

    @property
    def channel_name(self) -> str:
        return self.channel or self.field

    @property
    def cell(self) -> str:
        return self.location.key() if self.location.id or self.location.kind != "cell" else (
            self.node_id or self.location.key()
        )


@dataclass(frozen=True)
class FieldDelta:
    cell: str
    channel: str
    old: float
    new: float
    provenance: Provenance
    source: str = ""
    sequence: int = 0
    tick: int = 0
    confidence: float = 1.0

    def sort_key(self) -> tuple:
        return (self.cell, self.channel, self.source, self.sequence)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["provenance"] = self.provenance.to_dict()
        return d


@dataclass
class FieldTick:
    epoch: int
    sequence: int
    deltas: list[FieldDelta]
    dt: float = 0.0
    state_hash: str = ""
    audits: list[str] = field(default_factory=list)


CONSERVED = frozenset({"energy", "matter", "charge"})
DECAYING = frozenset({"information"})
OPTICAL_PREFIX = "optical."
