"""Level 9 Set 8 printed source, route, shift and refusal checks."""

from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from Tools import curriculum_level009_set08_candidate as set8


ROOT = Path(__file__).resolve().parents[1]


class Level9Set8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = (ROOT / set8.TXT_REL).read_bytes()
        cls.pdf = (ROOT / set8.PDF_REL).read_bytes()
        cls.candidate = set8.build_candidate()

    def test_exact_set_boundary_source_and_determinism(self) -> None:
        first, second = set8.build_candidate(), set8.build_candidate()
        self.assertEqual(first, second)
        self.assertEqual(first["source"]["txt_sha256"], set8.TXT_PIN[1])
        self.assertEqual(first["source"]["pdf_sha256"], set8.PDF_PIN[1])
        self.assertEqual(first["source"]["selected_pdf_page"], 9)
        self.assertEqual([row["code"] for row in first["records"]], list(set8.CODES))
        self.assertEqual([row["exercise_number"] for row in first["records"]], [f"{n:03d}" for n in range(85, 97)])
        self.assertEqual(first["records"][0]["source_refs"], {"txt": "L9-TXT1-1403-1417", "pdf": "L9-PDF1-p9"})
        self.assertEqual(first["records"][-1]["source_refs"], {"txt": "L9-TXT1-1579-1593", "pdf": "L9-PDF1-p9"})
        self.assertEqual(len(first["records"]), 12)
        self.assertEqual(sum(len(direction["sequential_one_string_routes"]) for record in first["records"]
                             for direction in record["directions"]), 144)
        self.assertEqual(sum(len(cell["notes"]) for record in first["records"]
                             for direction in record["directions"]
                             for route in direction["sequential_one_string_routes"]
                             for cell in route["cells"]), 576)

    def test_printed_first_middle_last_routes_and_hand_frame_shift(self) -> None:
        for index, up_frets, down_frets in ((0, [8, 5, 9, 7], [10, 7, 7, 5]),
                                           (6, [8, 6, 7, 8], [10, 8, 5, 6]),
                                           (11, [8, 6, 9, 10], [10, 8, 7, 8])):
            record = self.candidate["records"][index]
            up, down = record["directions"]
            self.assertEqual(up["route_order"], ["E", "A", "D", "G", "B", "e"])
            self.assertEqual(down["route_order"], ["e", "B", "G", "D", "A", "E"])
            self.assertEqual(up["position_order"], ["P5", "P7"])
            self.assertEqual(down["position_order"], ["P7", "P5"])
            for direction, expected, shift in ((up, up_frets, 2), (down, down_frets, -2)):
                for route in direction["sequential_one_string_routes"]:
                    notes = [note for cell in route["cells"] for note in cell["notes"]]
                    self.assertEqual([note["fret"] for note in notes], expected)
                    self.assertEqual([note["finger_digit"] for note in notes], list(record["code"]))
                    self.assertEqual([note["ordinal"] for note in notes], [1, 2, 3, 4])
                    self.assertEqual({note["string"] for note in notes}, {route["string"]})
                    self.assertEqual([note["position"] for note in notes], [direction["position_order"][0]] * 2 + [direction["position_order"][1]] * 2)
                    self.assertEqual(route["shift_after_note"], 2)
                    self.assertEqual(route["whole_hand_frame_shift_frets"], shift)
                    self.assertFalse(route["melodic_interval_inferred"])
        # Exercise 088 falls from fret 10 to 7 after an upward frame shift.
        middle = self.candidate["records"][3]["directions"][0]["sequential_one_string_routes"][0]
        self.assertEqual([note["fret"] for cell in middle["cells"] for note in cell["notes"]], [8, 5, 10, 7])

    def test_guidance_and_non_admission_are_explicit(self) -> None:
        result = self.candidate
        self.assertIn("not the melodic interval", result["instructions"]["movement_text"])
        self.assertIn("D-U | D-U and U-D | U-D", result["instructions"]["practice_text"])
        self.assertFalse(result["admitted"] or result["imported"] or result["runtime_eligible"] or result["runtime_admitted"])
        self.assertFalse(result["whole_workbook_complete"])
        for record in result["records"]:
            self.assertFalse(record["admitted"] or record["imported"] or record["runtime_eligible"] or record["runtime_admitted"])
            for key in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "note_per_click", "fixed_bpm"):
                self.assertIsNone(record[key])
            for direction in record["directions"]:
                self.assertEqual(len(direction["txt_rows_high_to_low"]), 6)
                self.assertEqual(direction["pdf_one_string_template"], "S" + direction["txt_rows_high_to_low"][0][1:])
                for route in direction["sequential_one_string_routes"]:
                    for cell in route["cells"]:
                        for note in cell["notes"]:
                            self.assertIsNone(note["onset_q"])
                            self.assertIsNone(note["duration_q"])

    def test_txt_boundary_code_route_and_fret_errors_refuse(self) -> None:
        text = self.txt.decode("utf-8")
        for old, new, reason in (("SET 8 OF 9 - EXERCISES 085-096", "SET 8 OF 9 - EXERCISES 085-097", "TXT_SET_BOUNDARY_MISMATCH"),
                                 ("Exercise 085: 4131", "Exercise 085: 4132", "TXT_CODE_ORDER_OR_CARD_SHAPE"),
                                 ("e|8-5------|9-7------|", "e|8-6------|9-7------|", "TXT_TEMPLATE_CONFLICT"),
                                 ("e|10-7-----|7-5------|", "E|10-7-----|7-5------|", "TXT_STRING_ORDER_MISMATCH")):
            with self.subTest(reason=reason), self.assertRaisesRegex(set8.CandidateError, reason):
                set8.txt_cards(text.replace(old, new, 1).encode("utf-8"))
        with self.assertRaisesRegex(set8.CandidateError, "FINGER_FRET_MISMATCH"):
            set8.cell_notes("8-6------", "41", "P5", 1, "e")

    def test_pdf_txt_conflict_and_pin_drift_refuse(self) -> None:
        page = set8.pdf_cards(self.pdf)
        self.assertEqual(len(page), 12)
        wrong = copy.deepcopy(page)
        wrong[0]["shift_up"] = "S|8-5------|9-8------|"
        with patch.object(set8, "pdf_cards", return_value=wrong):
            with self.assertRaisesRegex(set8.CandidateError, "PDF_TXT_TEMPLATE_MISMATCH"):
                set8.build_candidate()
        with self.assertRaisesRegex(set8.CandidateError, "PINNED_INPUT_DRIFT L9-TXT"):
            set8.build_candidate(txt_data=self.txt + b"x", pdf_data=self.pdf)
        with self.assertRaisesRegex(set8.CandidateError, "PINNED_INPUT_DRIFT L9-PDF"):
            set8.build_candidate(txt_data=self.txt, pdf_data=self.pdf + b"x")

    def test_output_boundary_and_overwrite_refuse(self) -> None:
        with self.assertRaisesRegex(set8.CandidateError, "OUTPUT_OUTSIDE_LANE_BUILD"):
            set8.write_candidate(ROOT / "Results" / "forbidden.json")
        (ROOT / set8.BUILD_REL).mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=ROOT / set8.BUILD_REL, suffix=".json") as stream:
            existing = Path(stream.name)
            existing.write_bytes(b"sentinel")
            with self.assertRaisesRegex(set8.CandidateError, "OUTPUT_EXISTS"):
                set8.write_candidate(existing)
            self.assertEqual(existing.read_bytes(), b"sentinel")


if __name__ == "__main__":
    unittest.main()
