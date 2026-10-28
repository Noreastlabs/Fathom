"""Three genuine shard proof, both Level10 modes and refusal cases."""

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel10_global_shard_verifier as globalv  # noqa: E402
import parallel10_three_real_shard_manifest_r05 as bridge  # noqa: E402


class ThreeRealShardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / bridge.OUT / "manifest.json").read_text())
        cls.summary = bridge.verify_manifest()
        cls.foundation = {role: globalv.load_artifact(ROOT, value)
                          for role, value in cls.manifest["foundation"].items()}
        cls.catalog = cls.foundation["registry"]["workbook_catalog"]
        cls.course = next(e for e in cls.foundation["registry"]["entities"] if e["kind"] == "course")
        cls.checked = []
        for descriptor in cls.manifest["shards"]:
            docs = {role: globalv.load_artifact(ROOT, ref)
                    for role, ref in descriptor["artifacts"].items()}
            cls.checked.append(globalv.check_local(descriptor, docs, cls.catalog, cls.course))

    def test_exact_three_native_shards_and_completion_false(self):
        self.assertEqual(self.summary["validated_workbooks"], [7, 8, 10])
        self.assertEqual(self.summary["shard_count"], 3)
        self.assertEqual(self.summary["new_counts"],
                         {"records": 324, "entities": 2163, "events": 22464,
                          "sources": 473, "variants": 1512})
        self.assertEqual(self.summary["next_allocation_floor"],
                         {"module": 1020, "item": 1020, "variant": 6946})
        self.assertFalse(self.summary["aggregate_complete"])
        self.assertFalse(self.summary["full_105_workbook_source_coverage_verified"])
        self.assertFalse(self.summary["admitted"])
        self.assertFalse(self.summary["runtime_admission"])
        self.assertEqual(globalv.encoded(self.summary),
                         (ROOT / bridge.OUT / "summary.json").read_bytes())
        for descriptor in self.manifest["shards"]:
            report = globalv.load_artifact(ROOT, descriptor["artifacts"]["native_report"])
            self.assertEqual((report["exit_code"], report["valid_reference"]), (2, True))
            self.assertEqual(report["coverage"]["observed_records"], 108)
            self.assertFalse(report["curriculum_playback_authorized"])

    def test_level10_two_mode_source_bridge(self):
        derived = bridge.source_prework()
        for name, obj in derived.items():
            self.assertEqual((ROOT / bridge.OUT / name).read_bytes(), globalv.encoded(obj))
        proposal = derived[bridge.SOURCE_OUTPUTS[0]]
        preallocation = derived[bridge.SOURCE_OUTPUTS[1]]
        completion = derived[bridge.SOURCE_OUTPUTS[2]]
        self.assertEqual(len(proposal["records"]), 108)
        self.assertTrue(all(len(row["mode_refs"]) == 2 for row in proposal["records"]))
        self.assertTrue(all(len(row["all_source_refs"]) == 5
                            for row in preallocation["records"]))
        self.assertEqual(completion["catalog_entry_count"], 105)
        self.assertEqual(completion["foundation_workbook_identity_count"], 16)
        self.assertEqual(completion["whole_source_complete_workbooks"], [])
        self.assertEqual(completion["admitted_workbooks"], [])
        self.assertFalse(completion["release_authority_present"])
        manifest_derived = bridge.manifest_inputs()
        for name, obj in manifest_derived.items():
            self.assertEqual((ROOT / bridge.OUT / name).read_bytes(), globalv.encoded(obj))

    def test_real_pairwise_and_serial_allocation(self):
        checked = self.checked
        for i in range(len(checked)):
            for j in range(i+1, len(checked)):
                a, b = checked[i], checked[j]
                self.assertFalse({e["id"] for e in a["entities"]} &
                                 {e["id"] for e in b["entities"]})
                self.assertFalse(a["record_ids"] & b["record_ids"])
                self.assertFalse(set(a["event_ids"]) & set(b["event_ids"]))
                self.assertFalse(a["source_ids"] & b["source_ids"])
                self.assertFalse(a["source_keys"] & b["source_keys"])
        self.assertEqual(globalv.check_union(self.foundation, checked, self.catalog)
                         ["validated_workbooks"], [7, 8, 10])

    def test_order_duplicate_and_false_completion_refuse(self):
        changed = copy.deepcopy(self.manifest)
        changed["shards"][1:] = list(reversed(changed["shards"][1:]))
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_RESERVED_OR_ORDER"):
            globalv.verify(ROOT, changed)
        changed = copy.deepcopy(self.manifest)
        changed["shards"].append(copy.deepcopy(changed["shards"][2]))
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_DUPLICATE_WORKBOOK"):
            globalv.verify(ROOT, changed)
        changed = copy.deepcopy(self.manifest)
        changed["aggregate_complete"] = True
        with self.assertRaisesRegex(globalv.GlobalError, "MANIFEST_COVERAGE"):
            globalv.verify(ROOT, changed)

    def test_mode_and_native_source_refusals(self):
        original = bridge.read
        def changed_read(path):
            value = original(path)
            if path == bridge.SOURCE / "allocation-handoff.json":
                value["source_map"][0]["modes"][1]["txt"] = "L10-TXT1-1-33"
            return value
        with patch.object(bridge, "read", side_effect=changed_read):
            with self.assertRaisesRegex(bridge.PreworkError, "MODE_MAP"):
                bridge.source_prework()
        changed = copy.deepcopy(self.manifest)
        changed["shards"][2]["artifacts"]["native_report"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(globalv.GlobalError, "ARTIFACT_PIN"):
            globalv.verify(ROOT, changed)
        descriptor = self.manifest["shards"][2]
        docs = {role: globalv.load_artifact(ROOT, ref)
                for role, ref in descriptor["artifacts"].items()}
        docs["source_map"]["entries"][0]["source_record_sha256"] = "0" * 64
        with self.assertRaisesRegex(globalv.GlobalError, "SOURCE_MAP_PROPOSAL"):
            globalv.check_local(descriptor, docs, self.catalog, self.course)

    def test_pairwise_identity_event_and_source_refuse(self):
        first, last = self.checked[0], self.checked[2]
        changed = copy.deepcopy(last)
        changed["entities"][1]["id"] = first["entities"][1]["id"]
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_DUPLICATE_ENTITY"):
            globalv.check_union(self.foundation, [first, changed], self.catalog)
        changed = copy.deepcopy(last)
        changed["event_ids"][0] = first["event_ids"][0]
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_DUPLICATE_EVENT"):
            globalv.check_union(self.foundation, [first, changed], self.catalog)
        changed = copy.deepcopy(last)
        changed["source_ids"].add(next(iter(first["source_ids"])))
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_DUPLICATE_SOURCE"):
            globalv.check_union(self.foundation, [first, changed], self.catalog)
        changed = copy.deepcopy(last)
        changed["source_keys"].add(next(iter(first["source_keys"])))
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_DUPLICATE_SOURCE_KEY"):
            globalv.check_union(self.foundation, [first, changed], self.catalog)


if __name__ == "__main__":
    unittest.main()
