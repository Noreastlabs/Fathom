"""Focused source, identity, timing and refusal tests for one Level 8 cell."""
import json
import unittest

import parallel04_level008_ex001_first_shift_candidate as candidate


class Level008FirstShiftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = candidate.derive()
        cls.record = cls.packet["package.json"]["records"][0]

    def test_eight_sequential_low_e_notes_and_center_shift(self):
        notes = self.record["events"]
        self.assertEqual(len(notes), 8)
        self.assertEqual([(n["string"], n["fret"], n["finger"], n["midi"]) for n in notes],
                         [(1, 5, 1, 45), (1, 6, 2, 46), (1, 5, 1, 45), (1, 6, 2, 46),
                          (1, 7, 1, 47), (1, 8, 2, 48), (1, 7, 1, 47), (1, 8, 2, 48)])
        self.assertEqual([n["onset_q"] for n in notes],
                         [[0, 1], [1, 4], [1, 2], [3, 4], [1, 1], [5, 4], [3, 2], [7, 4]])
        self.assertEqual([n["duration_q"] for n in notes], [[1, 4]] * 8)
        provenance = self.packet["source-provenance.json"]["events"]
        self.assertEqual([provenance[n["event_id"]]["frame"] for n in notes], ["P5"] * 4 + ["P7"] * 4)
        self.assertEqual([provenance[n["event_id"]]["cell"] for n in notes], [1] * 4 + [2] * 4)

    def test_source_closure_and_option_boundary(self):
        sources = self.packet["package.json"]["sources"]
        self.assertEqual(set(sources), set(self.record["source_refs"]))
        self.assertEqual(set(self.packet["expected-profile.json"]["event_sources"]),
                         {n["event_id"] for n in self.record["events"]})
        for eid, provenance in self.packet["source-provenance.json"]["events"].items():
            self.assertEqual(provenance["source_txt_ref"], self.packet["expected-profile.json"]["event_sources"][eid])
            self.assertEqual(provenance["source_txt_line"], 38)
            self.assertEqual(provenance["timing_option"], "PASS2_connected_straight_sixteenths")
        self.assertIn("straight sixteenths", self.record["timing"]["basis"])
        self.assertNotIn("fixed_bpm", self.record["context"])
        self.assertFalse(self.record["control_scope"]["whole_workbook_complete"])

    def test_reserved_ids_variants_and_nonadmission(self):
        self.assertEqual((self.record["id"], self.record["module_id"], self.record["workbook_id"]),
                         ("fg:item:001146", "fg:module:001146", "fg:workbook:000008"))
        self.assertEqual([(v["id"], v["pick_start"], v["accent_policy"], v["tail_pause"])
                          for v in self.record["variants"]],
                         [("fg:variant:007414", "D", "even", None),
                          ("fg:variant:007415", "U", "even", None)])
        self.assertEqual(self.packet["source-provenance.json"]["variant_strokes"],
                         {"fg:variant:007414": ["D", "U"] * 4,
                          "fg:variant:007415": ["U", "D"] * 4})
        self.assertFalse(self.record["runtime_eligible"])
        self.assertFalse(self.packet["summary.json"]["admitted"])

    def test_source_mutation_and_forced_eligibility_refused(self):
        facts = candidate.source_facts()[2]
        altered = list(facts)
        altered[4] = (1, 8, 1, 48, "P7")
        with self.assertRaisesRegex(candidate.CandidateError, "CANDIDATE_SOURCE_DRIFT"):
            candidate.derive(changed_facts=altered)
        with self.assertRaisesRegex(candidate.CandidateError, "FORCED_ELIGIBILITY"):
            candidate.derive(force_eligible=True)
        with self.assertRaisesRegex(candidate.CandidateError, "ID_RESERVATION_DRIFT"):
            candidate.derive(reserved_item="fg:item:001147")

    def test_saved_packet_matches_fresh_source_derivation(self):
        for name in candidate.NAMES:
            with self.subTest(name=name):
                self.assertEqual((candidate.ROOT / candidate.OUT / name).read_bytes(),
                                 candidate.encode(self.packet[name]))

    def test_native_report_reference_only(self):
        report = json.loads((candidate.ROOT / candidate.OUT / "native-report-r03.json").read_text())
        self.assertEqual(report["exit_code"], 2)
        self.assertTrue(report["valid_reference"])
        self.assertFalse(report["curriculum_playback_authorized"])
        self.assertEqual(report["coverage"]["events"], 8)
        self.assertEqual(report["coverage"]["variants"], 2)
        self.assertEqual([i["code"] for i in report["issues"]], ["MODEL_not_admitted"])


if __name__ == "__main__":
    unittest.main()
