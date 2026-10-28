"""Focused source, harmony and boundary checks for detached Level 37."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel_07_level037_whole_candidate as lane  # noqa: E402


class Level37CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = (ROOT / lane.TXT_REL).read_bytes()
        cls.pdf = (ROOT / lane.PDF_REL).read_bytes()
        cls.candidate = lane.build_candidate(txt_data=cls.txt, pdf_data=cls.pdf)

    def test_five_modules_count_contacts_and_harmony(self) -> None:
        data = self.candidate
        modules = data["modules"]
        self.assertEqual(data["written_workout_note_count"], 496)
        self.assertEqual([modules[key]["note_count"] for key in (
            "A_target_cells", "B_voice_leading", "C_target_phrases", "D_completion_cadences", "E_model_chorus"
        )], [168, 60, 160, 60, 48])
        self.assertEqual(data["pentatonic_pool"], list(lane.POOL))
        self.assertEqual(data["harmony"]["progression_twelve_bar"], list(lane.PROGRESSION_E))
        self.assertEqual(data["harmony"]["role_matrix"], lane.ROLE)
        all_events = []
        a = modules["A_target_cells"]["positions"]
        self.assertEqual(len(a), 5)
        for position_index, position in enumerate(a, start=1):
            self.assertEqual(position["position"], position_index)
            self.assertEqual([cell["roman"] for cell in position["cells"]], ["I", "IV", "V"])
            for cell in position["cells"]:
                events = cell["events"]
                target_contacts = cell["target_list"]
                self.assertEqual(len(events), cell["note_count"])
                self.assertEqual(len(events), len(target_contacts) * 2)
                contacts = [{"tone": event["tone"], "string": event["string"], "fret": event["fret"]}
                            for event in events]
                self.assertEqual(contacts, target_contacts + list(reversed(target_contacts)))
                self.assertEqual([event["finger_digit"] for event in events],
                                 list(reversed([event["finger_digit"] for event in events])))
                self.assertTrue(all(event["tone"] in lane.STRONG[cell["chord"]] for event in events))
                all_events.extend(events)
        b = modules["B_voice_leading"]["positions"]
        self.assertEqual(len(b), 5)
        for position in b:
            self.assertEqual([route["name"] for route in position["routes"]],
                             ["COMMON-TONE", "GUIDE-TONE", "FIFTH-LED"])
            for route in position["routes"]:
                self.assertEqual(len(route["events"]), 4)
                self.assertEqual([event["chord"] for event in route["events"]], list(lane.PROGRESSION_C))
                self.assertTrue(all(event["tone"] in lane.STRONG[event["chord"]] for event in route["events"]))
                all_events.extend(route["events"])
        c = modules["C_target_phrases"]["phrases"]
        self.assertEqual(len(c), 5)
        for phrase in c:
            self.assertEqual(len(phrase["events"]), 32)
            self.assertEqual([bar["chord"] for bar in phrase["bars"]], list(lane.PROGRESSION_C))
            first = [event for event in phrase["events"] if event["slot_in_bar"] == 1]
            self.assertEqual([{"chord": event["chord"], "tone": event["tone"], "role": event["role"]}
                              for event in first], phrase["beat_one_targets"])
            self.assertTrue(all(event["tone"] in lane.STRONG[event["chord"]] for event in first))
            all_events.extend(phrase["events"])
        d = modules["D_completion_cadences"]
        self.assertEqual(len(d["choices"]), 5)
        self.assertEqual(len(d["cadences"]), 5)
        for index, cadence in enumerate(d["cadences"]):
            self.assertEqual(len(cadence["events"]), 12)
            self.assertEqual([bar["chord"] for bar in cadence["bars"]], list(lane.PROGRESSION_D))
            self.assertEqual([event["tone"] for event in cadence["events"] if event["completion_tone"]],
                             ["D*", "G#*"])
            self.assertIn(cadence["events"][0]["string"] + str(cadence["events"][0]["fret"]), d["choices"][index]["D"])
            self.assertIn(cadence["events"][4]["string"] + str(cadence["events"][4]["fret"]), d["choices"][index]["G#"])
            all_events.extend(cadence["events"])
        e = modules["E_model_chorus"]
        self.assertEqual(len(e["bars"]), 12)
        self.assertEqual(len(e["events"]), 48)
        self.assertEqual([bar["chord"] for bar in e["bars"]], list(lane.PROGRESSION_E))
        self.assertEqual([event["tone"] for event in e["events"] if event["completion_tone"]],
                         ["D*", "G#*", "G#*"])
        self.assertEqual([event["tone"] for event in e["events"] if event["slot_in_bar"] == 1],
                         [entry["model_beat_one"] for entry in e["chart"]])
        all_events.extend(e["events"])
        self.assertEqual(len(all_events), 496)
        self.assertEqual(Counter(event["tone"] for event in all_events if event.get("completion_tone")),
                         Counter({"D*": 6, "G#*": 7}))
        for event in all_events:
            self.assertEqual(event["role"], lane.ROLE[event["chord"]][event["tone"]])
            self.assertEqual((lane.OPEN_MIDI[event["string"]] + event["fret"]) % 12,
                             lane._pitch_class(event["tone"]))
            self.assertIsNone(event["onset_q"])
            self.assertIsNone(event["duration_q"])
        self.assertIsNone(data["canonical_item_id"])
        self.assertIsNone(data["canonical_variant_id"])
        self.assertIsNone(data["fixed_bpm"])
        self.assertFalse(data["runtime_eligible"])
        self.assertFalse(data["admitted"])

    def test_pdf_parity_and_supplemental_separation(self) -> None:
        txt_lines = self.txt.decode("utf-8").splitlines()
        pages = lane._pdf_pages(self.pdf)
        txt_rows = lane._staff_counter(txt_lines)
        pdf_rows = sum((lane._staff_counter(page) for page in pages), Counter())
        self.assertEqual(sum(txt_rows.values()), 279)
        self.assertEqual(sum(pdf_rows.values()), 287)
        self.assertFalse(txt_rows - pdf_rows)
        self.assertEqual(pdf_rows - txt_rows, Counter(lane.PDF_EXAMPLE_ROWS))
        supplemental = self.candidate["supplemental_pdf_only"]
        self.assertFalse(supplemental["counted_in_written_workout"])
        self.assertEqual(supplemental["note_count"], 16)
        self.assertEqual(len(supplemental["events"]), 16)
        self.assertEqual(supplemental["source_ref"], "L37-PDF1-p1")
        self.assertEqual(self.candidate["exceptions"][0]["kind"], "pdf_supplemental_example")
        self.assertEqual(self.candidate["written_workout_note_count"], 496)
        self.assertEqual(self.candidate["modules"]["A_target_cells"]["positions"][0]["cells"][0]["target_list_text"],
                         "Targets: A(E5), C#(A4), E(A7), A(D7), C#(G6), E(B5), A(e5)")

    def test_pins_and_malformed_harmonic_mutations(self) -> None:
        changed = bytearray(self.txt)
        changed[0] = ord("X")
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L37-TXT"):
            lane.build_candidate(txt_data=bytes(changed), pdf_data=self.pdf)
        changed_pdf = bytearray(self.pdf)
        changed_pdf[-1] ^= 1
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L37-PDF"):
            lane.build_candidate(txt_data=self.txt, pdf_data=bytes(changed_pdf))
        source = self.txt.decode("utf-8")
        mutations = [
            ("Nte|A---C#--E---A---", "Nte|B---C#--E---A---", "CHORD_ROLE_OR_COMPLETION_INVALID"),
            ("Rol|R---3---5---R---", "Rol|R---5---5---R---", "CHORD_ROLE_OR_COMPLETION_INVALID"),
            ("E  |5---------------------------------------------------5---|",
             "E  |6---------------------------------------------------5---|", "TAB_NOTE_PITCH_MISMATCH"),
            ("COMMON-TONE: A(e5) R", "COMMON-TONE: A(e5) 3", "VOICE_ROUTE_ROLE_INVALID"),
            ("Nte|D*--F#--A---F#--", "Nte|E---F#--A---F#--", "CHORD_ROLE_OR_COMPLETION_INVALID"),
        ]
        for before, after, expected in mutations:
            self.assertIn(before, source)
            modified = source.replace(before, after, 1).encode("utf-8")
            with self.subTest(expected=expected), patch.object(lane, "TXT_BYTES", len(modified)), patch.object(
                lane, "TXT_SHA256", hashlib.sha256(modified).hexdigest()
            ):
                with self.assertRaisesRegex(lane.CandidateError, expected):
                    lane.build_candidate(txt_data=modified, pdf_data=self.pdf)

    def test_output_is_deterministic_and_confined(self) -> None:
        expected = (json.dumps(self.candidate, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        output = ROOT / lane.BUILD_REL / "candidate.json"
        self.assertEqual(output.read_bytes(), expected)
        self.assertEqual(hashlib.sha256(expected).hexdigest(), "d7f9243c38027676a1c3fb3bec9fc31d07a41d88a145aa33da27236443b7e3aa")
        with self.assertRaisesRegex(lane.CandidateError, "OUTPUT_EXISTS"):
            lane.write_candidate(output)
        with tempfile.TemporaryDirectory() as tempdir:
            outside = Path(tempdir) / "candidate.json"
            with self.assertRaisesRegex(lane.CandidateError, "OUTPUT_OUTSIDE_LANE_BUILD"):
                lane.write_candidate(outside)
            link = ROOT / lane.BUILD_REL / "test-symlink.json"
            try:
                link.symlink_to(outside)
                with self.assertRaisesRegex(lane.CandidateError, "OUTPUT_INVALID"):
                    lane.write_candidate(link)
            finally:
                link.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
