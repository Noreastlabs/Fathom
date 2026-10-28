"""Two genuine native shards, provenance bridge and ordered-union refusals."""

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel10_global_shard_verifier as globalv  # noqa: E402
import parallel10_two_real_shard_manifest_r04 as bridge  # noqa: E402


class TwoRealShardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / bridge.OUT / "manifest.json").read_text())
        cls.summary = bridge.verify()
        cls.foundation = {role: globalv.load_artifact(ROOT, value)
                          for role, value in cls.manifest["foundation"].items()}
        cls.catalog = cls.foundation["registry"]["workbook_catalog"]
        cls.course = next(e for e in cls.foundation["registry"]["entities"] if e["kind"] == "course")
        cls.checked = []
        for descriptor in cls.manifest["shards"]:
            docs = {role: globalv.load_artifact(ROOT, ref)
                    for role, ref in descriptor["artifacts"].items()}
            cls.checked.append(globalv.check_local(descriptor, docs, cls.catalog, cls.course))

    def test_exact_two_real_shards_and_no_admission(self):
        self.assertEqual(self.summary["validated_workbooks"], [7, 8])
        self.assertEqual(self.summary["shard_count"], 2)
        self.assertEqual(self.summary["new_counts"],
                         {"records": 216, "entities": 1082, "events": 12096,
                          "sources": 238, "variants": 648})
        self.assertEqual(self.summary["next_allocation_floor"],
                         {"module": 912, "item": 912, "variant": 6082})
        self.assertFalse(self.summary["aggregate_complete"])
        self.assertFalse(self.summary["full_105_workbook_source_coverage_verified"])
        self.assertFalse(self.summary["admitted"])
        self.assertFalse(self.summary["runtime_admission"])
        self.assertEqual(globalv.encoded(self.summary),
                         (ROOT / bridge.OUT / "summary.json").read_bytes())
        for descriptor in self.manifest["shards"]:
            report = globalv.load_artifact(ROOT, descriptor["artifacts"]["native_report"])
            self.assertTrue(report["valid_reference"])
            self.assertEqual(report["exit_code"], 2)
            self.assertFalse(report["curriculum_playback_authorized"])
            self.assertEqual(report["coverage"]["observed_records"], 108)

    def test_level8_bridge_binds_upstream_and_original_sources(self):
        derived = bridge.derive()
        for name, obj in derived.items():
            self.assertEqual((ROOT / bridge.OUT / name).read_bytes(), globalv.encoded(obj))
        normalized = derived["level008-normalized-source-proposal.json"]
        self.assertEqual(normalized["upstream_field_proposal_sha256"],
                         bridge.PINS[bridge.P12_SOURCE / "field-proposal.json"])
        self.assertEqual(normalized["upstream_handoff_sha256"],
                         bridge.PINS[bridge.P12_SOURCE / "allocation-handoff.json"])
        self.assertEqual(len(normalized["records"]), 108)
        with patch.dict(bridge.PINS, {bridge.TXT8: "0" * 64}):
            with self.assertRaisesRegex(bridge.BridgeError, "INPUT_PIN_DRIFT"):
                bridge.derive()

    def test_order_duplicate_and_coverage_refuse(self):
        changed = copy.deepcopy(self.manifest)
        changed["shards"].reverse()
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_RESERVED_OR_ORDER"):
            globalv.verify(ROOT, changed)
        changed = copy.deepcopy(self.manifest)
        changed["shards"].append(copy.deepcopy(changed["shards"][1]))
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_DUPLICATE_WORKBOOK"):
            globalv.verify(ROOT, changed)
        changed = copy.deepcopy(self.manifest)
        changed["aggregate_complete"] = True
        with self.assertRaisesRegex(globalv.GlobalError, "MANIFEST_COVERAGE"):
            globalv.verify(ROOT, changed)

    def test_pairwise_real_identity_and_source_sets(self):
        seven, eight = self.checked
        self.assertFalse({e["id"] for e in seven["entities"]} &
                         {e["id"] for e in eight["entities"]})
        self.assertFalse(seven["record_ids"] & eight["record_ids"])
        self.assertFalse(set(seven["event_ids"]) & set(eight["event_ids"]))
        self.assertFalse(seven["source_ids"] & eight["source_ids"])
        self.assertFalse(seven["source_keys"] & eight["source_keys"])
        self.assertEqual(globalv.check_union(self.foundation, self.checked, self.catalog)
                         ["validated_workbooks"], [7, 8])

    def test_pairwise_mutation_refusals(self):
        seven, eight = self.checked
        altered = copy.deepcopy(eight)
        altered["entities"][1]["id"] = seven["entities"][1]["id"]
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_DUPLICATE_ENTITY"):
            globalv.check_union(self.foundation, [seven, altered], self.catalog)
        altered = copy.deepcopy(eight)
        altered["event_ids"][0] = seven["event_ids"][0]
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_DUPLICATE_EVENT"):
            globalv.check_union(self.foundation, [seven, altered], self.catalog)
        altered = copy.deepcopy(eight)
        altered["source_ids"].add(next(iter(seven["source_ids"])))
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_DUPLICATE_SOURCE"):
            globalv.check_union(self.foundation, [seven, altered], self.catalog)
        altered = copy.deepcopy(eight)
        altered["source_keys"].add(next(iter(seven["source_keys"])))
        with self.assertRaisesRegex(globalv.GlobalError, "GLOBAL_DUPLICATE_SOURCE_KEY"):
            globalv.check_union(self.foundation, [seven, altered], self.catalog)

    def test_native_and_source_binding_refuse(self):
        changed = copy.deepcopy(self.manifest)
        changed["shards"][1]["artifacts"]["native_report"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(globalv.GlobalError, "ARTIFACT_PIN"):
            globalv.verify(ROOT, changed)
        descriptor = self.manifest["shards"][1]
        docs = {role: globalv.load_artifact(ROOT, ref)
                for role, ref in descriptor["artifacts"].items()}
        docs["source_map"]["entries"][0]["source_record_sha256"] = "0" * 64
        with self.assertRaisesRegex(globalv.GlobalError, "SOURCE_MAP_PROPOSAL"):
            globalv.check_local(descriptor, docs, self.catalog, self.course)


if __name__ == "__main__":
    unittest.main()
