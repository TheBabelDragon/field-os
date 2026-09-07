from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fieldos import (
    FieldKernel,
    FieldTick,
    Location,
    Observation,
    Provenance,
    ReplayLog,
    SourceClass,
    committed_state_hash,
    replay,
)


def obs(node, channel, value, cls, seq=1):
    return Observation(
        field=channel,
        channel=channel,
        value=value,
        provenance=Provenance(cls=cls, source="test", node_id=node, instrument="fixture"),
        location=Location(kind="node", id=node),
        node_id=node,
        sequence=seq,
        field_sequence=seq,
    )


class TestStateHash(unittest.TestCase):
    def test_hash_is_committed_state_not_tick_json(self):
        k = FieldKernel(allow_synthetic=False)
        tick = k.ingest([obs("c3-01", "temperature", 21.5, SourceClass.PHYSICAL)])
        self.assertEqual(tick.state_hash, committed_state_hash(k.state))
        self.assertEqual(len(tick.state_hash), 16)

    def test_json_roundtrip_replay_same_hash(self):
        k = FieldKernel(allow_synthetic=False)
        k.ingest([obs("c3-01", "temperature", 21.0, SourceClass.PHYSICAL, seq=1)])
        k.ingest([obs("c3-01", "temperature", 22.5, SourceClass.PHYSICAL, seq=2)])
        a = [t.state_hash for t in k.log]
        blob = json.dumps(ReplayLog.capture(k).to_dict())
        replayed, diffs = replay(ReplayLog.from_dict(json.loads(blob)))
        self.assertEqual(diffs, [])
        self.assertEqual([t.state_hash for t in replayed.log], a)

    def test_irrelevant_json_key_order_and_delta_order(self):
        k = FieldKernel(allow_synthetic=False)
        tick = k.ingest([
            obs("c3-02", "temperature", 2.0, SourceClass.PHYSICAL, seq=2),
            obs("c3-01", "temperature", 1.0, SourceClass.PHYSICAL, seq=1),
        ])
        parsed = json.loads(json.dumps(tick.to_dict()))
        scrambled = {
            "rejected": parsed["rejected"],
            "audits": parsed["audits"],
            "dt": parsed["dt"],
            "state_hash": parsed["state_hash"],
            "deltas": list(reversed(parsed["deltas"])),
            "sequence": parsed["sequence"],
            "epoch": parsed["epoch"],
            "contract": parsed["contract"],
        }
        restored = FieldTick.from_dict(scrambled)
        got = FieldKernel(allow_synthetic=False).tick(restored.deltas, dt=restored.dt)
        self.assertEqual(got.state_hash, tick.state_hash)

    def test_rejected_and_provenance_are_not_state(self):
        good = obs("c3-01", "temperature", 18.0, SourceClass.PHYSICAL)
        bad = obs("c3-01", "temperature", math.nan, SourceClass.PHYSICAL)
        mixed = FieldKernel(allow_synthetic=False)
        mixed.ingest([good, bad])
        clean = FieldKernel(allow_synthetic=False)
        clean.ingest([good])
        self.assertEqual(mixed.hash_state(), clean.hash_state())
        self.assertTrue(mixed.log[-1].rejected)
        physical = FieldKernel(allow_synthetic=False)
        physical.ingest([obs("n1", "temperature", 21.0, SourceClass.PHYSICAL)])
        synthetic = FieldKernel(allow_synthetic=True)
        synthetic.ingest([obs("n1", "temperature", 21.0, SourceClass.SYNTHETIC)])
        self.assertEqual(physical.hash_state(), synthetic.hash_state())

    def test_committed_value_change_breaks_hash(self):
        a = FieldKernel(allow_synthetic=False)
        a.ingest([obs("c3-01", "temperature", 21.0, SourceClass.PHYSICAL)])
        b = FieldKernel(allow_synthetic=False)
        b.ingest([obs("c3-01", "temperature", 21.1, SourceClass.PHYSICAL)])
        self.assertNotEqual(a.hash_state(), b.hash_state())


if __name__ == "__main__":
    unittest.main()
