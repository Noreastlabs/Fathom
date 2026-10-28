"""Level 9 Set 4 printed source, route, shift and refusal checks."""

from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from Tools import curriculum_level009_set04_candidate as set4


ROOT = Path(__file__).resolve().parents[1]


class Level9Set4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = (ROOT / set4.TXT_REL).read_bytes()
        cls.pdf = (ROOT / set4.PDF_REL).read_bytes()
        cls.candidate = set4.build_candidate()

    def test_exact_set_boundary_source_and_determinism(self) -> None:
        first, second = set4.build_candidate(), set4.build_candidate()
        self.assertEqual(first, second)
        self.assertEqual(first["source"]["txt_sha256"], set4.TXT_PIN[1])
        self.assertEqual(first["source"]["pdf_sha256"], set4.PDF_PIN[1])
        self.assertEqual(first["source"]["selected_pdf_page"], 5)
        self.assertEqual([row["code"] for row in first["records"]], list(set4.CODES))
        self.assertEqual([row["exercise_number"] for row in first["records"]], [f"{n:03d}" for n in range(37, 49)])
        self.assertEqual(first["records"][0]["source_refs"], {"txt": "L9-TXT1-619-633", "pdf": "L9-PDF1-p5"})
        self.assertEqual(first["records"][-1]["source_refs"], {"txt": "L9-TXT1-795-809", "pdf": "L9-PDF1-p5"})
        self.assertEqual(len(first["records"]), 12)
        self.assertEqual(sum(len(direction["sequential_one_string_routes"]) for record in first["records"]
                             for direction in record["directions"]), 144)
        self.assertEqual(sum(len(cell["notes"]) for record in first["records"]
                             for direction in record["directions"]
                             for route in direction["sequential_one_string_routes"]
                             for cell in route["cells"]), 576)

    def test_printed_first_middle_last_routes_and_hand_frame_shift(self) -> None:
        for index, up_frets, down_frets in ((0, [6, 7, 7, 8], [8, 9, 5, 6]),
                                           (6, [6, 7, 10, 7], [8, 9, 8, 5]),
                                           (11, [6, 8, 7, 10], [8, 10, 5, 8])):
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
        # Exercise 043 falls from fret 10 to 7 after an upward frame shift.
        middle = self.candidate["records"][6]["directions"][0]["sequential_one_string_routes"][0]
        self.assertEqual([note["fret"] for cell in middle["cells"] for note in cell["notes"]], [6, 7, 10, 7])

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
        for old, new, reason in (("SET 4 OF 9 - EXERCISES 037-048", "SET 4 OF 9 - EXERCISES 037-049", "TXT_SET_BOUNDARY_MISMATCH"),
                                 ("Exercise 037: 2312", "Exercise 037: 2313", "TXT_CODE_ORDER_OR_CARD_SHAPE"),
                                 ("e|6-7------|7-8------|", "e|6-8------|7-8------|", "TXT_TEMPLATE_CONFLICT"),
                                 ("e|8-9------|5-6------|", "E|8-9------|5-6------|", "TXT_STRING_ORDER_MISMATCH")):
            with self.subTest(reason=reason), self.assertRaisesRegex(set4.CandidateError, reason):
                set4.txt_cards(text.replace(old, new, 1).encode("utf-8"))
        with self.assertRaisesRegex(set4.CandidateError, "FINGER_FRET_MISMATCH"):
            set4.cell_notes("6-8------", "23", "P5", 1, "e")

    def test_pdf_txt_conflict_and_pin_drift_refuse(self) -> None:
        page = set4.pdf_cards(self.pdf)
        self.assertEqual(len(page), 12)
        wrong = copy.deepcopy(page)
        wrong[0]["shift_up"] = "S|6-7------|7-9------|"
        with patch.object(set4, "pdf_cards", return_value=wrong):
            with self.assertRaisesRegex(set4.CandidateError, "PDF_TXT_TEMPLATE_MISMATCH"):
                set4.build_candidate()
        with self.assertRaisesRegex(set4.CandidateError, "PINNED_INPUT_DRIFT L9-TXT"):
            set4.build_candidate(txt_data=self.txt + b"x", pdf_data=self.pdf)
        with self.assertRaisesRegex(set4.CandidateError, "PINNED_INPUT_DRIFT L9-PDF"):
            set4.build_candidate(txt_data=self.txt, pdf_data=self.pdf + b"x")

    def test_output_boundary_and_overwrite_refuse(self) -> None:
        with self.assertRaisesRegex(set4.CandidateError, "OUTPUT_OUTSIDE_LANE_BUILD"):
            set4.write_candidate(ROOT / "Results" / "forbidden.json")
        (ROOT / set4.BUILD_REL).mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=ROOT / set4.BUILD_REL, suffix=".json") as stream:
            existing = Path(stream.name)
            existing.write_bytes(b"sentinel")
            with self.assertRaisesRegex(set4.CandidateError, "OUTPUT_EXISTS"):
                set4.write_candidate(existing)
            self.assertEqual(existing.read_bytes(), b"sentinel")


if __name__ == "__main__":
    unittest.main()
