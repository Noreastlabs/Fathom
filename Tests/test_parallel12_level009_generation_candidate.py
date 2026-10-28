import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock


TOOL = Path(__file__).resolve().parents[1] / "Tools/parallel12_level009_generation_candidate.py"
spec = importlib.util.spec_from_file_location("parallel12_level009_generation_candidate", TOOL)
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class GenerationCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generation, cls.preflight = candidate.derive()

    def test_counts_identity_catalog_and_historical_lineage(self):
        current = json.loads((candidate.ROOT / candidate.CURRENT / "generation.json").read_text())
        self.assertEqual({k: self.generation[k] for k in ("records", "current_entities", "variants", "events", "passages")}, {"records": 659, "current_entities": 6336, "variants": 5001, "events": 26845, "passages": 775})
        self.assertEqual(self.generation["workbooks"], sorted(current["workbooks"] + [9]))
        self.assertEqual(self.generation["workbook_catalog"], current["workbook_catalog"])
        self.assertEqual(self.generation["reconciliation"], current["reconciliation"])
        self.assertEqual(self.generation["bundle_status"], current["bundle_status"])
        self.assertFalse(self.generation["bundle_status"]["admitted"])
        self.assertEqual(self.generation["identities"]["package.json"], candidate.PINS[candidate.OVERLAY / "package.json"])

    def test_four_file_preflight_and_level12_catalog_precedent(self):
        self.assertEqual(set(self.preflight["candidate"]), set(candidate.FOUR))
        self.assertEqual(set(self.preflight["baseline"]), set(candidate.FOUR))
        self.assertEqual(self.preflight["rollback_inputs"], self.preflight["baseline"])
        self.assertEqual(self.preflight["candidate"]["generation.json"]["sha256"], candidate.sha(candidate.encoded(self.generation)))
        self.assertEqual(self.preflight["status"], "ready_for_P02_review_only_no_content_write")
        self.assertTrue(self.preflight["catalog_status_distinction"]["level12_precedent_checked"])
        self.assertFalse(self.preflight["catalog_status_distinction"]["catalog_change_proposed"])
        self.assertEqual(self.preflight["unchanged_workbook_coverage"]["sha256"], candidate.PINS[candidate.CURRENT / "workbook-coverage.json"])

    def test_input_pin_drift_refused(self):
        path = candidate.OVERLAY / "package.json"
        original = candidate.PINS[path]
        try:
            candidate.PINS[path] = "0" * 64
            with self.assertRaisesRegex(candidate.PreflightError, "PIN_DRIFT"):
                candidate.check_pins()
        finally:
            candidate.PINS[path] = original

    def test_each_reserved_family_refused(self):
        registry = json.loads((candidate.ROOT / candidate.CURRENT / "identity-registry.json").read_text())
        for kind, reserved in (("module", "fg:module:000552"), ("item", "fg:item:000587"), ("variant", "fg:variant:005001")):
            with self.subTest(kind=kind), self.assertRaisesRegex(candidate.PreflightError, "RESERVED_ID_COLLISION"):
                candidate.check_reservations(registry, [{"kind": kind, "id": reserved}])

    def test_native_authority_refusal(self):
        original_load = candidate.load
        def altered_load(root, path):
            value = original_load(root, path)
            if path == candidate.OVERLAY / "native-report.json":
                value["valid_reference"] = False
            return value
        with mock.patch.object(candidate, "load", side_effect=altered_load), self.assertRaisesRegex(candidate.PreflightError, "NATIVE_REFERENCE"):
            candidate.derive()

    def test_deterministic_bytes(self):
        generation, preflight = candidate.derive()
        self.assertEqual(candidate.encoded(generation), candidate.encoded(self.generation))
        self.assertEqual(candidate.encoded(preflight), candidate.encoded(self.preflight))


if __name__ == "__main__":
    unittest.main()
