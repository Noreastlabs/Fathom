"""Focused source, timing, identity, and refusal checks for two Level 9 cells."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest

import parallel37_level009_two_case_candidate as candidate


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = candidate.derive()

    def test_two_exact_source_routes_and_2_plus_2_frame_boundary(self):
        records = self.output["package.json"]["records"]
        self.assertEqual([r["context"]["local_code"] for r in records],
                         ["L009-S01-EX001:SHIFT_UP:E:PASS2",
                          "L009-S01-EX001:SHIFT_DOWN:e:PASS2"])
        expected = [[(1, 5, 1, 45), (1, 6, 2, 46),
                     (1, 7, 1, 47), (1, 8, 2, 48)],
                    [(6, 7, 1, 71), (6, 8, 2, 72),
                     (6, 5, 1, 69), (6, 6, 2, 70)]]
        for record, notes in zip(records, expected):
            self.assertEqual([(e["string"], e["fret"], e["finger"], e["midi"])
                              for e in record["events"]], notes)
            self.assertEqual([e["onset_q"] for e in record["events"]],
                             [[0, 1], [1, 4], [1, 2], [3, 4]])
            self.assertEqual([e["duration_q"] for e in record["events"]], [[1, 4]]*4)
            self.assertEqual(record["control_scope"]["source_event_count"], 4)
            self.assertFalse(record["runtime_eligible"])
            self.assertFalse(record["control_scope"]["whole_workbook_complete"])
            self.assertIsNone(record["rubric"])
            self.assertNotIn("fixed_bpm", record["context"])

    def test_all_events_have_distinct_provenance_and_source_authored_pick_starts(self):
        package = self.output["package.json"]
        provenance = self.output["source-provenance.json"]
        profile = self.output["expected-profile.json"]
        records = package["records"]
        event_ids = {e["event_id"] for r in records for e in r["events"]}
        self.assertEqual(event_ids, set(profile["event_sources"]))
        self.assertEqual(event_ids, set(provenance["events"]))
        self.assertEqual(len({p["source_local_event_key"] for p in provenance["events"].values()}), 8)
        self.assertEqual([p["frame"] for p in provenance["events"].values()],
                         ["P5", "P5", "P7", "P7", "P7", "P7", "P5", "P5"])
        self.assertEqual([p["landing_note"] for p in provenance["events"].values()],
                         [False, False, True, False]*2)
        self.assertEqual([p["source_txt_line"] for p in provenance["events"].values()],
                         [38]*4+[40]*4)
        for record in records:
            self.assertEqual([v["pick_start"] for v in record["variants"]], ["D", "U"])
            self.assertEqual([v["accent_policy"] for v in record["variants"]], ["even"]*2)
            self.assertEqual(set(record["source_refs"]), set(package["sources"]))
        for variant, strokes in provenance["variant_strokes"].items():
            self.assertEqual(strokes, ["D", "U", "D", "U"] if variant.endswith(("420", "422"))
                             else ["U", "D", "U", "D"])

    def test_provisional_allocation_and_native_nonadmission(self):
        registry = self.output["identity-registry.json"]
        self.assertEqual([e["id"] for e in registry["entities"]],
                         ["fg:course:000001", "fg:workbook:000009",
                          "fg:module:001149", "fg:item:001149",
                          "fg:variant:007420", "fg:variant:007421",
                          "fg:module:001150", "fg:item:001150",
                          "fg:variant:007422", "fg:variant:007423"])
        self.assertEqual(set(self.output["candidate-allocation.json"]["records"]), set(candidate.ITEMS))
        self.assertEqual(self.output["expected-profile.json"]["reference_package"],
                         self.output["package.json"])
        report = json.loads((candidate.ROOT/candidate.OUT/"native-report.json").read_text())
        self.assertEqual(report["exit_code"], 2)
        self.assertTrue(report["valid_reference"])
        self.assertFalse(report["curriculum_playback_authorized"])
        self.assertEqual(report["coverage"]["observed_records"], 2)
        self.assertEqual(report["coverage"]["events"], 8)
        self.assertEqual(report["coverage"]["variants"], 4)
        self.assertEqual([(i["code"], i["record"]) for i in report["issues"]],
                         [("MODEL_not_admitted", candidate.ITEMS[0]),
                          ("MODEL_not_admitted", candidate.ITEMS[1])])

    def test_changed_source_timing_strokes_identity_and_eligibility_refuse(self):
        facts = [s["facts"] for s in candidate.source_facts()[2]]
        changed = copy.deepcopy(facts)
        changed[1][2] = (6, 6, 1, 70, "P5")
        with self.assertRaisesRegex(candidate.CandidateError, "CANDIDATE_SOURCE_DRIFT"):
            candidate.derive(changed_facts=changed)
        with self.assertRaisesRegex(candidate.CandidateError, "CANDIDATE_TIMING_DRIFT"):
            candidate.derive(changed_onsets=[[0, 1]]*4)
        with self.assertRaisesRegex(candidate.CandidateError, "CANDIDATE_DURATION_DRIFT"):
            candidate.derive(changed_durations=[[1, 2]]*4)
        with self.assertRaisesRegex(candidate.CandidateError, "CANDIDATE_STROKE_DRIFT"):
            candidate.derive(changed_strokes={candidate.VARIANTS[0][0]: ["D"]*4})
        with self.assertRaisesRegex(candidate.CandidateError, "FORCED_ELIGIBILITY"):
            candidate.derive(force_eligible=True)
        with self.assertRaisesRegex(candidate.CandidateError, "FOREIGN_ID"):
            candidate.derive(reserved_item="fg:item:999999")
        original = candidate.TXT_SHA
        try:
            candidate.TXT_SHA = "0"*64
            with self.assertRaisesRegex(candidate.CandidateError, "TXT_PIN_DRIFT"):
                candidate.derive()
        finally:
            candidate.TXT_SHA = original

    def test_written_bytes_and_output_boundary(self):
        command = [sys.executable, str(candidate.ROOT/"Tools/parallel37_level009_two_case_candidate.py")]
        verify = subprocess.run(command+["verify"], capture_output=True, text=True)
        self.assertEqual(verify.returncode, 0, verify.stderr)
        rebuild = subprocess.run(command+["build"], capture_output=True, text=True)
        self.assertNotEqual(rebuild.returncode, 0)
        self.assertIn("OUTPUT_EXISTS", rebuild.stderr)
        escape = subprocess.run(command+["build", "--out", "Build/parallel-37/escape"],
                                capture_output=True, text=True)
        self.assertNotEqual(escape.returncode, 0)
        self.assertIn("OUTPUT_SCOPE", escape.stderr)


if __name__ == "__main__":
    unittest.main()
