"""Focused source closure, pitch, timing, identity, and admission checks for Rung05."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel03_level012_rung05_candidate as candidate


class Rung05CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = candidate.derive()
        cls.build = ROOT / candidate.OUT
        cls.record = cls.output["package.json"]["records"][0]

    def test_deterministic_artifacts_and_identity(self):
        for name in candidate.NAMES:
            self.assertEqual((self.build / name).read_bytes(), candidate.encode(self.output[name]), name)
        self.assertEqual((self.record["id"], self.record["module_id"], self.record["workbook_id"]),
                         ("fg:item:001145", "fg:module:001145", "fg:workbook:000012"))
        self.assertEqual((self.record["content_revision"], self.record["lineage"]), (1, {"kind": "new"}))
        self.assertEqual([v["id"] for v in self.record["variants"]],
                         ["fg:variant:007412", "fg:variant:007413"])
        self.assertFalse(self.record["runtime_eligible"])
        self.assertTrue(self.output["summary.json"]["fresh_identity_scan"]["collision_free"])
        self.assertEqual(self.output["summary.json"]["live_identity_audit_sha256"], candidate.IDENTITY_AUDIT_SHA)

    def test_original_cards_pitch_fingering_and_setup(self):
        package = self.output["package.json"]
        candidate.check_source_cell(package["sources"], self.record, "L12-TXT1-98-109", "L12-PDF1-p4")
        self.assertEqual([e["midi"] for e in self.record["events"]],
                         [49, 51, 53, 54, 56, 58, 60, 61, 61, 60, 58, 56, 54, 53, 51, 49])
        self.assertEqual(self.record["context"]["tuning_open_midi"], [40, 45, 50, 55, 59, 64])
        self.assertEqual(self.record["context"]["capo"], 0)
        candidate.check_candidate_labels(self.record, self.output["identity-registry.json"],
                                         self.output["expected-profile.json"])

    def test_even_eighths_and_alternate_strokes(self):
        candidate.check_connected_eighths(self.record)
        self.assertEqual([e["onset_q"] for e in self.record["events"]],
                         [[i // 2, 1] if i % 2 == 0 else [i, 2] for i in range(16)])
        self.assertTrue(all(e["duration_q"] == [1, 2] for e in self.record["events"]))
        self.assertEqual([v["pick_start"] for v in self.record["variants"]], ["D", "U"])
        self.assertTrue(all(v["tail_pause"] is None for v in self.record["variants"]))

    def test_source_ref_closure_and_mutation_refusal(self):
        refs = self.output["package.json"]["sources"]
        event_sources = self.output["expected-profile.json"]["event_sources"]
        candidate.check_source_closure(self.record, refs, event_sources)
        bad = copy.deepcopy(self.record)
        bad["source_refs"][0] = "L12-TXT1-84-95"
        with self.assertRaisesRegex(candidate.PilotError, "SOURCE_REF_CLOSURE"):
            candidate.check_source_closure(bad, refs, event_sources)
        bad_sources = dict(event_sources)
        bad_sources[next(iter(bad_sources))] = "L12-TXT1-84-95"
        with self.assertRaisesRegex(candidate.PilotError, "EVENT_SOURCE_CLOSURE"):
            candidate.check_source_closure(self.record, refs, bad_sources)

    def test_fret_timing_and_self_admission_refusals(self):
        bad = copy.deepcopy(self.record)
        bad["events"][0]["fret"] = 10
        with self.assertRaisesRegex(candidate.PilotError, "SOURCE_EVENT_DRIFT"):
            candidate.check_source_cell(self.output["package.json"]["sources"], bad,
                                        "L12-TXT1-98-109", "L12-PDF1-p4")
        bad = copy.deepcopy(self.record)
        bad["events"][1]["onset_q"] = [1, 1]
        with self.assertRaisesRegex(candidate.PilotError, "TIMING_SCOPE"):
            candidate.check_connected_eighths(bad)
        bad = copy.deepcopy(self.record)
        bad["runtime_eligible"] = True
        with self.assertRaisesRegex(candidate.PilotError, "SETUP_OR_ADMISSION_DRIFT"):
            candidate.check_source_closure(bad, self.output["package.json"]["sources"],
                                           self.output["expected-profile.json"]["event_sources"])

    def test_native_valid_reference_playback_withheld(self):
        report = json.loads((self.build / "native-report.json").read_text())
        self.assertEqual((report["exit_code"], report["valid_reference"],
                          report["curriculum_playback_authorized"]), (2, True, False))
        self.assertEqual((report["coverage"]["observed_records"], report["coverage"]["events"],
                          report["coverage"]["variants"]), (1, 16, 2))
        self.assertEqual(report["package_sha256"],
                         hashlib.sha256((self.build / "package.json").read_bytes()).hexdigest())
        self.assertIn("MODEL_not_admitted", {issue["code"] for issue in report["issues"]})


if __name__ == "__main__":
    unittest.main()
