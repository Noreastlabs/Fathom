import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level013_local_shard as shard


class Level13LocalShardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = shard.derive()
        _, cls.packages, cls.registries, _ = shard.predecessors(shard.ROOT)

    def test_exact_source_field_projection_and_turn(self):
        proposal = shard.read(shard.ROOT, shard.PROPOSAL / "field-proposal.json")
        package = self.output["package.json"]
        self.assertEqual(shard.floors(self.registries),
                         {"module": 1128, "item": 1128, "variant": 7378})
        self.assertEqual(len(package["records"]), 13)
        for index, (source_case, record) in enumerate(zip(proposal["records"], package["records"], strict=True)):
            expected = copy.deepcopy(source_case["schema1_fields"])
            item = f"fg:item:{1128 + index:06d}"
            expected.update(id=item, module_id=f"fg:module:{1128 + index:06d}",
                            workbook_id="fg:workbook:000013", content_revision=1,
                            lineage={"kind": "new"})
            for ordinal, event in enumerate(expected["events"], 1):
                event["event_id"] = f"{item}:event:{ordinal:04d}"
            for vi, (variant, membership) in enumerate(zip(expected["variants"], source_case["variant_memberships"], strict=True)):
                variant["id"] = f"fg:variant:{7378 + index * 2 + vi:06d}"
                variant["event_ids"] = [expected["events"][n - 1]["event_id"]
                                        for n in membership["event_local_ordinals"]]
                self.assertEqual(self.output["local-summary.json"]["source_map"][index]
                                 ["variant_turn_event_ids"][variant["label"]],
                                 [expected["events"][14]["event_id"], expected["events"][15]["event_id"]])
            self.assertEqual(record, expected)
        shard.check_global(self.output, self.packages, self.registries)

    def test_route_native_local_reference_and_nonadmission(self):
        report = shard.verify_native(shard.ROOT, self.output)
        self.assertTrue(report["valid_reference"])
        self.assertFalse(report["curriculum_playback_authorized"])
        self.assertEqual(report["coverage"]["events"], 390)
        summary = self.output["local-summary.json"]
        self.assertEqual(len(summary["routes"]["continuous_round_trip"]), 25)
        self.assertEqual(summary["routes"]["continuous_round_trip"].count("L13-rung13"), 1)
        self.assertFalse(summary["aggregate_complete"])

    def test_predecessor_and_reserved_collision_refused(self):
        wrong = copy.deepcopy(self.output)
        wrong["identity-registry.json"]["entities"][2]["id"] = self.registries[-1]["entities"][2]["id"]
        with self.assertRaisesRegex(shard.ShardError, "GLOBAL_ENTITY_COLLISION"):
            shard.check_global(wrong, self.packages, self.registries)
        wrong = copy.deepcopy(self.output)
        wrong["identity-registry.json"]["entities"][2]["id"] = "fg:module:000552"
        with self.assertRaisesRegex(shard.ShardError, "GLOBAL_ID_ORDER module"):
            shard.check_global(wrong, self.packages, self.registries)
        wrong = copy.deepcopy(self.output)
        wrong["package.json"]["sources"][next(iter(wrong["package.json"]["sources"]))] = 0
        old_ref = next(iter(self.packages[-1]["sources"]))
        wrong["package.json"]["sources"][old_ref] = 0
        with self.assertRaisesRegex(shard.ShardError, "GLOBAL_SOURCE_COLLISION"):
            shard.check_global(wrong, self.packages, self.registries)

    def test_timing_and_runtime_authority_refused(self):
        wrong = copy.deepcopy(self.output)
        wrong["package.json"]["records"][0]["events"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(shard.ShardError, "LINEAGE_OR_TIMING"):
            shard.check_global(wrong, self.packages, self.registries)
        wrong = copy.deepcopy(self.output)
        wrong["package.json"]["records"][0]["runtime_eligible"] = True
        with self.assertRaisesRegex(shard.ShardError, "LINEAGE_OR_TIMING"):
            shard.check_global(wrong, self.packages, self.registries)

    def test_source_and_native_binding_refused(self):
        proposal = shard.read(shard.ROOT, shard.PROPOSAL / "field-proposal.json")
        proposal["records"][0]["schema1_fields"]["events"][0]["fret"] = 12
        with self.assertRaisesRegex(shard.ShardError, "SOURCE_PROPOSAL_DRIFT"):
            shard.derive(proposal_override=proposal)
        native = shard.read(shard.ROOT, shard.OUT / "native-report.json")
        native["package_sha256"] = "0" * 64
        original_read = shard.read
        def swapped(root, path):
            return native if path == shard.OUT / "native-report.json" else original_read(root, path)
        with patch.object(shard, "read", side_effect=swapped):
            with self.assertRaisesRegex(shard.ShardError, "NATIVE_INPUT_BINDING"):
                shard.verify_native(shard.ROOT, self.output)

    def test_input_hash_refusal(self):
        with patch.dict(shard.PINS, {shard.FOUR / "manifest.json": "0" * 64}):
            with self.assertRaisesRegex(shard.ShardError, "INPUT_PIN_DRIFT"):
                shard.pin(shard.ROOT)


if __name__ == "__main__":
    unittest.main()
