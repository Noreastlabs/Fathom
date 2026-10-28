"""Focused source, timing, provenance, native and refusal checks for P41."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import unittest

import parallel41_level011_two_case_candidate as candidate

OUT = candidate.ROOT / candidate.OUT
NATIVE = candidate.ROOT / "Build/parallel-13/four-shard-source-bundle-r01/bundle/bin/fathom_content_validate"
NATIVE_SHA = "a85c1b25d8cded12cbe273e4620bd5f33a711d06311d29583a0fdbed7748f714"


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = candidate.derive()

    def test_exact_original_routes_and_two_shift_landings(self):
        records = self.output["package.json"]["records"]
        self.assertEqual([r["context"]["local_code"] for r in records],
                         ["L011-S01-EX001:SHIFT_UP:E:PASS2",
                          "L011-S01-EX001:SHIFT_DOWN:e:PASS2"])
        expected = [[(1,5,1,45),(1,8,2,48),(1,7,1,47),(1,10,2,50)],
                    [(6,9,1,73),(6,8,2,72),(6,7,1,71),(6,6,2,70)]]
        for record, notes in zip(records, expected):
            self.assertEqual([(e["string"],e["fret"],e["finger"],e["midi"])
                              for e in record["events"]],notes)
            self.assertEqual([e["onset_q"] for e in record["events"]],
                             [[0,1],[1,4],[1,2],[3,4]])
            self.assertEqual([e["duration_q"] for e in record["events"]],[[1,4]]*4)
            self.assertEqual(record["control_scope"]["source_event_count"],4)
            self.assertFalse(record["runtime_eligible"])
            self.assertFalse(record["control_scope"]["whole_workbook_complete"])
            self.assertIsNone(record["rubric"])
            self.assertNotIn("fixed_bpm",record["context"])

    def test_complete_source_and_variant_provenance(self):
        package=self.output["package.json"]
        sidecar=self.output["source-provenance.json"]
        profile=self.output["expected-profile.json"]
        ids={e["event_id"] for r in package["records"] for e in r["events"]}
        self.assertEqual(ids,set(profile["event_sources"]))
        self.assertEqual(ids,set(sidecar["events"]))
        self.assertEqual(len({p["source_local_event_key"] for p in sidecar["events"].values()}),8)
        self.assertEqual([p["frame"] for p in sidecar["events"].values()],
                         ["P5","P7","P7","P9","P9","P7","P7","P5"])
        self.assertEqual([p["landing_note"] for p in sidecar["events"].values()],
                         [False,True,False,True]*2)
        self.assertEqual([p["source_txt_line"] for p in sidecar["events"].values()],
                         [54]*4+[57]*4)
        self.assertTrue(all(p["shift_boundary_after_notes"]==[1,3]
                            for p in sidecar["events"].values()))
        for record in package["records"]:
            self.assertEqual([v["pick_start"] for v in record["variants"]],["D","U"])
            self.assertTrue(all(v["accent_policy"]=="even" for v in record["variants"]))
            self.assertEqual(set(record["source_refs"]),set(package["sources"]))
        self.assertEqual(sidecar["variant_strokes"],
                         {vid:(["D","U","D","U"] if j==0 else ["U","D","U","D"])
                          for pair in candidate.VARIANTS for j,vid in enumerate(pair)})

    def test_provisional_ids_and_native_reference_without_admission(self):
        self.assertEqual([e["id"] for e in self.output["identity-registry.json"]["entities"]],
                         ["fg:course:000001","fg:workbook:000011",
                          "fg:module:001151","fg:item:001151",
                          "fg:variant:007424","fg:variant:007425",
                          "fg:module:001152","fg:item:001152",
                          "fg:variant:007426","fg:variant:007427"])
        self.assertEqual(set(self.output["candidate-allocation.json"]["records"]),set(candidate.ITEMS))
        self.assertEqual(self.output["expected-profile.json"]["reference_package"],
                         self.output["package.json"])
        report=json.loads((OUT/"native-report.json").read_text())
        self.assertEqual(report["exit_code"],2)
        self.assertTrue(report["valid_reference"])
        self.assertFalse(report["curriculum_playback_authorized"])
        self.assertEqual((report["coverage"]["observed_records"],report["coverage"]["events"],
                          report["coverage"]["variants"]),(2,8,4))
        self.assertEqual([(i["code"],i["record"]) for i in report["issues"]],
                         [("MODEL_not_admitted",candidate.ITEMS[0]),
                          ("MODEL_not_admitted",candidate.ITEMS[1])])

    def test_mutated_source_timing_identity_stroke_and_forced_eligibility_refuse(self):
        facts=[s["facts"] for s in candidate.source_facts()[2]]
        changed=copy.deepcopy(facts);changed[1][3]=(6,7,2,71,"P5")
        cases=[("CANDIDATE_SOURCE_DRIFT",{"changed_facts":changed}),
               ("CANDIDATE_TIMING_DRIFT",{"changed_onsets":[[0,1]]*4}),
               ("CANDIDATE_DURATION_DRIFT",{"changed_durations":[[1,2]]*4}),
               ("CANDIDATE_STROKE_DRIFT",{"changed_strokes":{candidate.VARIANTS[0][0]:["D"]*4}}),
               ("FOREIGN_ID",{"reserved_item":"fg:item:999999"}),
               ("FORCED_ELIGIBILITY",{"force_eligible":True})]
        for code,kwargs in cases:
            with self.subTest(code=code),self.assertRaisesRegex(candidate.CandidateError,code):
                candidate.derive(**kwargs)
        original=candidate.TXT_SHA
        try:
            candidate.TXT_SHA="0"*64
            with self.assertRaisesRegex(candidate.CandidateError,"TXT_PIN_DRIFT"):
                candidate.derive()
        finally:
            candidate.TXT_SHA=original

    def test_frozen_native_negative_fixtures(self):
        self.assertEqual(hashlib.sha256(NATIVE.read_bytes()).hexdigest(),NATIVE_SHA)
        package=self.output["package.json"]
        fixtures={}
        for name in ("pitch","onset","duration","source","identity","forced_eligibility"):
            altered=copy.deepcopy(package)
            if name=="pitch": altered["records"][0]["events"][1]["midi"]+=1
            if name=="onset": altered["records"][0]["events"][1]["onset_q"]=[0,1]
            if name=="duration": altered["records"][0]["events"][1]["duration_q"]=[1,2]
            if name=="source": altered["sources"]["L11-TXT1-51-57"]["sha256"]="0"*64
            if name=="identity": altered["records"][0]["id"]="fg:item:999999"
            if name=="forced_eligibility": altered["records"][0]["runtime_eligible"]=True
            package_path=OUT/f"negative-{name}-package.json"
            report_path=OUT/f"negative-{name}-report.json"
            if report_path.exists():
                replay=2
                while (OUT/f"negative-{name}-report-replay-{replay:02d}.json").exists():
                    replay+=1
                report_path=OUT/f"negative-{name}-report-replay-{replay:02d}.json"
            package_path.write_bytes(candidate.encode(altered))
            cmd=[str(NATIVE),"--package",str(package_path),"--registry",str(OUT/"identity-registry.json"),
                 "--profile",str(OUT/"expected-profile.json"),"--profile-sha256",
                 hashlib.sha256((OUT/"expected-profile.json").read_bytes()).hexdigest(),
                 "--source-root",str(candidate.ROOT),"--report",str(report_path)]
            run=subprocess.run(cmd,capture_output=True,text=True)
            report=json.loads(report_path.read_text())
            self.assertEqual(run.returncode,1,(name,run.stdout,run.stderr))
            self.assertFalse(report["valid_reference"],name)
            codes=[issue["code"] for issue in report["issues"]]
            required={"pitch":"MODEL_pitch_position","onset":"RECORD_FIDELITY",
                      "duration":"RECORD_FIDELITY","source":"SOURCE_HASH",
                      "identity":"RECORD_IDENTITY","forced_eligibility":"RUNTIME_NOT_ADMITTED"}
            self.assertIn(required[name],codes,name)
            fixtures[name]={"exit_code":run.returncode,"valid_reference":report["valid_reference"],
                            "issue_codes":codes,"package_sha256":hashlib.sha256(package_path.read_bytes()).hexdigest(),
                            "report_sha256":hashlib.sha256(report_path.read_bytes()).hexdigest(),
                            "stdout":run.stdout,"stderr":run.stderr}
        (OUT/"negative-checks.json").write_bytes(candidate.encode(fixtures))

    def test_written_bytes_and_output_boundary(self):
        command=[sys.executable,str(candidate.ROOT/"Tools/parallel41_level011_two_case_candidate.py")]
        verify=subprocess.run(command+["verify"],capture_output=True,text=True)
        self.assertEqual(verify.returncode,0,verify.stderr)
        rebuild=subprocess.run(command+["build"],capture_output=True,text=True)
        self.assertNotEqual(rebuild.returncode,0)
        self.assertIn("OUTPUT_EXISTS",rebuild.stderr)
        escape=subprocess.run(command+["build","--out","Build/parallel-41/escape"],
                              capture_output=True,text=True)
        self.assertNotEqual(escape.returncode,0)
        self.assertIn("OUTPUT_SCOPE",escape.stderr)


if __name__=="__main__":
    unittest.main()
