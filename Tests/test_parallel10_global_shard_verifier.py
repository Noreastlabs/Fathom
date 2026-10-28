"""Real one-shard proof and negative cases for the ordered global verifier."""

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel10_global_shard_verifier as verifier  # noqa: E402


class GlobalShardVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / verifier.OUT / "manifest.json").read_text())
        cls.foundation = {
            role: verifier.load_artifact(ROOT, value)
            for role, value in cls.manifest["foundation"].items()
        }
        cls.catalog = cls.foundation["registry"]["workbook_catalog"]
        cls.course = next(e for e in cls.foundation["registry"]["entities"] if e["kind"] == "course")
        cls.descriptor = cls.manifest["shards"][0]
        cls.docs = {role: verifier.load_artifact(ROOT, ref)
                    for role, ref in cls.descriptor["artifacts"].items()}
        cls.checked = verifier.check_local(cls.descriptor, cls.docs, cls.catalog, cls.course)

    def test_real_level7_and_derived_serial_floor(self):
        summary = verifier.verify(ROOT, self.manifest)
        self.assertEqual(summary["validated_workbooks"], [7])
        self.assertEqual(summary["shard_count"], 1)
        self.assertEqual(summary["new_counts"],
                         {"records": 108, "entities": 433, "events": 1728,
                          "sources": 120, "variants": 216})
        self.assertEqual(summary["next_allocation_floor"],
                         {"module": 804, "item": 804, "variant": 5650})
        self.assertFalse(summary["aggregate_complete"])
        self.assertFalse(summary["admitted"])
        self.assertEqual(verifier.encoded(summary),
                         (ROOT / verifier.OUT / "summary.json").read_bytes())

    def test_manifest_pins_and_admission_refuse(self):
        changed = copy.deepcopy(self.manifest)
        changed["foundation"]["package"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(verifier.GlobalError, "FOUNDATION_PIN"):
            verifier.verify(ROOT, changed)
        changed = copy.deepcopy(self.manifest)
        changed["shards"][0]["artifacts"]["profile"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(verifier.GlobalError, "ARTIFACT_PIN"):
            verifier.verify(ROOT, changed)
        changed = copy.deepcopy(self.manifest)
        changed["admitted"] = True
        with self.assertRaisesRegex(verifier.GlobalError, "MANIFEST_AUTHORITY"):
            verifier.verify(ROOT, changed)

    def test_duplicate_real_descriptor_refuses_without_positive_synthetic_claim(self):
        changed = copy.deepcopy(self.manifest)
        changed["shards"].append(copy.deepcopy(changed["shards"][0]))
        with self.assertRaisesRegex(verifier.GlobalError, "GLOBAL_DUPLICATE_WORKBOOK"):
            verifier.verify(ROOT, changed)

    def test_local_baseline_native_and_source_map_refuse(self):
        docs = copy.deepcopy(self.docs)
        docs["identity_baseline"]["entities"] = []
        with self.assertRaisesRegex(verifier.GlobalError, "LOCAL_BASELINE"):
            verifier.check_local(self.descriptor, docs, self.catalog, self.course)
        docs = copy.deepcopy(self.docs)
        docs["native_report"]["valid_reference"] = False
        with self.assertRaisesRegex(verifier.GlobalError, "NATIVE_SHARD_INVALID"):
            verifier.check_local(self.descriptor, docs, self.catalog, self.course)
        docs = copy.deepcopy(self.docs)
        docs["source_map"]["entries"][0]["source_record_sha256"] = "0" * 64
        with self.assertRaisesRegex(verifier.GlobalError, "SOURCE_MAP_PROPOSAL"):
            verifier.check_local(self.descriptor, docs, self.catalog, self.course)
        docs = copy.deepcopy(self.docs)
        docs["profile"]["authority_artifacts"] = [a for a in docs["profile"]["authority_artifacts"]
                                                  if a["role"] != "candidate_identity_allocation"]
        with self.assertRaisesRegex(verifier.GlobalError, "LOCAL_AUTHORITY_BINDING"):
            verifier.check_local(self.descriptor, docs, self.catalog, self.course)

    def test_reserved_and_ordered_allocation_refusals(self):
        checked = copy.deepcopy(self.checked)
        module = next(e for e in checked["entities"] if e["kind"] == "module")
        module["id"] = "fg:module:000552"  # catalog-reserved and not in the 659 registry
        with self.assertRaisesRegex(verifier.GlobalError, "GLOBAL_RESERVED_OR_ORDER"):
            verifier.check_union(self.foundation, [checked], self.catalog)
        # A fabricated high-ID first payload is used only to prove refusal
        # when the subsequent genuine Level7 IDs run backward in order.
        first = copy.deepcopy(self.checked)
        first["workbook"] = "fg:workbook:000008"
        for e in first["entities"]:
            if e["kind"] == "workbook":
                e["id"] = first["workbook"]
            else:
                e["id"] = f"fg:{e['kind']}:{verifier.number(e['id'], e['kind']) + 10000:06d}"
        with self.assertRaisesRegex(verifier.GlobalError, "GLOBAL_RESERVED_OR_ORDER"):
            verifier.check_union(self.foundation, [first, self.checked], self.catalog)

    def test_pairwise_identity_event_source_refusals(self):
        # These altered payloads are negative fixtures. No fabricated second
        # workbook is ever accepted as native evidence.
        second = copy.deepcopy(self.checked)
        second["workbook"] = "fg:workbook:000008"
        second["entities"][0]["id"] = second["workbook"]
        with self.assertRaisesRegex(verifier.GlobalError, "GLOBAL_DUPLICATE_ENTITY"):
            verifier.check_union(self.foundation, [self.checked, second], self.catalog)
        for e in second["entities"][1:]:
            e["id"] = f"fg:{e['kind']}:{verifier.number(e['id'], e['kind']) + 10000:06d}"
        second["record_ids"] = {f"fg:item:{verifier.number(r, 'item') + 10000:06d}"
                                for r in second["record_ids"]}
        with self.assertRaisesRegex(verifier.GlobalError, "GLOBAL_DUPLICATE_EVENT"):
            verifier.check_union(self.foundation, [self.checked, second], self.catalog)
        second["event_ids"] = [f"synthetic-negative:{i}" for i in range(len(second["event_ids"]))]
        with self.assertRaisesRegex(verifier.GlobalError, "GLOBAL_DUPLICATE_SOURCE"):
            verifier.check_union(self.foundation, [self.checked, second], self.catalog)
        second["source_ids"] = {f"synthetic-negative:{x}" for x in second["source_ids"]}
        with self.assertRaisesRegex(verifier.GlobalError, "GLOBAL_DUPLICATE_SOURCE_KEY"):
            verifier.check_union(self.foundation, [self.checked, second], self.catalog)

    def test_foundation_record_event_and_source_refusals(self):
        changed = copy.deepcopy(self.checked)
        changed["record_ids"].add(self.foundation["package"]["records"][0]["id"])
        with self.assertRaisesRegex(verifier.GlobalError, "GLOBAL_DUPLICATE_RECORD"):
            verifier.check_union(self.foundation, [changed], self.catalog)
        changed = copy.deepcopy(self.checked)
        changed["event_ids"][0] = self.foundation["package"]["records"][0]["events"][0]["event_id"]
        with self.assertRaisesRegex(verifier.GlobalError, "GLOBAL_DUPLICATE_EVENT"):
            verifier.check_union(self.foundation, [changed], self.catalog)
        changed = copy.deepcopy(self.checked)
        changed["source_ids"].add(next(iter(self.foundation["package"]["sources"])))
        with self.assertRaisesRegex(verifier.GlobalError, "GLOBAL_DUPLICATE_SOURCE"):
            verifier.check_union(self.foundation, [changed], self.catalog)


if __name__ == "__main__":
    unittest.main()
