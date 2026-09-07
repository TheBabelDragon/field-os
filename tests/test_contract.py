from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fieldos import (
    BYLIGHT_CHANNELS,
    CONTRACT_VERSION,
    BylightSample,
    FieldDelta,
    FieldKernel,
    FieldTick,
    Location,
    Observation,
    Provenance,
    ReplayLog,
    SourceClass,
    bylight_observations,
    from_phy,
    replay,
    validate_bylight_bundle,
    validate_observation,
)
from fieldos.conservation import audit_tick


def obs(node, channel, value, cls, seq=1, instrument="fixture", source="test", system=""):
    return Observation(
        field=channel,
        channel=channel,
        value=value,
        provenance=Provenance(cls=cls, source=source, node_id=node, instrument=instrument, system=system),
        location=Location(kind="node", id=node),
        node_id=node,
        field_epoch=0,
        field_sequence=seq,
        sequence=seq,
    )


class TestSchemasLocked(unittest.TestCase):
    def test_contract_version(self):
        self.assertEqual(CONTRACT_VERSION, "0.1")
        self.assertEqual(Path("VERSION").read_text().strip(), "0.1")

    def test_schema_files_exist(self):
        for name in (
            "observation.schema.json",
            "field_delta.schema.json",
            "field_tick.schema.json",
            "provenance.schema.json",
            "location.schema.json",
            "field_time.schema.json",
        ):
            data = json.loads((Path("schema") / name).read_text())
            self.assertFalse(data.get("additionalProperties", True))


class TestAdmission(unittest.TestCase):
    def test_observation_becomes_delta(self):
        tick = FieldKernel(allow_synthetic=False).ingest([obs("c3-01", "temperature", 21.5, SourceClass.PHYSICAL)])
        self.assertEqual(tick.deltas[0].old, 0.0)
        self.assertEqual(tick.deltas[0].new, 21.5)
        self.assertTrue(tick.deltas[0].provenance.is_physical)

    def test_invalid_nan_rejected(self):
        bad = obs("c3-01", "temperature", math.nan, SourceClass.PHYSICAL)
        self.assertEqual(validate_observation(bad), "non-finite-value")
        tick = FieldKernel(allow_synthetic=False).ingest([bad])
        self.assertEqual(tick.deltas, [])
        self.assertTrue(any("non-finite-value" in r for r in tick.rejected))

    def test_missing_field_rejected(self):
        bad = Observation(field="", value=1.0, provenance=Provenance(SourceClass.PHYSICAL, instrument="x", node_id="n"))
        tick = FieldKernel(allow_synthetic=False).ingest([bad])
        self.assertTrue(any("missing-field" in r for r in tick.rejected))

    def test_physical_without_instrument_rejected(self):
        orphan = Observation(field="temperature", value=20.0, provenance=Provenance(cls=SourceClass.PHYSICAL))
        tick = FieldKernel(allow_synthetic=False).ingest([orphan])
        self.assertTrue(any("physical-missing-instrument" in r for r in tick.rejected))


class TestOrdering(unittest.TestCase):
    def test_deltas_sorted_deterministically(self):
        tick = FieldKernel(allow_synthetic=False).ingest([
            obs("c3-02", "temperature", 2.0, SourceClass.PHYSICAL, seq=2),
            obs("c3-01", "energy", 1.0, SourceClass.PHYSICAL, seq=1),
            obs("c3-01", "temperature", 3.0, SourceClass.PHYSICAL, seq=3),
        ])
        self.assertEqual([d.sort_key() for d in tick.deltas], sorted(d.sort_key() for d in tick.deltas))
        self.assertEqual([(d.cell, d.channel) for d in tick.deltas], [("c3-01", "energy"), ("c3-01", "temperature"), ("c3-02", "temperature")])

    def test_ingest_order_does_not_change_hash(self):
        def run(order):
            k = FieldKernel(allow_synthetic=False)
            k.ingest([obs(n, "temperature", v, SourceClass.PHYSICAL) for n, v in order])
            return k.hash_state()
        self.assertEqual(run([("c3-02", 2.0), ("c3-01", 1.0), ("c3-03", 3.0)]), run([("c3-03", 3.0), ("c3-01", 1.0), ("c3-02", 2.0)]))


class TestProvenance(unittest.TestCase):
    def test_unlabeled_is_synthetic_and_rejected(self):
        tick = FieldKernel(allow_synthetic=False).ingest([obs("n1", "temperature", 20.0, SourceClass.UNKNOWN)])
        self.assertEqual(tick.deltas, [])
        self.assertTrue(any("synthetic-not-allowed" in r for r in tick.rejected))

    def test_synthetic_cannot_become_or_overwrite_physical(self):
        k = FieldKernel(allow_synthetic=True)
        k.ingest([obs("n1", "energy", 1.0, SourceClass.SYNTHETIC)])
        forged = Observation(
            field="energy", value=2.0,
            provenance=Provenance(cls=SourceClass.PHYSICAL, source="lie", instrument="sht31", node_id="n1", original_class=SourceClass.SYNTHETIC),
            node_id="n1",
        )
        tick = k.ingest([forged])
        self.assertTrue(any("synthetic-cannot-become-physical" in r for r in tick.rejected))
        self.assertEqual(k.get("n1", "energy"), 1.0)
        k2 = FieldKernel(allow_synthetic=True)
        k2.ingest([obs("n1", "temperature", 19.0, SourceClass.PHYSICAL)])
        tick2 = k2.ingest([obs("n1", "temperature", 99.0, SourceClass.SYNTHETIC)])
        self.assertEqual(k2.get("n1", "temperature"), 19.0)
        self.assertTrue(any("synthetic-cannot-overwrite-physical" in r for r in tick2.rejected))

    def test_replayed_is_not_physical(self):
        replayed = Provenance(SourceClass.PHYSICAL, source="sensor", instrument="sht31", node_id="n1").as_replayed()
        self.assertEqual(replayed.cls, SourceClass.REPLAYED)
        self.assertEqual(replayed.origin, SourceClass.PHYSICAL)
        self.assertFalse(replayed.is_physical)


class TestReplay(unittest.TestCase):
    def test_tick_replay_and_json_roundtrip(self):
        k = FieldKernel(allow_synthetic=False)
        for seq, temp in enumerate((21.0, 22.5, 23.0), start=1):
            k.ingest([obs("c3-01", "temperature", temp, SourceClass.PHYSICAL, seq=seq)])
        log = ReplayLog.capture(k)
        replayed, diffs = replay(log)
        self.assertEqual(diffs, [])
        self.assertEqual(replayed.hash_state(), k.hash_state())
        blob = json.dumps(log.to_dict())
        replayed2, diffs2 = replay(ReplayLog.from_dict(json.loads(blob)))
        self.assertEqual(diffs2, [])
        self.assertEqual(replayed2.hash_state(), k.hash_state())
        self.assertEqual(replayed.provenance[("c3-01", "temperature")].cls, SourceClass.REPLAYED)
        self.assertEqual(replayed.provenance[("c3-01", "temperature")].origin, SourceClass.PHYSICAL)


class TestConservation(unittest.TestCase):
    def test_energy_and_information_and_optical(self):
        ok = [
            FieldDelta("a", "energy", 0, 1, Provenance(SourceClass.DERIVED, system="xfer"), source="xfer"),
            FieldDelta("b", "energy", 1, 0, Provenance(SourceClass.DERIVED, system="xfer"), source="xfer"),
        ]
        self.assertEqual(audit_tick(ok), [])
        created = [FieldDelta("a", "energy", 0, 4, Provenance(SourceClass.SYNTHETIC, system="magic"), source="magic")]
        self.assertTrue(any(f.startswith("conservation energy") for f in audit_tick(created)))
        info = [FieldDelta("a", "information", 0, 3, Provenance(SourceClass.SYNTHETIC, system="dream"), source="dream")]
        self.assertTrue(any(f.startswith("information-from-nowhere") for f in audit_tick(info)))
        optical = [FieldDelta("link", "optical.signal", 1, 0.2, Provenance(SourceClass.PHYSICAL, instrument="pd"), source="phy")]
        self.assertEqual(audit_tick(optical), [])
        diff = [
            FieldDelta("a", "temperature", 10, 12, Provenance(SourceClass.DERIVED, system="diffusion"), source="diffusion"),
            FieldDelta("b", "temperature", 20, 18, Provenance(SourceClass.DERIVED, system="diffusion"), source="diffusion"),
        ]
        self.assertEqual(audit_tick(diff), [])


class TestBylight(unittest.TestCase):
    def test_phy_enters_kernel(self):
        sample = BylightSample(node_id="c3-03", peer_id="c3-04", signal=0.8, noise=0.1, lock=1.0, dropout=0.0)
        bundle = bylight_observations(sample)
        self.assertEqual(validate_bylight_bundle(bundle), None)
        self.assertEqual({o.channel_name for o in bundle}, set(BYLIGHT_CHANNELS))
        k = FieldKernel(allow_synthetic=False)
        tick = k.ingest(bundle)
        self.assertGreaterEqual(len(tick.deltas), len(BYLIGHT_CHANNELS))
        self.assertEqual(k.get("c3-03", "optical.signal"), 0.8)
        self.assertEqual(k.provenance[("c3-03", "optical.snr")].source, "bylight_phy")
        sample2 = from_phy({"node_id": "c3-01", "peer_id": "c3-02", "signal": 0.4, "noise": 0.2, "lock": 1.0, "dropout": 0.0})
        k2 = FieldKernel(allow_synthetic=False)
        k2.ingest(bylight_observations(sample2))
        self.assertAlmostEqual(k2.get("c3-01", "optical.snr"), 2.0)


class TestTickContract(unittest.TestCase):
    def test_tick_carries_contract_version(self):
        tick = FieldKernel(allow_synthetic=False).ingest([obs("c3-01", "temperature", 1.0, SourceClass.PHYSICAL)])
        self.assertEqual(tick.contract, "0.1")
        self.assertEqual(FieldTick.from_dict(tick.to_dict()).state_hash, tick.state_hash)


if __name__ == "__main__":
    unittest.main()
