import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel12_level008_local_shard as shard


class Level8LocalShardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = shard.derive()
        cls.base_pkg = shard.read(shard.ROOT, shard.BASE / "package.json")
        cls.base_reg = shard.read(shard.ROOT, shard.BASE / "identity-registry.json")
        cls.base_prof = shard.read(shard.ROOT, shard.BASE / "expected-profile.json")
        cls.l7_pkg = shard.read(shard.ROOT, shard.L7 / "package.json")
        cls.l7_reg = shard.read(shard.ROOT, shard.L7 / "identity-registry.json")
        cls.l7_prof = shard.read(shard.ROOT, shard.L7 / "expected-profile.json")

    def check_global(self, output):
        shard.check_global(output, self.base_pkg, self.base_reg, self.base_prof,
                           self.l7_pkg, self.l7_reg, self.l7_prof)

    def test_whole_source_projection_and_identity_ranges(self):
        proposal = shard.read(shard.ROOT, shard.L8 / "field-proposal.json")
        pkg = self.output["package.json"]
        reg = self.output["identity-registry.json"]
        self.assertEqual(shard.floors(self.base_reg, self.l7_reg),
                         {"module": 804, "item": 804, "variant": 5650})
        self.assertEqual(len(pkg["records"]), 108)
        self.assertEqual(len(reg["entities"]), 650)
        for index, (source_record, record) in enumerate(zip(proposal["records"], pkg["records"], strict=True)):
            expected = copy.deepcopy(source_record["schema1_fields"])
            item = f"fg:item:{804 + index:06d}"
            expected.update(id=item, module_id=f"fg:module:{804 + index:06d}",
                            workbook_id="fg:workbook:000008", lineage={"kind": "new"})
            for ordinal, event in enumerate(expected["events"], 1):
                event["event_id"] = f"{item}:event:{ordinal:04d}"
            for vi, (variant, member) in enumerate(zip(expected["variants"], source_record["variant_memberships"], strict=True)):
                variant["id"] = f"fg:variant:{5650 + index * 4 + vi:06d}"
                variant["event_ids"] = [expected["events"][n - 1]["event_id"] for n in member["event_local_ordinals"]]
            self.assertEqual(record, expected)
        self.check_global(self.output)

    def test_native_report_bound_and_nonadmitted(self):
        report = shard.verify_native(shard.ROOT, self.output)
        self.assertTrue(report["valid_reference"])
        self.assertFalse(report["curriculum_playback_authorized"])
        self.assertEqual(report["coverage"]["events"], 10368)
        self.assertFalse(self.output["local-summary.json"]["aggregate_complete"])

    def test_duplicate_and_reserved_identity_refused(self):
        wrong = copy.deepcopy(self.output)
        wrong["identity-registry.json"]["entities"][2]["id"] = self.l7_reg["entities"][2]["id"]
        with self.assertRaisesRegex(shard.ShardError, "GLOBAL_ENTITY_COLLISION"):
            self.check_global(wrong)
        wrong = copy.deepcopy(self.output)
        wrong["identity-registry.json"]["entities"][2]["id"] = "fg:module:000552"
        with self.assertRaisesRegex(shard.ShardError, "GLOBAL_ID_ORDER module"):
            self.check_global(wrong)

    def test_timing_or_admission_refused(self):
        wrong = copy.deepcopy(self.output)
        wrong["package.json"]["records"][0]["events"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(shard.ShardError, "LINEAGE_OR_TIMING"):
            self.check_global(wrong)
        wrong = copy.deepcopy(self.output)
        wrong["package.json"]["records"][0]["runtime_eligible"] = True
        with self.assertRaisesRegex(shard.ShardError, "LINEAGE_OR_TIMING"):
            self.check_global(wrong)

    def test_source_and_native_report_drift_refused(self):
        proposal = shard.read(shard.ROOT, shard.L8 / "field-proposal.json")
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

    def test_pin_refusal(self):
        with patch.dict(shard.PINS, {shard.L8 / "field-proposal.json": "0" * 64}):
            with self.assertRaisesRegex(shard.ShardError, "INPUT_PIN_DRIFT"):
                shard.pin(shard.ROOT)


if __name__ == "__main__":
    unittest.main()
