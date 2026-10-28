"""Source-linked whole Level 28 diatonic-triad ladder checks."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from parallel_12_level028_whole_triad_ladder import (
    DOWN_PATH, KEYS, PDF, PDF_PIN, ROOT, TXT, TXT_PIN, UP_PATH,
    CandidateError, build_candidate, digest, local_bytes, parse_contact_cells,
    parse_pdf_pages, pitch_class, serialize, source_rungs, verify, write_output,
)


class LevelTwentyEightTriadLadderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = local_bytes(ROOT, TXT)
        cls.pdf = local_bytes(ROOT, PDF)
        cls.candidate = build_candidate()

    def test_exact_inventory_keys_sources_and_discrepancy_record(self) -> None:
        c = self.candidate
        self.assertEqual(c["schema"], "fathom-level028-whole-detached-triad-candidate-v1")
        self.assertEqual(c["source_title"], "Natural Minor Diatonic Triads - Two-Octave Six-String Neck Ladder")
        self.assertEqual(c["source_discrepancies"], [])
        self.assertEqual(c["counts"], {"rungs": 13, "triads_per_cell": 22,
                                        "contacts_per_cell": 66, "unique_triads": 286,
                                        "unique_contacts": 858, "round_trip_cells": 25,
                                        "round_trip_contacts": 1650})
        self.assertEqual([rung["rung"] for rung in c["rungs"]], list(range(1, 14)))
        self.assertEqual([rung["key"] for rung in c["rungs"]], list(KEYS))
        self.assertEqual([rung["root_fret"] for rung in c["rungs"]], list(range(5, 18)))
        for index, rung in enumerate(c["rungs"]):
            start = 104 + 27 * index
            page = 3 + index // 2
            page_line = 4 + 26 * (index % 2)
            self.assertEqual(rung["source_refs"],
                             {"txt": f"L28-TXT1-{start}-{start + 24}",
                              "pdf": f"L28-PDF1-p{page}-L{page_line}-{page_line + 25}",
                              "pdf_overview": "L28-PDF1-p2"})
            self.assertEqual((rung["frame_min_fret"], rung["frame_max_fret"]),
                             (rung["root_fret"] - 1, rung["root_fret"] + 3))
            self.assertEqual(len(rung["scale_tones_two_octaves"]), 15)
            self.assertEqual(len(rung["diatonic_triad_names"]), 7)
            self.assertEqual(len(rung["triads"]), 22)
            self.assertEqual(sum(len(triad["contacts"]) for triad in rung["triads"]), 66)
        self.assertEqual(self.candidate["rungs"][6]["diatonic_triad_names"],
                         ["Ebm", "Fdim", "Gb", "Abm", "Bbm", "Cb", "Db"])

    def test_every_triad_contact_path_harmony_and_source_cell(self) -> None:
        for rung in self.candidate["rungs"]:
            triads = rung["triads"]
            self.assertEqual([triad["triad_ordinal"] for triad in triads], list(range(1, 23)))
            self.assertEqual([triad["direction"] for triad in triads], ["ascending"] * 11 + ["descending"] * 11)
            self.assertEqual([triad["direction_triad_ordinal"] for triad in triads],
                             list(range(1, 12)) + list(range(1, 12)))
            self.assertEqual([triad["string_path"] for triad in triads], list(UP_PATH) + list(DOWN_PATH))
            for index, triad in enumerate(triads):
                self.assertEqual(len(triad["contacts"]), 3)
                self.assertEqual("".join(note["string"] for note in triad["contacts"]), triad["string_path"])
                self.assertEqual([note["contact_ordinal"] for note in triad["contacts"]], [1, 2, 3])
                self.assertEqual([note["ordinal"] for note in triad["contacts"]],
                                 list(range(index * 3 + 1, index * 3 + 4)))
                self.assertEqual(len(triad["source_cells"]["tab_high_to_low"]), 6)
                self.assertEqual(len(triad["source_cells"]["degrees"]), 12)
                self.assertEqual(len(triad["source_cells"]["fingers"]), 12)
                self.assertEqual(triad["harmonic_function"], triad["source_cells"]["harmonic"].rstrip("-"))
                for note in triad["contacts"]:
                    self.assertEqual(note["onset_q"], None)
                    self.assertEqual(note["duration_q"], None)
                    self.assertIn(note["finger_digit"], (1, 2, 3, 4))
                    self.assertEqual(pitch_class(note["pitch_spelling"]),
                                     ({"E": 4, "A": 9, "D": 2, "G": 7, "B": 11, "e": 4}[note["string"]] + note["fret"]) % 12)
            self.assertEqual([triad["harmonic_function"] for triad in triads[:7]],
                             ["i", "ii-dim", "III", "iv", "v", "VI", "VII"])
            self.assertEqual([triad["chord_quality"] for triad in triads[:7]],
                             ["minor", "diminished", "major", "minor", "minor", "major", "major"])

    def test_turn_g_b_offset_and_a_to_a_route(self) -> None:
        for rung in self.candidate["rungs"]:
            root = rung["root_fret"]
            notes = [note for triad in rung["triads"] for note in triad["contacts"]]
            self.assertEqual(len(notes), 66)
            self.assertEqual([(n["string"], n["fret"], n["degree"]) for n in notes[32:34]],
                             [("e", root, "15"), ("e", root, "15")])
            self.assertEqual((notes[0]["string"], notes[0]["fret"], notes[-1]["string"], notes[-1]["fret"]),
                             ("E", root, "E", root))
            g = {(n["fret"], n["finger_digit"]) for n in notes if n["string"] == "G"}
            b = {(n["fret"], n["finger_digit"]) for n in notes if n["string"] == "B"}
            self.assertEqual(g, {(root - 1, 1), (root, 2), (root + 2, 4)})
            self.assertEqual(b, {(root, 1), (root + 1, 2), (root + 3, 4)})
        route = self.candidate["full_round_trip_route"]
        self.assertEqual([cell["rung"] for cell in route], list(range(1, 14)) + list(range(12, 0, -1)))
        self.assertEqual([cell["root_fret"] for cell in route], list(range(5, 18)) + list(range(16, 4, -1)))
        self.assertEqual(sum(cell["contact_count"] for cell in route), 1650)

    def test_pins_pdf_parity_and_determinism(self) -> None:
        verify(self.txt, TXT_PIN, "TXT")
        verify(self.pdf, PDF_PIN, "PDF")
        self.assertEqual((len(self.txt), digest(self.txt)), TXT_PIN)
        self.assertEqual((len(self.pdf), digest(self.pdf)), PDF_PIN)
        self.assertEqual(serialize(self.candidate), serialize(build_candidate()))
        rungs, _ = source_rungs(self.txt, self.pdf)
        self.assertEqual(rungs, self.candidate["rungs"])
        self.assertEqual(len(parse_pdf_pages(self.pdf)), 10)
        with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT LEVEL28_TXT"):
            build_candidate(txt_data=self.txt + b"x", pdf_data=self.pdf)
        with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT LEVEL28_PDF"):
            build_candidate(txt_data=self.txt, pdf_data=self.pdf[:-1])

    def test_wrong_rung_quality_contact_and_pdf_refuse(self) -> None:
        baseline = self.txt.decode("utf-8").splitlines()
        def bad(line: int, replacement: str, error: str) -> None:
            lines = copy.copy(baseline)
            lines[line - 1] = replacement
            with self.assertRaisesRegex(CandidateError, error):
                source_rungs(("\n".join(lines) + "\n").encode(), self.pdf)
        bad(104, baseline[103].replace("RUNG 01", "RUNG 02"), "TXT_RUNG_SHAPE")
        bad(105, baseline[104].replace("A B C", "A B Db"), "NATURAL_MINOR_TONE")
        bad(106, baseline[105].replace("Bdim", "Bm"), "TXT_TRIAD_NAMES")
        bad(109, baseline[108].replace("ii-dim", "ii-min", 1), "TXT_PDF_RUNG_MISMATCH")
        bad(110, baseline[109].replace("b3", "3", 1), "TXT_PDF_RUNG_MISMATCH")
        bad(111, baseline[110].replace("1---4---3", "1---3---3", 1), "TXT_PDF_RUNG_MISMATCH")
        bad(114, baseline[113].replace("4---7", "5---7", 1), "TXT_PDF_RUNG_MISMATCH")
        bad(113, baseline[112].replace("5---8", "5---7", 1), "TXT_PDF_RUNG_MISMATCH")
        bad(428, baseline[427].replace("RUNG 13", "RUNG 12"), "TXT_RUNG_SHAPE")
        pages = parse_pdf_pages(self.pdf)
        altered = copy.deepcopy(pages)
        altered[2][8] = "01" if altered[2][8] != "01" else "02"
        with patch("parallel_12_level028_whole_triad_ladder.parse_pdf_pages", return_value=altered):
            with self.assertRaisesRegex(CandidateError, "PDF_RUNG_SUMMARY"):
                source_rungs(self.txt, self.pdf)
        altered = copy.deepcopy(pages)
        altered[3][8] = altered[3][8].replace("ii-dim", "ii-min", 1)
        with patch("parallel_12_level028_whole_triad_ladder.parse_pdf_pages", return_value=altered):
            with self.assertRaisesRegex(CandidateError, "TXT_PDF_RUNG_MISMATCH"):
                source_rungs(self.txt, self.pdf)
        source_rows = baseline[111:117]
        invalid = copy.copy(source_rows)
        invalid[-1] = invalid[-1].replace("5---8-------", "5--8--------", 1)
        with self.assertRaisesRegex(CandidateError, "TAB_CONTACT_COLUMNS"):
            parse_contact_cells(invalid, 1, "ascending")

    def test_guidance_nonadmission_and_output_boundary(self) -> None:
        c = self.candidate
        self.assertIn("minor v and a major VII", "\n".join(c["source_guidance"]["harmonic_function_source"]))
        self.assertIn("sextuplets", "\n".join(c["source_guidance"]["rhythm_source"]))
        self.assertFalse(c["source_guidance"]["practice_is_timing_authority"])
        self.assertFalse(c["source_guidance"]["static_five_fret_stretch_inferred"])
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
