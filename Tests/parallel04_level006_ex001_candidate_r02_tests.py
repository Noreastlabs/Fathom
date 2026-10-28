"""Focused musical/source and refusal checks for the Level6 first-cell candidate."""
import copy
import json
import unittest

import parallel04_level006_ex001_candidate_r02 as candidate


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = candidate.derive()

    def test_exact_first_cell_and_silent_string(self):
        record = self.output["package.json"]["records"][0]
        notes = record["events"]
        self.assertEqual([(n["string"], n["fret"], n["finger"], n["midi"]) for n in notes],
                         [(1, 5, 1, 45), (1, 6, 2, 46), (1, 5, 1, 45), (3, 6, 2, 56)])
        self.assertEqual([n["onset_q"] for n in notes], [[0, 1], [1, 4], [1, 2], [3, 4]])
        self.assertEqual([n["duration_q"] for n in notes], [[1, 4]] * 4)
        self.assertEqual([p["silent_intervening_string"] for p in
                          self.output["source-provenance.json"]["events"].values()], ["A"] * 4)
        self.assertEqual(self.output["source-provenance.json"]["variant_strokes"],
                         {"fg:variant:007410": ["D", "U", "D", "U"],
                          "fg:variant:007411": ["U", "D", "U", "D"]})

    def test_source_closure_and_nonadmission(self):
        package = self.output["package.json"]
        record = package["records"][0]
        self.assertEqual(set(package["sources"]), set(record["source_refs"]))
        self.assertEqual([(v["id"], v["pick_start"]) for v in record["variants"]],
                         [("fg:variant:007410", "D"), ("fg:variant:007411", "U")])
        self.assertEqual((record["id"], record["module_id"], record["content_revision"]),
                         ("fg:item:001144", "fg:module:001144", 1))
        self.assertFalse(record["runtime_eligible"])
        self.assertFalse(self.output["summary.json"]["admitted"])

    def test_every_event_provenance_ref_is_declared_and_profile_bound(self):
        package = self.output["package.json"]
        record = package["records"][0]
        profile = self.output["expected-profile.json"]
        sidecar = self.output["source-provenance.json"]
        self.assertEqual(set(sidecar["events"]), {e["event_id"] for e in record["events"]})
        self.assertEqual(set(sidecar["events"]), set(profile["event_sources"]))
        for event_id, provenance in sidecar["events"].items():
            with self.subTest(event_id=event_id):
                source_ref = provenance["source_txt_ref"]
                self.assertEqual(source_ref, "L6-TXT1-34-41")
                self.assertIn(source_ref, package["sources"])
                self.assertIn(source_ref, record["source_refs"])
                self.assertEqual(profile["event_sources"][event_id], source_ref)
                self.assertEqual(provenance["source_pdf_page"], package["sources"]["L6-PDF1-p2"]["page"])

    def test_registry_and_profile_have_only_level6_case_labels(self):
        registry = self.output["identity-registry.json"]
        profile = self.output["expected-profile.json"]
        labels = [entity["label"] for entity in registry["entities"] if entity["kind"] != "course"]
        self.assertTrue(all("Level6" in label or "Level 6" in label or "first-E-D-cell" in label for label in labels))
        self.assertFalse(any("Level12" in label or "B-major" in label for label in labels))
        self.assertEqual(profile["degree_roots"], {})
        self.assertEqual(profile["reference_registry"], registry)
        self.assertEqual(profile["reference_package"]["records"][0]["id"], "fg:item:001144")
        self.assertTrue(all(source["path"].endswith("108_Finger_Permutations_Level_6_Odd_Count_String_Skip_Transfer." + source["format"])
                            for source in profile["reference_package"]["sources"].values()))

    def test_changed_source_fact_refused(self):
        proposal = candidate.read(candidate.ROOT, candidate.PROPOSAL)
        changed = copy.deepcopy(proposal["records"][0]["schema1_fields"])
        changed["events"][3]["fret"] = 7
        with self.assertRaisesRegex(candidate.CandidateError, "CANDIDATE_SOURCE_DRIFT"):
            candidate.derive(override=changed)

    def test_undeclared_event_source_ref_refused(self):
        package = self.output["package.json"]
        record = package["records"][0]
        profile = self.output["expected-profile.json"]
        changed = copy.deepcopy(self.output["source-provenance.json"]["events"])
        changed[record["events"][0]["event_id"]]["source_txt_ref"] = "L6-TXT1-34-48"
        with self.assertRaisesRegex(candidate.CandidateError, "EVENT_SOURCE_CLOSURE"):
            candidate.check_event_source_closure(record, package["sources"], profile["event_sources"], changed)

    def test_forced_admission_refused(self):
        with self.assertRaisesRegex(candidate.CandidateError, "FORCED_ELIGIBILITY"):
            candidate.derive(force_eligible=True)

    def test_saved_build_matches_current_derivation(self):
        for name in candidate.NAMES:
            with self.subTest(name=name):
                self.assertEqual((candidate.ROOT / candidate.OUT / name).read_bytes(),
                                 candidate.encode(self.output[name]))

    def test_native_report_is_reference_only(self):
        report = json.loads((candidate.ROOT / candidate.OUT / "native-report.json").read_bytes())
        self.assertEqual(report["exit_code"], 2)
        self.assertTrue(report["valid_reference"])
        self.assertFalse(report["curriculum_playback_authorized"])
        self.assertEqual(report["coverage"]["events"], 4)
        self.assertEqual(report["coverage"]["variants"], 2)
        self.assertEqual([issue["code"] for issue in report["issues"]], ["MODEL_not_admitted"])


if __name__ == "__main__":
    unittest.main()
