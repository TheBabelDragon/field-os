from __future__ import annotations

import sys
import unittest
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
from fieldos.conservation import audit_tick
from fieldos.types import FieldDelta


def obs(node: str, channel: str, value: float, cls: SourceClass, seq: int = 1) -> Observation:
    return Observation(
        field=channel,
        channel=channel,
        value=value,
        provenance=Provenance(cls=cls, source="test", node_id=node, instrument="fixture"),
        location=Location(kind="node", id=node),
        node_id=node,
        field_epoch=0,
        field_sequence=seq,
        sequence=seq,
    )


class TestProvenance(unittest.TestCase):
    def test_unlabeled_is_synthetic(self):
        k = FieldKernel(allow_synthetic=False)
        tick = k.ingest([obs("n1", "temperature", 20.0, SourceClass.UNKNOWN)])
        self.assertEqual(tick.deltas, [])
        self.assertEqual(k.get("n1", "temperature"), 0.0)

    def test_physical_is_admitted(self):
        k = FieldKernel(allow_synthetic=False)
        k.ingest([obs("n1", "temperature", 20.5, SourceClass.PHYSICAL)])
        self.assertEqual(k.get("n1", "temperature"), 20.5)
        self.assertTrue(k.provenance[("n1", "temperature")].is_physical)

    def test_synthetic_allowed_flag(self):
        k = FieldKernel(allow_synthetic=True)
        k.ingest([obs("n1", "energy", 1.0, SourceClass.SYNTHETIC)])
        self.assertEqual(k.get("n1", "energy"), 1.0)


class TestConservation(unittest.TestCase):
    def test_energy_must_balance(self):
        deltas = [
            FieldDelta("a", "energy", 0, 1, Provenance(SourceClass.DERIVED, system="xfer"), source="xfer"),
            FieldDelta("b", "energy", 1, 0, Provenance(SourceClass.DERIVED, system="xfer"), source="xfer"),
        ]
        self.assertEqual(audit_tick(deltas), [])

    def test_energy_creation_is_flagged(self):
        deltas = [
            FieldDelta("a", "energy", 0, 4, Provenance(SourceClass.SYNTHETIC, system="magic"), source="magic"),
        ]
        findings = audit_tick(deltas)
        self.assertTrue(any(f.startswith("conservation energy") for f in findings))

    def test_optical_is_lossy_on_purpose(self):
        deltas = [
            FieldDelta("link", "optical.signal", 1, 0.2, Provenance(SourceClass.PHYSICAL), source="phy"),
        ]
        self.assertEqual(audit_tick(deltas), [])


class TestOptical(unittest.TestCase):
    def test_phy_writes_many_channels(self):
        sample = OpticalSample(
            node_id="c3-03",
            peer_id="c3-04",
            signal=0.8,
            noise=0.1,
            lock=1.0,
            dropout=0.0,
        )
        bundle = optical_observations(sample)
        names = {o.channel for o in bundle}
        self.assertIn("optical.snr", names)
        self.assertIn("optical.confidence", names)
        self.assertTrue(all(o.provenance.is_physical for o in bundle))
        k = FieldKernel(allow_synthetic=False)
        k.ingest(bundle)
        self.assertGreater(k.get("c3-03", "optical.confidence"), 0.0)


class TestReplay(unittest.TestCase):
    def test_same_log_same_hash(self):
        k = FieldKernel(allow_synthetic=False)
        for seq, temp in enumerate((21.0, 22.5, 23.0), start=1):
            k.ingest([obs("c3-01", "temperature", temp, SourceClass.PHYSICAL, seq=seq)])
        log = ReplayLog.capture(k)
        replayed, diffs = replay(log)
        self.assertEqual(diffs, [])
        self.assertEqual(replayed.hash_state(), k.hash_state())

    def test_replay_marks_provenance(self):
        k = FieldKernel(allow_synthetic=False)
        k.ingest([obs("c3-01", "temperature", 19.0, SourceClass.PHYSICAL)])
        replayed, diffs = replay(ReplayLog.capture(k))
        self.assertEqual(diffs, [])
        self.assertEqual(
            replayed.provenance[("c3-01", "temperature")].cls,
            SourceClass.REPLAYED,
        )


class TestDeterminism(unittest.TestCase):
    def test_delta_order_does_not_change_hash(self):
        def run(order):
            k = FieldKernel(allow_synthetic=False)
            bundle = [obs(n, "temperature", v, SourceClass.PHYSICAL) for n, v in order]
            k.ingest(bundle)
            return k.hash_state()

        a = run([("c3-02", 2.0), ("c3-01", 1.0), ("c3-03", 3.0)])
        b = run([("c3-03", 3.0), ("c3-01", 1.0), ("c3-02", 2.0)])
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
