"""Focused original-source and refusal checks for Level7 Exercise001 Pass2."""
from __future__ import annotations

import copy
import subprocess
import sys
import unittest

import parallel33_level007_ex001_relay_candidate as candidate


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = candidate.derive()

    def test_ordered_full_route_and_nominal_pass2(self):
        record = self.output["package.json"]["records"][0]
        events = record["events"]
        expected = [
            (1,5,1,45),(3,6,2,56),(3,5,1,55),(5,6,2,65),
            (2,5,1,50),(4,6,2,61),(4,5,1,60),(6,6,2,70),
            (6,5,1,69),(4,6,2,61),(4,5,1,60),(2,6,2,51),
            (5,5,1,64),(3,6,2,56),(3,5,1,55),(1,6,2,46)]
        self.assertEqual([(e["string"],e["fret"],e["finger"],e["midi"]) for e in events], expected)
        self.assertEqual([e["onset_q"] for e in events],
                         [[candidate.Fraction(i,4).numerator,candidate.Fraction(i,4).denominator]
                          for i in range(16)])
        self.assertEqual([e["duration_q"] for e in events], [[1,4]]*16)
        self.assertEqual(record["control_scope"]["source_event_count"],16)
        self.assertEqual(record["context"]["local_code"],"L007-S01-EX001:ASC-DESC:PASS2")
        self.assertFalse(record["runtime_eligible"])
        self.assertFalse(record["control_scope"]["whole_workbook_complete"])
        self.assertNotIn("fixed_bpm",record["context"])
        self.assertIsNone(record["rubric"])

    def test_every_note_and_variant_has_source_and_stroke(self):
        package=self.output["package.json"]
        record=package["records"][0]
        profile=self.output["expected-profile.json"]
        sidecar=self.output["source-provenance.json"]
        ids={e["event_id"] for e in record["events"]}
        self.assertEqual(ids,set(profile["event_sources"]))
        self.assertEqual(ids,set(sidecar["events"]))
        self.assertEqual(set(record["source_refs"]),set(package["sources"]))
        self.assertEqual([p["route_group"] for p in sidecar["events"].values()],
                         ["ASC-E-D-B"]*4+["ASC-A-G-e"]*4+["DESC-e-G-A"]*4+["DESC-B-D-E"]*4)
        self.assertEqual([p["source_txt_line"] for p in sidecar["events"].values()],
                         [37,35,35,33,36,34,34,32,39,41,41,43,40,42,42,44])
        self.assertEqual([p["gap_landing"] for p in sidecar["events"].values()],
                         [False,True,False,True]*4)
        self.assertEqual(sidecar["variant_strokes"],
                         {candidate.VARIANTS[0]:["D","U"]*8,candidate.VARIANTS[1]:["U","D"]*8})
        for variant in record["variants"]:
            self.assertEqual(set(variant["event_ids"]),ids)
            self.assertEqual(set(variant["source_refs"]),set(package["sources"]))
            self.assertEqual(variant["accent_policy"],"even")

    def test_provisional_identity_and_nonadmission(self):
        registry=self.output["identity-registry.json"]
        profile=self.output["expected-profile.json"]
        self.assertEqual([e["id"] for e in registry["entities"]],
                         ["fg:course:000001","fg:workbook:000007","fg:module:001148",
                          "fg:item:001148","fg:variant:007418","fg:variant:007419"])
        self.assertEqual(profile["reference_package"],self.output["package.json"])
        self.assertEqual(profile["reference_registry"],registry)
        self.assertEqual(profile["degree_roots"],{})
        self.assertEqual(self.output["summary.json"]["identity_audit_sha256"],candidate.AUDIT_SHA)
        self.assertFalse(self.output["summary.json"]["admitted"])

    def test_changed_fact_timing_source_identity_stroke_and_eligibility_refuse(self):
        facts=candidate.source_facts()[2]
        changed=copy.deepcopy(facts); changed[-1]=(1,7,2,47,"DESC-B-D-E",44)
        with self.assertRaisesRegex(candidate.CandidateError,"CANDIDATE_SOURCE_DRIFT"):
            candidate.derive(changed_facts=changed)
        with self.assertRaisesRegex(candidate.CandidateError,"CANDIDATE_TIMING_DRIFT"):
            candidate.derive(changed_onsets=[[0,1]]*16)
        with self.assertRaisesRegex(candidate.CandidateError,"CANDIDATE_DURATION_DRIFT"):
            candidate.derive(changed_durations=[[1,2]]*16)
        with self.assertRaisesRegex(candidate.CandidateError,"CANDIDATE_STROKE_DRIFT"):
            candidate.derive(changed_strokes={candidate.VARIANTS[0]:["D"]*16})
        with self.assertRaisesRegex(candidate.CandidateError,"FORCED_ELIGIBILITY"):
            candidate.derive(force_eligible=True)
        with self.assertRaisesRegex(candidate.CandidateError,"FOREIGN_ID"):
            candidate.derive(reserved_item="fg:item:999999")
        original=candidate.TXT_SHA
        try:
            candidate.TXT_SHA="0"*64
            with self.assertRaisesRegex(candidate.CandidateError,"TXT_PIN_DRIFT"):
                candidate.derive()
        finally:
            candidate.TXT_SHA=original

    def test_written_package_and_boundary_refusals(self):
        command=[sys.executable,str(candidate.ROOT/"Tools/parallel33_level007_ex001_relay_candidate.py")]
        verify=subprocess.run(command+["verify"],capture_output=True,text=True)
        self.assertEqual(verify.returncode,0,verify.stderr)
        rebuild=subprocess.run(command+["build"],capture_output=True,text=True)
        self.assertNotEqual(rebuild.returncode,0)
        self.assertIn("OUTPUT_EXISTS",rebuild.stderr)
        escape=subprocess.run(command+["build","--out","Build/parallel-33/escape"],
                              capture_output=True,text=True)
        self.assertNotEqual(escape.returncode,0)
        self.assertIn("OUTPUT_SCOPE",escape.stderr)


if __name__=="__main__":
    unittest.main()
