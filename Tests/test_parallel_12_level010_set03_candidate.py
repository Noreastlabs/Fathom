"""Focused source-linked Level 10 Set 3 odd-count transfer checks."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from parallel_12_level010_set03_candidate import (
    CODES, PDF, PDF_PIN, ROOT, TXT, TXT_PIN, CandidateError, build_candidate,
    digest, local_bytes, parse_txt, serialize, verify, write_output,
)


class LevelTenSetThreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = local_bytes(ROOT, TXT)
        cls.pdf = local_bytes(ROOT, PDF)
        cls.candidate = build_candidate()

    def test_all_codes_modes_and_sequential_routes(self) -> None:
        candidate = self.candidate
        self.assertEqual(candidate["schema"], "fathom-level010-set03-detached-candidate-v1")
        self.assertEqual(candidate["counts"], {"records": 12, "modes": 24, "directions": 48,
                                               "string_routes": 288, "untimed_note_positions": 1152})
        self.assertEqual([record["code"] for record in candidate["records"]], list(CODES))
        self.assertEqual([record["exercise_number"] for record in candidate["records"]],
                         [f"{number:03d}" for number in range(25, 37)])
        for record in candidate["records"]:
            self.assertEqual([mode["mode"] for mode in record["modes"]], ["mode_a", "mode_b"])
            self.assertTrue(record["source_local_key"].startswith("L10-set03-ex"))
            self.assertIsNone(record["canonical_item_id"])
            self.assertIsNone(record["canonical_variant_id"])
            self.assertIsNone(record["onset_q"])
            self.assertIsNone(record["duration_q"])
            self.assertFalse(record["runtime_eligible"] or record["runtime_admitted"] or record["imported"] or record["admitted"])
            for mode in record["modes"]:
                self.assertEqual([direction["direction"] for direction in mode["directions"]],
                                 ["shift_up", "shift_down"])
                self.assertEqual(mode["source_refs"]["pdf"],
                                 "L10-PDF1-p6" if mode["mode"] == "mode_a" else "L10-PDF1-p7")
                for direction in mode["directions"]:
                    self.assertEqual(len(direction["routes"]), 6)
                    self.assertEqual([route["string"] for route in direction["routes"]], direction["route_order"])
                    for route in direction["routes"]:
                        self.assertEqual(len(route["notes"]), 4)
                        self.assertEqual(route["source_finger_row"], direction["source_finger_row"])
                        self.assertEqual(route["pdf_tab_template"][1:], route["source_tab_row"][1:])
                        self.assertTrue(all(note["onset_q"] is None and note["duration_q"] is None for note in route["notes"]))

    def test_distinct_mode_landing_ordinals_and_exact_frets(self) -> None:
        for record in self.candidate["records"]:
            code = record["code"]
            for mode in record["modes"]:
                shift = 3 if mode["mode"] == "mode_a" else 1
                landing = shift + 1
                self.assertEqual((mode["shift_after_note"], mode["landing_note_ordinal"]), (shift, landing))
                for direction in mode["directions"]:
                    source, destination = direction["position_order"]
                    for route in direction["routes"]:
                        self.assertEqual(route["shift_after_note"], shift)
                        self.assertEqual([note["ordinal"] for note in route["notes"]], [1, 2, 3, 4])
                        self.assertEqual([note["finger_digit"] for note in route["notes"]], list(code))
                        self.assertEqual([note["position"] for note in route["notes"]],
                                         [source] * shift + [destination] * (4 - shift))
                        self.assertEqual([note["landing"] for note in route["notes"]],
                                         [index == landing for index in range(1, 5)])
                        self.assertEqual([note["fret"] for note in route["notes"]],
                                         [int(digit) + (4 if position == "P5" else 6)
                                          for digit, position in zip(code, [source] * shift + [destination] * (4 - shift), strict=True)])
                        self.assertEqual(route["landing_note"]["ordinal"], landing)
                        self.assertEqual(route["landing_note"]["fret"], route["notes"][landing - 1]["fret"])
        self.assertEqual(self.candidate["records"][0]["modes"][0]["landing_note_ordinal"], 4)
        self.assertEqual(self.candidate["records"][0]["modes"][1]["landing_note_ordinal"], 2)

    def test_source_pins_and_deterministic_candidate(self) -> None:
        verify(self.txt, TXT_PIN, "TXT")
        verify(self.pdf, PDF_PIN, "PDF")
        self.assertEqual(self.candidate, build_candidate())
        self.assertEqual(serialize(self.candidate), serialize(build_candidate()))
        self.assertEqual(digest(self.txt), TXT_PIN[1])
        self.assertEqual(digest(self.pdf), PDF_PIN[1])
        with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT"):
            build_candidate(txt_data=self.txt + b"x", pdf_data=self.pdf)
        with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT"):
            build_candidate(txt_data=self.txt, pdf_data=self.pdf[:-1])

    def test_txt_mode_route_barline_and_fret_errors_refuse(self) -> None:
        baseline = self.txt.decode("utf-8").splitlines()
        def bad(line: int, text: str, code: str) -> None:
            lines = copy.copy(baseline)
            lines[line - 1] = text
            with self.assertRaisesRegex(CandidateError, code):
                parse_txt(lines)
        bad(936, "MODE B - 1+3 EARLY SHIFT", "TXT_MODE_HEADER")
        bad(941, "Exercise 025: 1432", "TXT_CARD_SHAPE")
        bad(943, "F|1-4|3-1|", "TAB_CELL_MISMATCH")
        bad(944, "e|5-8|7-7|", "TAB_CELL_MISMATCH")
        bad(944, "e|5-8-7------8----------|", "TAB_ROW_INVALID")
        bad(944, "B|5-8-7------|7----------|", "TXT_STRING_ORDER")
        bad(1165, "F|1-4-3------|1----------|", "TAB_CELL_MISMATCH")

    def test_output_boundary_and_no_hidden_admission(self) -> None:
        self.assertFalse(self.candidate["runtime_eligible"] or self.candidate["runtime_admitted"] or
                         self.candidate["imported"] or self.candidate["admitted"] or
                         self.candidate["whole_workbook_complete"])
        self.assertIsNone(self.candidate["canonical_item_id"])
        self.assertIsNone(self.candidate["fixed_bpm"])
        self.assertIsNone(self.candidate["note_per_click"])
        with self.assertRaisesRegex(CandidateError, "OUTPUT_BOUNDARY"):
            write_output(Path("relative.json"), b"{}")
        with self.assertRaisesRegex(CandidateError, "OUTPUT_BOUNDARY"):
            write_output(ROOT / "Build/parallel-12/other/candidate.json", b"{}")


if __name__ == "__main__":
    unittest.main()
