"""Parser-independent Level 7 overlay source, lineage and authority checks."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from Tools import parallel10_level007_schema1_overlay as subject


class Level7OverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifacts = subject.derive()
        cls.predecessor = subject.load(subject.ROOT, subject.CURRENT / "package.json")
        cls.pre_registry = subject.load(subject.ROOT, subject.CURRENT / "identity-registry.json")
        cls.pre_profile = subject.load(subject.ROOT, subject.CURRENT / "expected-profile.json")
        cls.source = subject.load(subject.ROOT, subject.SOURCE_PROPOSAL)

    def test_exact_predecessor_prefix_and_generation(self) -> None:
        a = self.artifacts
        package, registry = a["package.json"], a["identity-registry.json"]
        profile, generation = a["expected-profile.json"], a["generation.json"]
        self.assertEqual(package["records"][:659], self.predecessor["records"])
        self.assertEqual(registry["entities"][:6336], self.pre_registry["entities"])
        self.assertEqual({k: package["sources"][k] for k in self.predecessor["sources"]}, self.predecessor["sources"])
        self.assertEqual({k: profile["event_sources"][k] for k in self.pre_profile["event_sources"]},
                         self.pre_profile["event_sources"])
        self.assertEqual(a["candidate-allocation.json"]["records"] | {},
                         {**subject.load(subject.ROOT, subject.ALLOCATION_659)["records"],
                          **a["transaction.json"]["records"]})
        self.assertEqual((generation["records"], generation["current_entities"], generation["variants"],
                          generation["events"], generation["passages"]), (767, 6769, 5217, 28573, 895))
        self.assertEqual(generation["reconciliation"], subject.load(subject.ROOT, subject.CURRENT / "generation.json")["reconciliation"])
        self.assertEqual(package["workbook_catalog"], self.predecessor["workbook_catalog"])
        self.assertEqual(profile["workbook_catalog"], self.pre_profile["workbook_catalog"])

    def test_all_108_cases_432_routes_1728_contacts(self) -> None:
        a = self.artifacts
        new = a["package.json"]["records"][659:]
        self.assertEqual(len(new), 108)
        self.assertEqual(len(a["transaction.json"]["source_map"]), 108)
        self.assertEqual(len(a["transaction.json"]["new_entities"]), 433)
        self.assertEqual(sum(len(r["events"]) for r in new), 1728)
        self.assertEqual(sum(len(r["variants"]) for r in new), 216)
        self.assertEqual(sum(len(case["record_proposal"]["route_proposals"]) for case in self.source["records"]), 432)
        for case, record, source_map in zip(self.source["records"], new, a["transaction.json"]["source_map"], strict=True):
            self.assertEqual(record["context"]["source_local_key"], case["source_local_key"])
            self.assertEqual(source_map["source_local_key"], case["source_local_key"])
            self.assertEqual(record["source_refs"][:2], [case["source_refs"]["txt"], case["source_refs"]["pdf"]])
            self.assertEqual(record["lineage"], {"kind": "new"})
            self.assertFalse(record["runtime_eligible"])
            self.assertEqual(record["timing"]["status"], "unresolved")
            self.assertEqual([v["pick_start"] for v in record["variants"]], ["D", "U"])
            for variant in record["variants"]:
                self.assertEqual(variant["event_ids"], [e["event_id"] for e in record["events"]])
            raw = case["record_proposal"]["events"]
            self.assertEqual([(e["string"], e["fret"], e["finger"], e["midi"]) for e in record["events"]],
                             [(e["string"], e["fret"], e["finger"], e["midi"]) for e in raw])
            self.assertTrue(all(e["onset_q"] is None and e["duration_q"] is None for e in record["events"]))
            self.assertEqual(len(a["candidate-allocation.json"]["records"][record["id"]]["occurrences"]), 16)
            self.assertEqual(len(a["candidate-allocation.json"]["records"][record["id"]]["variants"]), 2)

    def test_allocations_clear_all_current_and_reserved_ranges(self) -> None:
        a = self.artifacts
        new = a["transaction.json"]["new_entities"]
        self.assertEqual(a["transaction.json"]["floors"], {"module": 696, "item": 696, "variant": 5434})
        subject.check_new_ids(self.pre_registry, new)
        for kind, expected in (("module", list(range(696, 804))),
                               ("item", list(range(696, 804))),
                               ("variant", list(range(5434, 5650)))):
            numbers = [subject.suffix(e["id"]) for e in new if e["kind"] == kind]
            self.assertEqual(numbers, expected)
        for kind, reserved in (("module", "fg:module:000587"), ("item", "fg:item:000587"),
                               ("variant", "fg:variant:005001")):
            with self.subTest(kind=kind):
                broken = copy.deepcopy(new)
                next(e for e in broken if e["kind"] == kind)["id"] = reserved
                with self.assertRaisesRegex(subject.OverlayError, "RESERVED_ID_COLLISION"):
                    subject.check_new_ids(self.pre_registry, broken)
        broken = copy.deepcopy(new)
        broken[2]["id"] = broken[1]["id"]
        with self.assertRaisesRegex(subject.OverlayError, "DUPLICATE_ENTITY"):
            subject.check_new_ids(self.pre_registry, broken)

    def test_duplicate_key_and_duplicate_authority_refuse(self) -> None:
        source = copy.deepcopy(self.source)
        source["records"][1]["source_local_key"] = source["records"][0]["source_local_key"]
        with self.assertRaisesRegex(subject.OverlayError, "DUPLICATE_SOURCE_LOCAL_KEY"):
            subject.level7_records(source, self.pre_registry)
        profile = copy.deepcopy(self.pre_profile)
        profile["authority_artifacts"].append(profile["authority_artifacts"][-1])
        with self.assertRaisesRegex(subject.OverlayError, "PREDECESSOR_AUTHORITY"):
            subject.check_predecessor(self.predecessor, self.pre_registry, profile,
                                      subject.load(subject.ROOT, subject.CURRENT / "generation.json"),
                                      subject.load(subject.ROOT, subject.ALLOCATION_659))

    def test_input_pin_drift_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = next(iter(subject.PINS))
            path = root / first
            path.parent.mkdir(parents=True)
            path.write_text("changed")
            with self.assertRaisesRegex(subject.OverlayError, "PIN_DRIFT"):
                subject.pin_inputs(root)

    def test_build_outputs_verify_and_frozen_parser_limit_is_explicit(self) -> None:
        for name in subject.NAMES:
            self.assertEqual((subject.ROOT / subject.OUT / name).read_bytes(), subject.encoded(self.artifacts[name]))
        failed = json.loads((subject.ROOT / subject.OUT / "native-report.json").read_text())
        self.assertFalse(failed["valid_reference"])
        self.assertEqual(failed["exit_code"], 1)
        self.assertEqual(failed["records"], [])
        self.assertEqual([i["code"] for i in failed["issues"]], ["JSON_VALUE_LIMIT"])

        def values(value):
            if isinstance(value, dict):
                return 1 + sum(values(v) for v in value.values())
            if isinstance(value, list):
                return 1 + sum(values(v) for v in value)
            return 1

        self.assertEqual(values(self.pre_profile), 971166)
        self.assertEqual(values(self.artifacts["expected-profile.json"]), 1015106)
        self.assertGreater(values(self.artifacts["expected-profile.json"]), 1000000)
        self.assertLess(values(self.artifacts["package.json"]), 1000000)
        self.assertLess(values(self.artifacts["identity-registry.json"]), 1000000)


if __name__ == "__main__":
    unittest.main()
