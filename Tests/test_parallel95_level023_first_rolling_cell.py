"""P95 exact first-card and native reference/refusal checks."""
from __future__ import annotations
import copy
import json
import subprocess
import sys
import unittest
from fractions import Fraction
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"Tools"))
import parallel95_level023_first_rolling_cell as c
OUT=c.ROOT/c.OUT

def native(package,report):
    profile=OUT/"expected-profile.json"
    run=subprocess.run([str(c.ROOT/c.NATIVE),"--package",str(package),
                        "--registry",str(OUT/"identity-registry.json"),
                        "--profile",str(profile),"--profile-sha256",c.sha(profile.read_bytes()),
                        "--source-root",str(c.ROOT),"--report",str(report)],
                       text=True,capture_output=True)
    return run,json.loads(report.read_text())

class FirstRollingCellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=c.derive()
        cls.events=cls.output["package.json"]["records"][0]["events"]
        cls.side=cls.output["source-provenance.json"]["events"]
    def test_original_first_card_worked_example_and_36_contacts(self):
        lines,pages,notes=c.source_facts()
        self.assertEqual(lines[64],pages[0][22])
        self.assertEqual(lines[64],pages[2][7])
        self.assertEqual(len(notes),36)
        self.assertEqual([n["degree"] for n in notes[15:21]],["b6","b7","8","8","b7","b6"])
        self.assertEqual([(n["string"],n["fret"],n["finger"]) for n in notes[17:19]],
                         [("D",7,3),("D",7,3)])
        self.assertEqual([n["string"] for n in notes[:3]],["E"]*3)
        self.assertEqual([n["string"] for n in notes[-3:]],["E"]*3)
        for i,(note,event) in enumerate(zip(notes,self.events)):
            detail=self.side[event["event_id"]]
            self.assertEqual((event["string"],event["fret"],event["finger"],event["midi"],
                              event["spelling"]),(*c.OPEN[note["string"]][:1],
                              note["fret"],note["finger"],note["midi"],note["spelling"]))
            self.assertEqual((detail["source_group"],detail["source_group_slot"],
                              detail["source_degree"],detail["source_txt_tab_line"]),
                             (i//3+1,i%3+1,note["degree"],
                              67+("e","B","G","D","A","E").index(note["string"])))
            self.assertEqual(detail["source_txt_ref"],"L23-TXT-RUNG01-62-73")
            self.assertEqual(detail["source_pdf_ref"],"L23-PDF-CARD01-P3")
        self.assertEqual(set(self.side),{e["event_id"] for e in self.events})
    def test_triplet_grid_and_uninterrupted_pick_cycles(self):
        self.assertEqual(len(self.events),36)
        for i,e in enumerate(self.events):
            self.assertEqual(e["onset_q"],list(Fraction(i,3).as_integer_ratio()))
            self.assertEqual(e["duration_q"],[1,3])
            self.assertEqual(e["degree_contexts"]["A-natural-minor"]["source_label"],
                             self.side[e["event_id"]]["source_degree"])
        self.assertEqual(self.events[17]["degree_contexts"]["A-natural-minor"]["ordinal"],8)
        self.assertEqual(self.events[18]["degree_contexts"]["A-natural-minor"]["ordinal"],8)
        record=self.output["package.json"]["records"][0]
        self.assertFalse(record["runtime_eligible"])
        self.assertIsNone(record["rubric"])
        self.assertNotIn("fixed_bpm",record["timing"])
        self.assertEqual(self.output["summary.json"]["case_end_q"],[12,1])
        self.assertEqual(self.output["summary.json"]["last_onset_q"],[35,3])
        for variant,start in zip(record["variants"],("D","U")):
            self.assertEqual(variant["event_ids"],[e["event_id"] for e in self.events])
            want=[start if i%2==0 else ("U" if start=="D" else "D") for i in range(36)]
            self.assertEqual(self.output["source-provenance.json"]["variant_strokes"][variant["id"]],want)
            self.assertEqual([self.side[e["event_id"]]["pick_strokes"][variant["id"]]
                              for e in self.events],want)
        self.assertEqual(len(record["variants"])*len(self.events),72)
    def test_native_valid_reference_playback_withheld(self):
        report=json.loads((OUT/"native-report-r02.json").read_text())
        self.assertEqual(c.sha((c.ROOT/c.NATIVE).read_bytes()),c.PINS[c.NATIVE])
        self.assertTrue(report["valid_reference"])
        self.assertFalse(report["curriculum_playback_authorized"])
        self.assertEqual([(x["code"],x["record"]) for x in report["issues"]],
                         [("MODEL_not_admitted",c.ITEM)])
        self.assertEqual(tuple(report["coverage"][k] for k in
                               ("events","variants","variant_event_memberships")),(36,2,72))
        for variant in report["variants"]:
            self.assertFalse(variant["curriculum_playback_authorized"])
            self.assertEqual(len(variant["model"]["events"]),36)
    def test_generator_causal_refusals(self):
        for kw,code in (({"force_eligible":True},"FORCED_ELIGIBILITY"),
                        ({"forced_bpm":120},"FIXED_BPM_UNAUTHORIZED"),
                        ({"reserved_item":"fg:item:000001"},"FOREIGN_ID"),
                        ({"grouping":"even_subdivision"},"SOURCE_EVENT_TIME_REQUIRED"),
                        ({"changed_contacts":[]},"CONTACT_DRIFT"),
                        ({"changed_onsets":[]},"TIMING_DRIFT"),
                        ({"changed_durations":[]},"DURATION_DRIFT"),
                        ({"changed_strokes":{}},"STROKE_DRIFT")):
            with self.subTest(code=code),self.assertRaisesRegex(c.CandidateError,code):
                c.derive(**kw)
    def test_native_causal_refusals(self):
        checks=[]
        def check(name,code,edit):
            pkg=copy.deepcopy(self.output["package.json"]);edit(pkg)
            package=OUT/f"negative-{name}-package.json"
            report=OUT/f"negative-{name}-report.json"
            package.write_bytes(c.encode(pkg))
            report.unlink(missing_ok=True)
            run,out=native(package,report)
            self.assertEqual(run.returncode,1,(name,run.stdout,run.stderr))
            self.assertFalse(out["valid_reference"])
            codes=sorted({i["code"] for i in out["issues"]})
            self.assertIn(code,codes)
            checks.append({"name":name,"exit_code":run.returncode,"issue_codes":codes,
                           "package_sha256":c.sha(package.read_bytes()),
                           "report_sha256":c.sha(report.read_bytes())})
        check("minor-degree","MODEL_degree_pitch",lambda p:p["records"][0]["events"][2]["degree_contexts"]["A-natural-minor"].update(source_label="3",alteration=0))
        check("minor-pitch","MODEL_pitch_position",lambda p:p["records"][0]["events"][2].update(midi=49))
        check("wrong-fret","MODEL_pitch_position",lambda p:p["records"][0]["events"][17].update(fret=5))
        check("triplet-onset","MODEL_event_order",lambda p:p["records"][0]["events"][3].update(onset_q=[1,2]))
        check("triplet-duration","MODEL_string_overlap",lambda p:p["records"][0]["events"][0].update(duration_q=[1,2]))
        check("wrong-identity","RECORD_IDENTITY",lambda p:p["records"][0].update(id="fg:item:009999"))
        check("forced-eligible","RUNTIME_NOT_ADMITTED",lambda p:p["records"][0].update(runtime_eligible=True))
        check("source-hash","SOURCE_HASH",lambda p:p["sources"]["L23-TXT-RUNG01-62-73"].update(sha256="0"*64))
        check("wrong-pick","UNSUPPORTED_VALUE",lambda p:p["records"][0]["variants"][0].update(pick_start="X"))
        check("missing-membership","RECORD_FIDELITY",lambda p:p["records"][0]["variants"][0]["event_ids"].pop())
        (OUT/"negative-checks.json").write_bytes(c.encode({"checks":checks}))
    def test_frozen_packet_bytes(self):
        for name in c.NAMES:
            self.assertEqual((OUT/name).read_bytes(),c.encode(self.output[name]))

if __name__=="__main__":unittest.main()
