"""Focused source and refusal checks for the Level 10 first odd-count shift."""
import copy
import json
import subprocess
import sys
import unittest

import parallel23_level010_ex001_odd_shift_candidate as candidate


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = candidate.derive()

    def test_exact_low_e_mode_a_route(self):
        record = self.output["package.json"]["records"][0]
        events = record["events"]
        self.assertEqual([(e["string"], e["fret"], e["finger"], e["midi"]) for e in events],
                         [(1, 5, 1, 45), (1, 6, 2, 46), (1, 5, 1, 45), (1, 8, 2, 48)])
        self.assertEqual([e["onset_q"] for e in events], [[0, 1], [1, 4], [1, 2], [3, 4]])
        self.assertEqual([e["duration_q"] for e in events], [[1, 4]] * 4)
        self.assertEqual([p["frame"] for p in self.output["source-provenance.json"]["events"].values()],
                         ["P5", "P5", "P5", "P7"])
        self.assertEqual([p["landing_note"] for p in self.output["source-provenance.json"]["events"].values()],
                         [False, False, False, True])

    def test_picking_starts_and_exact_scope(self):
        record = self.output["package.json"]["records"][0]
        sidecar = self.output["source-provenance.json"]
        self.assertEqual(sidecar["variant_strokes"],
                         {"fg:variant:007416": ["D", "U", "D", "U"],
                          "fg:variant:007417": ["U", "D", "U", "D"]})
        self.assertEqual(record["context"]["local_code"], "L010-S01-MA-EX001:UP:E:PASS2")
        self.assertEqual([v["pick_start"] for v in record["variants"]], ["D", "U"])
        self.assertEqual(record["control_scope"]["source_event_count"], 4)
        self.assertFalse(record["control_scope"]["whole_workbook_complete"])
        self.assertFalse(record["runtime_eligible"])
        self.assertNotIn("fixed_bpm", record["context"])

    def test_every_event_and_variant_is_source_closed(self):
        package = self.output["package.json"]
        record = package["records"][0]
        profile = self.output["expected-profile.json"]
        sidecar = self.output["source-provenance.json"]
        event_ids = {e["event_id"] for e in record["events"]}
        self.assertEqual(event_ids, set(profile["event_sources"]))
        self.assertEqual(event_ids, set(sidecar["events"]))
        self.assertEqual(set(record["source_refs"]), set(package["sources"]))
        for event_id, provenance in sidecar["events"].items():
            self.assertEqual(profile["event_sources"][event_id], provenance["source_txt_ref"])
            self.assertEqual(provenance["source_txt_line"], 53)
            self.assertEqual(provenance["source_pdf_page"], 2)
            self.assertIn(provenance["source_txt_ref"], record["source_refs"])
        for variant in record["variants"]:
            self.assertEqual(set(variant["event_ids"]), event_ids)
            self.assertEqual(set(variant["source_refs"]), set(package["sources"]))

    def test_registry_profile_and_provisional_ids(self):
        registry = self.output["identity-registry.json"]
        profile = self.output["expected-profile.json"]
        ids = [entity["id"] for entity in registry["entities"]]
        self.assertEqual(ids, ["fg:course:000001", "fg:workbook:000010", "fg:module:001147",
                               "fg:item:001147", "fg:variant:007416", "fg:variant:007417"])
        self.assertEqual(profile["reference_package"], self.output["package.json"])
        self.assertEqual(profile["reference_registry"], registry)
        self.assertEqual(profile["degree_roots"], {})
        self.assertEqual(self.output["summary.json"]["identity_audit_sha256"], candidate.AUDIT_SHA)

    def test_source_timing_eligibility_and_identity_refusals(self):
        facts = [(1, 5, 1, 45, "P5"), (1, 6, 2, 46, "P5"),
                 (1, 5, 1, 45, "P5"), (1, 8, 2, 48, "P7")]
        modified = copy.deepcopy(facts)
        modified[-1] = (1, 9, 2, 49, "P7")
        with self.assertRaisesRegex(candidate.CandidateError, "CANDIDATE_SOURCE_DRIFT"):
            candidate.derive(changed_facts=modified)
        with self.assertRaisesRegex(candidate.CandidateError, "CANDIDATE_TIMING_DRIFT"):
            candidate.derive(changed_onsets=[[0, 1], [1, 4], [1, 2], [1, 1]])
        with self.assertRaisesRegex(candidate.CandidateError, "FORCED_ELIGIBILITY"):
            candidate.derive(force_eligible=True)
        with self.assertRaisesRegex(candidate.CandidateError, "FOREIGN_ID"):
            candidate.derive(reserved_item="fg:item:999999")

    def test_written_package_verifies_and_rebuild_refuses_overwrite(self):
        command = [sys.executable, str(candidate.ROOT / "Tools/parallel23_level010_ex001_odd_shift_candidate.py")]
        verify = subprocess.run(command + ["verify"], capture_output=True, text=True)
        self.assertEqual(verify.returncode, 0, verify.stderr)
        rebuild = subprocess.run(command + ["build"], capture_output=True, text=True)
        self.assertNotEqual(rebuild.returncode, 0)
        self.assertIn("OUTPUT_EXISTS", rebuild.stderr)
        escape = subprocess.run(command + ["build", "--out", "Build/parallel-23/escape"],
                                capture_output=True, text=True)
        self.assertNotEqual(escape.returncode, 0)
        self.assertIn("OUTPUT_SCOPE", escape.stderr)


if __name__ == "__main__":
    unittest.main()
