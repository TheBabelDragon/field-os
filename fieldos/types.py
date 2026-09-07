from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


CONTRACT_VERSION = "0.1"


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
    original_class: Optional[SourceClass] = None

    @property
    def is_synthetic(self) -> bool:
        return self.cls in (SourceClass.SYNTHETIC, SourceClass.UNKNOWN)

    @property
    def is_physical(self) -> bool:
        return self.cls is SourceClass.PHYSICAL

    @property
    def origin(self) -> SourceClass:
        return self.original_class or self.cls

    def as_replayed(self) -> "Provenance":
        origin = self.original_class or self.cls
        if origin is SourceClass.REPLAYED:
            origin = SourceClass.UNKNOWN
        return Provenance(
            cls=SourceClass.REPLAYED,
            source=self.source,
            instrument=self.instrument,
            node_id=self.node_id,
            system=self.system,
            original_class=origin,
        )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "class": self.cls.value,
            "source": self.source,
            "instrument": self.instrument,
            "node_id": self.node_id,
            "system": self.system,
        }
        if self.original_class is not None:
            data["original_class"] = self.original_class.value
        return data

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> "Provenance":
        data = data or {}
        original = data.get("original_class")
        return cls(
            cls=SourceClass.parse(data.get("class")),
            source=str(data.get("source") or ""),
            instrument=str(data.get("instrument") or ""),
            node_id=str(data.get("node_id") or ""),
            system=str(data.get("system") or ""),
            original_class=SourceClass.parse(original) if original else None,
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

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "id": self.id, "x": self.x, "y": self.y, "z": self.z}

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> "Location":
        data = data or {}
        return cls(
            kind=str(data.get("kind") or "cell"),
            id=str(data.get("id") or ""),
            x=data.get("x"),
            y=data.get("y"),
            z=data.get("z"),
        )


@dataclass(frozen=True)
class FieldTime:
    epoch: int = 0
    field_sequence: int = 0
    node_sequence: int = 0
    observation_sequence: int = 0
    timestamp_ns: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "epoch": self.epoch,
            "field_sequence": self.field_sequence,
            "node_sequence": self.node_sequence,
            "observation_sequence": self.observation_sequence,
            "timestamp_ns": self.timestamp_ns,
        }


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
        if self.node_id:
            return self.node_id
        return self.location.key()

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "channel": self.channel_name,
            "location": self.location.to_dict(),
            "value": self.value,
            "unit": self.unit,
            "uncertainty": self.uncertainty,
            "confidence": self.confidence,
            "timestamp_ns": self.timestamp_ns,
            "field_epoch": self.field_epoch,
            "field_sequence": self.field_sequence,
            "node_id": self.node_id,
            "sequence": self.sequence,
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Observation":
        return cls(
            field=str(data.get("field") or ""),
            value=float(data["value"]) if data.get("value") is not None else float("nan"),
            provenance=Provenance.from_dict(data.get("provenance")),
            channel=str(data.get("channel") or ""),
            location=Location.from_dict(data.get("location")),
            unit=str(data.get("unit") or ""),
            uncertainty=float(data.get("uncertainty") or 0.0),
            confidence=float(data["confidence"]) if data.get("confidence") is not None else 1.0,
            timestamp_ns=int(data.get("timestamp_ns") or 0),
            field_epoch=int(data.get("field_epoch") or 0),
            field_sequence=int(data.get("field_sequence") or 0),
            node_id=str(data.get("node_id") or ""),
            sequence=int(data.get("sequence") or 0),
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
        return {
            "cell": self.cell,
            "channel": self.channel,
            "old": self.old,
            "new": self.new,
            "source": self.source,
            "sequence": self.sequence,
            "tick": self.tick,
            "confidence": self.confidence,
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FieldDelta":
        return cls(
            cell=str(data.get("cell") or ""),
            channel=str(data.get("channel") or ""),
            old=float(data.get("old") or 0.0),
            new=float(data["new"]) if data.get("new") is not None else float("nan"),
            provenance=Provenance.from_dict(data.get("provenance")),
            source=str(data.get("source") or ""),
            sequence=int(data.get("sequence") or 0),
            tick=int(data.get("tick") or 0),
            confidence=float(data["confidence"]) if data.get("confidence") is not None else 1.0,
        )


@dataclass
class FieldTick:
    epoch: int
    sequence: int
    deltas: list[FieldDelta]
    dt: float = 0.0
    state_hash: str = ""
    audits: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    contract: str = CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "epoch": self.epoch,
            "sequence": self.sequence,
            "dt": self.dt,
            "state_hash": self.state_hash,
            "audits": list(self.audits),
            "rejected": list(self.rejected),
            "deltas": [d.to_dict() for d in self.deltas],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FieldTick":
        return cls(
            epoch=int(data.get("epoch") or 0),
            sequence=int(data.get("sequence") or 0),
            deltas=[FieldDelta.from_dict(d) for d in data.get("deltas") or []],
            dt=float(data.get("dt") or 0.0),
            state_hash=str(data.get("state_hash") or ""),
            audits=list(data.get("audits") or []),
            rejected=list(data.get("rejected") or []),
            contract=str(data.get("contract") or CONTRACT_VERSION),
        )


CONSERVED = frozenset({"energy", "matter", "charge"})
DECAYING = frozenset({"information"})
DIFFUSING = frozenset({"temperature"})
OPTICAL_PREFIX = "optical."
BYLIGHT_CHANNELS = (
    "optical.signal",
    "optical.noise",
    "optical.snr",
    "optical.edge",
    "optical.pulse_width",
    "optical.ambient",
    "optical.saturation",
    "optical.dropout",
    "optical.lock",
    "optical.confidence",
)
