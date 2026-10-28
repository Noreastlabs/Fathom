import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level010_local_shard as shard


class Level10LocalShardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = shard.derive()
        cls.packages = tuple(shard.l8tool.read(shard.ROOT, path / "package.json")
                             for path in (shard.l8tool.BASE, shard.l8tool.L7, shard.L8))
        cls.registries = tuple(shard.l8tool.read(shard.ROOT, path / "identity-registry.json")
                              for path in (shard.l8tool.BASE, shard.l8tool.L7, shard.L8))

    def test_exact_108_case_projection_and_mode_landings(self):
        proposal = shard.l8tool.read(shard.ROOT, shard.PROPOSAL / "field-proposal.json")
        pkg = self.output["package.json"]
        self.assertEqual(shard.floors(*self.registries),
                         {"module": 912, "item": 912, "variant": 6082})
        self.assertEqual(len(pkg["records"]), 108)
        for index, (source_case, record) in enumerate(zip(proposal["records"], pkg["records"], strict=True)):
            expected = copy.deepcopy(source_case["schema1_fields"])
            item = f"fg:item:{912 + index:06d}"
            expected.update(id=item, module_id=f"fg:module:{912 + index:06d}",
                            workbook_id="fg:workbook:000010", lineage={"kind": "new"})
            for ordinal, event in enumerate(expected["events"], 1):
                event["event_id"] = f"{item}:event:{ordinal:04d}"
            for vi, (variant, membership) in enumerate(zip(expected["variants"], source_case["variant_memberships"], strict=True)):
                variant["id"] = f"fg:variant:{6082 + index * 8 + vi:06d}"
                variant["event_ids"] = [expected["events"][ordinal - 1]["event_id"]
                                        for ordinal in membership["event_local_ordinals"]]
                self.assertEqual(len(variant["event_ids"]), 24)
                self.assertEqual(self.output["local-summary.json"]["source_map"][index]
                                 ["variant_landing_event_ids"][variant["label"]],
                                 [expected["events"][ordinal - 1]["event_id"]
                                  for ordinal in membership["landing_event_local_ordinals"]])
            self.assertEqual([m["landing_event_local_ordinals"][0]
                              for m in source_case["variant_memberships"]],
                             [4, 4, 28, 28, 50, 50, 74, 74])
            self.assertEqual(record, expected)
        shard.check_global(self.output, self.packages, self.registries)

    def test_native_local_report_and_nonadmission(self):
        report = shard.verify_native(shard.ROOT, self.output)
        self.assertTrue(report["valid_reference"])
        self.assertFalse(report["curriculum_playback_authorized"])
        self.assertEqual(report["coverage"]["events"], 10368)
        self.assertFalse(self.output["local-summary.json"]["aggregate_complete"])

    def test_used_and_reserved_identity_refused(self):
        wrong = copy.deepcopy(self.output)
        wrong["identity-registry.json"]["entities"][2]["id"] = self.registries[2]["entities"][2]["id"]
        with self.assertRaisesRegex(shard.ShardError, "GLOBAL_ENTITY_COLLISION"):
            shard.check_global(wrong, self.packages, self.registries)
        wrong = copy.deepcopy(self.output)
        wrong["identity-registry.json"]["entities"][2]["id"] = "fg:module:000552"
        with self.assertRaisesRegex(shard.ShardError, "GLOBAL_ID_ORDER module"):
            shard.check_global(wrong, self.packages, self.registries)

    def test_timing_and_admission_refused(self):
        wrong = copy.deepcopy(self.output)
        wrong["package.json"]["records"][0]["events"][0]["duration_q"] = [1, 2]
        with self.assertRaisesRegex(shard.ShardError, "LINEAGE_OR_TIMING"):
            shard.check_global(wrong, self.packages, self.registries)
        wrong = copy.deepcopy(self.output)
        wrong["package.json"]["records"][0]["runtime_eligible"] = True
        with self.assertRaisesRegex(shard.ShardError, "LINEAGE_OR_TIMING"):
            shard.check_global(wrong, self.packages, self.registries)

    def test_source_and_native_binding_refused(self):
        proposal = shard.l8tool.read(shard.ROOT, shard.PROPOSAL / "field-proposal.json")
        proposal["records"][0]["schema1_fields"]["events"][0]["fret"] = 12
        with self.assertRaisesRegex(shard.ShardError, "SOURCE_PROPOSAL_DRIFT"):
            shard.derive(proposal_override=proposal)
        native = shard.l8tool.read(shard.ROOT, shard.OUT / "native-report.json")
        native["package_sha256"] = "0" * 64
        original_read = shard.l8tool.read
        def swapped(root, path):
            return native if path == shard.OUT / "native-report.json" else original_read(root, path)
        with patch.object(shard.l8tool, "read", side_effect=swapped):
            with self.assertRaisesRegex(shard.ShardError, "NATIVE_INPUT_BINDING"):
                shard.verify_native(shard.ROOT, self.output)

    def test_pin_refusal(self):
        with patch.dict(shard.PINS, {shard.L8 / "package.json": "0" * 64}):
            with self.assertRaisesRegex(shard.ShardError, "INPUT_PIN_DRIFT"):
                shard.pin(shard.ROOT)


if __name__ == "__main__":
    unittest.main()
