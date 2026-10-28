"""Source-linked Level 10 Sets 4–9 batch conversion checks."""

from __future__ import annotations

import copy
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader

import parallel_12_level010_sets04_09_candidate as candidate_module
from parallel_12_level010_sets04_09_candidate import (
    PRIOR, SETS, CandidateError, PDF, PDF_PIN, ROOT, TXT, TXT_PIN,
    build_candidate, digest, local_bytes, parse_pdf_set, parse_txt_set,
    prior_inputs, serialize, verify, write_output,
)


class LevelTenSetsFourThroughNineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = local_bytes(ROOT, TXT)
        cls.pdf = local_bytes(ROOT, PDF)
        cls.lines = cls.txt.decode("utf-8").splitlines()
        cls.candidate = build_candidate()

    def test_explicit_inventory_all_modes_routes_and_source_refs(self) -> None:
        candidate = self.candidate
        self.assertEqual(candidate["schema"], "fathom-level010-sets04-09-detached-candidate-v1")
        self.assertEqual(candidate["sets"], [4, 5, 6, 7, 8, 9])
        self.assertEqual(candidate["counts"], {"records": 72, "modes": 144, "directions": 288,
                                               "string_routes": 1728, "untimed_note_positions": 6912})
        self.assertEqual([record["exercise_number"] for record in candidate["records"]],
                         [f"{number:03d}" for number in range(37, 109)])
        self.assertEqual([record["code"] for record in candidate["records"]],
                         [code for _, codes in SETS.values() for code in codes])
        self.assertEqual(len(set(record["source_local_key"] for record in candidate["records"])), 72)
        for record in candidate["records"]:
            set_number = record["set"]
            header = SETS[set_number][0]
            index = (int(record["exercise_number"]) - 1) % 12
            self.assertEqual([mode["mode"] for mode in record["modes"]], ["mode_a", "mode_b"])
            for mode in record["modes"]:
                offset = 0 if mode["mode"] == "mode_a" else 222
                start = header + 9 + offset + 18 * index
                page = 2 * set_number + (0 if offset == 0 else 1)
                self.assertEqual(mode["source_refs"],
                                 {"txt": f"L10-TXT1-{start}-{start + 16}", "pdf": f"L10-PDF1-p{page}"})
                self.assertEqual([direction["direction"] for direction in mode["directions"]],
                                 ["shift_up", "shift_down"])
                for direction in mode["directions"]:
                    self.assertEqual(len(direction["routes"]), 6)
                    self.assertEqual([route["string"] for route in direction["routes"]],
                                     direction["route_order"])
                    self.assertEqual([route["route_ordinal"] for route in direction["routes"]],
                                     [1, 2, 3, 4, 5, 6])
                    self.assertEqual(direction["route_order"],
                                     ["E", "A", "D", "G", "B", "e"] if direction["direction"] == "shift_up"
                                     else ["e", "B", "G", "D", "A", "E"])
                    for route in direction["routes"]:
                        self.assertEqual(route["source_finger_row"], direction["source_finger_row"])
                        self.assertEqual(route["pdf_tab_template"][1:], route["source_tab_row"][1:])
                        self.assertEqual(route["pdf_finger_template"], route["source_finger_row"])

    def test_note_fret_finger_position_and_distinct_landing(self) -> None:
        for record in self.candidate["records"]:
            code = record["code"]
            for mode in record["modes"]:
                shift = 3 if mode["mode"] == "mode_a" else 1
                landing = shift + 1
                self.assertEqual((mode["shift_after_note"], mode["landing_note_ordinal"]),
                                 (shift, landing))
                for direction in mode["directions"]:
                    source, destination = direction["position_order"]
                    positions = [source] * shift + [destination] * (4 - shift)
                    for route in direction["routes"]:
                        notes = route["notes"]
                        self.assertEqual(len(notes), 4)
                        self.assertEqual([note["ordinal"] for note in notes], [1, 2, 3, 4])
                        self.assertEqual([note["finger_digit"] for note in notes], list(code))
                        self.assertEqual([note["position"] for note in notes], positions)
                        self.assertEqual([note["fret"] for note in notes],
                                         [int(digit) + (4 if position == "P5" else 6)
                                          for digit, position in zip(code, positions, strict=True)])
                        self.assertEqual([note["landing"] for note in notes],
                                         [ordinal == landing for ordinal in range(1, 5)])
                        self.assertEqual(route["landing_note"]["ordinal"], landing)
                        self.assertEqual(route["landing_note"]["fret"], notes[landing - 1]["fret"])
                        self.assertTrue(all(note["string"] == route["string"] and
                                            note["onset_q"] is None and note["duration_q"] is None
                                            for note in notes))

    def test_source_and_released_neighbor_pins_and_determinism(self) -> None:
        verify(self.txt, TXT_PIN, "TXT")
        verify(self.pdf, PDF_PIN, "PDF")
        self.assertEqual(len(prior_inputs()), 3)
        for set_number, path, pin in PRIOR:
            data = local_bytes(ROOT, path)
            self.assertEqual((len(data), digest(data)), pin, set_number)
        self.assertEqual(serialize(self.candidate), serialize(build_candidate()))
        with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT LEVEL10_TXT"):
            build_candidate(txt_data=self.txt + b"x", pdf_data=self.pdf)
        with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT LEVEL10_PDF"):
            build_candidate(txt_data=self.txt, pdf_data=self.pdf[:-1])
        original = candidate_module.local_bytes
        def changed_prior(root: Path, path: Path) -> bytes:
            data = original(root, path)
            return data + b"x" if path == PRIOR[1][1] else data
        with patch.object(candidate_module, "local_bytes", side_effect=changed_prior):
            with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT RELEASED_SET_2"):
                prior_inputs()

    def test_every_set_txt_and_pdf_card_structure(self) -> None:
        reader = PdfReader(BytesIO(self.pdf), strict=True)
        for set_number in SETS:
            txt = parse_txt_set(self.lines, set_number)
            pdf = parse_pdf_set(reader, set_number)
            for mode in ("mode_a", "mode_b"):
                self.assertEqual(len(txt[mode]), 12)
                self.assertEqual(len(pdf[mode]), 12)
                self.assertEqual([card["code"] for card in txt[mode]],
                                 [card["code"] for card in pdf[mode]])
                for txt_card, pdf_card in zip(txt[mode], pdf[mode], strict=True):
                    for direction in ("shift_up", "shift_down"):
                        self.assertEqual(txt_card[direction]["finger_row"],
                                         pdf_card[direction]["finger_template"])
                        self.assertTrue(all("S" + row[1:] == pdf_card[direction]["tab_template"]
                                            for row in txt_card[direction]["rows_high_to_low"]))
        self.assertEqual(len(self.lines), 4065)  # final card complete, no two trailing blank lines

    def test_bad_set_mode_card_cell_and_eof_refuse(self) -> None:
        def bad(set_number: int, line: int, replacement: str, error: str) -> None:
            lines = copy.copy(self.lines)
            lines[line - 1] = replacement
            with self.assertRaisesRegex(CandidateError, error):
                parse_txt_set(lines, set_number)
        bad(4, 1380, "SET 5 OF 9 - EXERCISES 037-048", "TXT_SET_BOUNDARY")
        bad(5, 1832, "MODE B - 1+3 EARLY SHIFT", "TXT_MODE_HEADER")
        bad(6, 2285, "Exercise 061: 3142", "TXT_CARD_SHAPE")
        bad(7, 2735, "F|3-4|1-2|", "TAB_CELL_MISMATCH")
        bad(8, 3184, "e|8-5-7------|8----------|", "TAB_CELL_MISMATCH")
        bad(9, 3629, "Exercise 097: 4242", "TXT_CARD_SHAPE")
        with self.assertRaisesRegex(CandidateError, "TXT_FINAL_SET_EOF"):
            parse_txt_set(self.lines[:-1], 9)

    def test_pdf_page_or_landing_mutation_refuses(self) -> None:
        reader = PdfReader(BytesIO(self.pdf), strict=True)
        class Page:
            def __init__(self, text: str): self.text = text
            def extract_text(self) -> str: return self.text
        class Reader:
            def __init__(self, pages: list[object]): self.pages = pages
        pages = list(reader.pages)
        page = 18 - 1
        text = pages[page].extract_text().replace("landing note 4; no pick reset",
                                                  "landing note 2; no pick reset", 1)
        pages[page] = Page(text)
        with self.assertRaisesRegex(CandidateError, "PDF_CARD_SHAPE"):
            parse_pdf_set(Reader(pages), 9)

    def test_no_admission_and_write_boundary(self) -> None:
        root = self.candidate
        for key in ("runtime_eligible", "runtime_admitted", "imported", "admitted", "whole_workbook_complete"):
            self.assertFalse(root[key])
        for key in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q",
                    "fixed_bpm", "note_per_click"):
            self.assertIsNone(root[key])
        for record in root["records"]:
            self.assertTrue(all(not record[key] for key in ("runtime_eligible", "runtime_admitted",
                                                             "imported", "admitted")))
            self.assertTrue(all(record[key] is None for key in ("canonical_item_id", "canonical_variant_id",
                                                                  "onset_q", "duration_q", "fixed_bpm",
                                                                  "note_per_click")))
        with self.assertRaisesRegex(CandidateError, "OUTPUT_BOUNDARY"):
            write_output(Path("relative.json"), b"{}")
        with self.assertRaisesRegex(CandidateError, "OUTPUT_BOUNDARY"):
            write_output(ROOT / "Build/parallel-12/other/candidate.json", b"{}")


if __name__ == "__main__":
    unittest.main()
