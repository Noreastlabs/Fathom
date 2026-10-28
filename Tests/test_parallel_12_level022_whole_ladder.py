"""Source-linked Level 22 full ladder and refusal tests."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from parallel_12_level022_whole_ladder import (
    KEYS, PDF, PDF_PIN, ROOT, TXT, TXT_PIN, CandidateError, build_candidate,
    digest, local_bytes, parse_pdf_pages, parse_tab_rows, pitch_class,
    serialize, source_rungs, verify, write_output,
)


class LevelTwentyTwoWholeLadderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = local_bytes(ROOT, TXT)
        cls.pdf = local_bytes(ROOT, PDF)
        cls.candidate = build_candidate()

    def test_thirteen_rungs_exact_notes_and_source_refs(self) -> None:
        c = self.candidate
        self.assertEqual(c["schema"], "fathom-level022-whole-detached-candidate-v1")
        self.assertEqual(c["counts"], {"rungs": 13, "notes_per_cell": 30, "unique_cell_notes": 390,
                                        "round_trip_cells": 25, "round_trip_picked_notes": 750})
        self.assertEqual([rung["rung"] for rung in c["rungs"]], list(range(1, 14)))
        self.assertEqual([rung["key"] for rung in c["rungs"]], list(KEYS))
        self.assertEqual([rung["root_fret"] for rung in c["rungs"]], list(range(5, 18)))
        for index, rung in enumerate(c["rungs"]):
            start = 55 + 14 * index
            page = 3 + index // 3
            page_line = 6 + 14 * (index % 3)
            self.assertEqual(rung["source_refs"],
                             {"txt": f"L22-TXT1-{start}-{start + 11}",
                              "pdf": f"L22-PDF1-p{page}-L{page_line}-{page_line + 13}",
                              "pdf_overview": "L22-PDF1-p2"})
            self.assertEqual((rung["frame_min_fret"], rung["frame_max_fret"]),
                             (rung["root_fret"] - 1, rung["root_fret"] + 3))
            notes = rung["cell_notes"]
            self.assertEqual(len(notes), 30)
            self.assertEqual([note["ordinal"] for note in notes], list(range(1, 31)))
            self.assertEqual([note["direction"] for note in notes], ["ascending"] * 15 + ["descending"] * 15)
            self.assertEqual([note["turn_repeat"] for note in notes], [False] * 15 + [True] + [False] * 14)
            self.assertEqual([(note["string"], note["fret"], note["finger_digit"])
                              for note in notes[14:16]], [("e", rung["root_fret"], 1)] * 2)
            self.assertEqual([(note["string"], note["fret"]) for note in [notes[0], notes[-1]]],
                             [("E", rung["root_fret"])] * 2)
            self.assertEqual([note["degree"] for note in notes[0:3]], ["1", "2", "b3"])
            self.assertEqual([note["degree"] for note in notes[-3:]], ["b3", "2", "1"])
            self.assertTrue(all(note["onset_q"] is None and note["duration_q"] is None for note in notes))

    def test_g_backreach_b_offset_and_minor_spelling(self) -> None:
        for rung in self.candidate["rungs"]:
            root = rung["root_fret"]
            notes = rung["cell_notes"]
            self.assertEqual([(n["fret"], n["finger_digit"]) for n in notes[8:11]],
                             [(root - 1, 1), (root, 2), (root + 2, 4)])
            self.assertEqual([(n["fret"], n["finger_digit"]) for n in notes[11:14]],
                             [(root, 1), (root + 1, 2), (root + 3, 4)])
            self.assertEqual([n["string"] for n in notes[:15]],
                             ["E"] * 3 + ["A"] * 3 + ["D"] * 2 + ["G"] * 3 + ["B"] * 3 + ["e"])
            self.assertEqual([n["string"] for n in notes[15:]],
                             ["e"] + ["B"] * 3 + ["G"] * 3 + ["D"] * 2 + ["A"] * 3 + ["E"] * 3)
            self.assertEqual([pitch_class(t) for t in rung["scale_tones_two_octaves"][:7]],
                             [(pitch_class(rung["key"]) + offset) % 12 for offset in (0, 2, 3, 5, 7, 8, 10)])
            self.assertFalse(self.candidate["source_guidance"]["static_five_fret_stretch_inferred"])
        self.assertEqual(self.candidate["rungs"][6]["scale_tones_two_octaves"][:7],
                         ["Eb", "F", "Gb", "Ab", "Bb", "Cb", "Db"])

    def test_round_trip_is_a_to_a_25_cells_750_notes(self) -> None:
        route = self.candidate["full_round_trip_route"]
        self.assertEqual([cell["rung"] for cell in route], list(range(1, 14)) + list(range(12, 0, -1)))
        self.assertEqual([cell["root_fret"] for cell in route], list(range(5, 18)) + list(range(16, 4, -1)))
        self.assertEqual(sum(cell["cell_note_count"] for cell in route), 750)
        self.assertTrue(all(cell["travel_direction"] == ("up" if index < 13 else "down")
                            for index, cell in enumerate(route)))
        self.assertEqual(route[0]["key"], route[-1]["key"])

    def test_source_pins_pdf_parity_and_determinism(self) -> None:
        verify(self.txt, TXT_PIN, "TXT")
        verify(self.pdf, PDF_PIN, "PDF")
        self.assertEqual((len(self.txt), digest(self.txt)), TXT_PIN)
        self.assertEqual((len(self.pdf), digest(self.pdf)), PDF_PIN)
        self.assertEqual(serialize(self.candidate), serialize(build_candidate()))
        rungs, _ = source_rungs(self.txt, self.pdf)
        self.assertEqual(rungs, self.candidate["rungs"])
        pages = parse_pdf_pages(self.pdf)
        self.assertEqual(len(pages), 7)
        with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT LEVEL22_TXT"):
            build_candidate(txt_data=self.txt + b"x", pdf_data=self.pdf)
        with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT LEVEL22_PDF"):
            build_candidate(txt_data=self.txt, pdf_data=self.pdf[:-1])

    def test_bad_rung_degree_finger_tab_and_pdf_refuse(self) -> None:
        baseline = self.txt.decode("utf-8").splitlines()
        def bad(line: int, replacement: str, error: str) -> None:
            lines = copy.copy(baseline)
            lines[line - 1] = replacement
            with self.assertRaisesRegex(CandidateError, error):
                source_rungs(("\n".join(lines) + "\n").encode(), self.pdf)
        bad(55, baseline[55 - 1].replace("RUNG 01", "RUNG 02"), "TXT_RUNG_SHAPE")
        bad(56, baseline[56 - 1].replace("A B C", "A B Db"), "NATURAL_MINOR_TONE")
        bad(58, baseline[58 - 1].replace("b3-4", "3--4", 1), "TXT_PDF_RUNG_MISMATCH")
        bad(59, baseline[59 - 1].replace("1--3--4", "1--2--4", 1), "TXT_PDF_RUNG_MISMATCH")
        bad(60, baseline[60 - 1].replace("5--5", "5--6", 1), "TXT_PDF_RUNG_MISMATCH")
        bad(62, baseline[62 - 1].replace("4--5--7", "5--5--7", 1), "TXT_PDF_RUNG_MISMATCH")
        bad(61, baseline[61 - 1].replace("5--6--8", "5--7--8", 1), "TXT_PDF_RUNG_MISMATCH")
        bad(223, baseline[223 - 1].replace("RUNG 13", "RUNG 12"), "TXT_RUNG_SHAPE")
        pdf_pages = parse_pdf_pages(self.pdf)
        mutated = copy.deepcopy(pdf_pages)
        mutated[3][9] = mutated[3][9].replace("b3", "3", 1)
        with patch("parallel_12_level022_whole_ladder.parse_pdf_pages", return_value=mutated):
            with self.assertRaisesRegex(CandidateError, "TXT_PDF_RUNG_MISMATCH"):
                source_rungs(self.txt, self.pdf)
        with self.assertRaisesRegex(CandidateError, "TXT_TAB_FRETS"):
            parse_tab_rows(["e  |5--5|", "B  |5--6--8--8--6--5|",
                            "G  |5--5--7--7--5--5|", "D  |5--7--7--5|",
                            "A  |5--7--8--8--7--5|", "E  |5--7--8--8--7--5|"], 5, 1)

    def test_guidance_unadmitted_and_output_boundary(self) -> None:
        c = self.candidate
        self.assertIn("Begin 10-15 BPM", "\n".join(c["source_guidance"]["practice_tempo_source"]))
        self.assertIn("D-start: strict D-U", "\n".join(c["source_guidance"]["picking_source"]))
        self.assertFalse(c["source_guidance"]["practice_is_timing_authority"])
        for item in [c, *c["rungs"]]:
            self.assertTrue(all(item[key] is None for key in
                                ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q",
                                 "fixed_bpm", "note_per_click")))
            self.assertTrue(all(item[key] is False for key in
                                ("runtime_eligible", "runtime_admitted", "imported", "admitted")))
        self.assertFalse(c["whole_workbook_complete"])
        with self.assertRaisesRegex(CandidateError, "OUTPUT_BOUNDARY"):
            write_output(Path("relative.json"), b"{}")
        with self.assertRaisesRegex(CandidateError, "OUTPUT_BOUNDARY"):
            write_output(ROOT / "Build/parallel-12/other/candidate.json", b"{}")


if __name__ == "__main__":
    unittest.main()
