"""Focused source and musical-cell checks for detached Levels 88–89."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "Tools/curriculum_levels_088_089_candidate.py"
spec = importlib.util.spec_from_file_location("curriculum_levels_088_089_candidate", TOOL)
assert spec and spec.loader
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = candidate.read_sources()
        cls.payload = candidate.build()

    def test_exact_pairs_and_selected_pages(self) -> None:
        self.assertEqual(set(self.payload["levels"]), {"88", "89"})
        self.assertEqual(len(self.payload["levels"]["88"]["cells"]), 4)
        self.assertEqual(len(self.payload["levels"]["89"]["cells"]), 8)
        for level, page in ((88, 4), (89, 3)):
            self.assertEqual(set(self.payload["source_identities"][str(level)]), {"txt", "pdf"})
            self.assertEqual(self.payload["levels"][str(level)]["selected_pdf_page"]["page"], page)

    def test_gallop_grid_and_picking_positions(self) -> None:
        rows = self.payload["levels"]["88"]["cells"]
        self.assertEqual(rows[0]["ordered_contact_symbols"], ["M", "-", "M", "M"])
        self.assertEqual(rows[0]["ordered_picking_symbols"], ["D", "-", "D", "U"])
        self.assertEqual(rows[3]["ordered_contact_symbols"], ["-", "M", "M", "M"])
        self.assertEqual(rows[3]["ordered_picking_symbols"], ["-", "U", "D", "U"])
        self.assertEqual([r["txt_module_anchor_line"] for r in rows], [14] * 4)
        self.assertEqual([r["txt_skill_anchor_line"] for r in rows], [27] * 4)
        self.assertIn("rows 5–8 not converted", self.payload["levels"]["88"]["scope_note"])
        for row in rows:
            self.assertEqual(row["txt_cell_detail"], "omitted")
            self.assertIsNone(row["performed_onsets_and_durations"])
            self.assertIsNone(row["pedal_string_and_fret"])

    def test_alternating_bass_root_fifth_and_order(self) -> None:
        rows = self.payload["levels"]["89"]["cells"]
        self.assertEqual([r["printed_chord"] for r in rows], ["G", "C", "D", "A", "E", "Am", "Em", "F"])
        self.assertEqual(rows[0]["ordered_bass_notes"], ["G", "D", "G", "D"])
        self.assertEqual(rows[-1]["ordered_bass_notes"], ["F", "C", "F", "C"])
        self.assertEqual(rows[3]["ordered_bass_notes"], rows[5]["ordered_bass_notes"])
        self.assertEqual(rows[4]["ordered_bass_notes"], rows[6]["ordered_bass_notes"])
        self.assertEqual([r["txt_module_anchor_line"] for r in rows], [12] * 8)
        self.assertEqual([r["txt_skill_anchor_line"] for r in rows], [24] * 8)
        for row in rows:
            self.assertEqual(row["printed_count"], "1-2-3-4")
            self.assertEqual(row["txt_cell_detail"], "omitted")
            self.assertIsNone(row["sounding_octaves"])
            self.assertIsNone(row["performed_onsets_and_durations"])

    def test_bad_musical_relations_are_refused(self) -> None:
        for grid, pick in (("M - M M", "- - D U"), ("M M M -", "D U D U"), ("M - M", "D - U")):
            with self.subTest(grid=grid, pick=pick), self.assertRaises(candidate.CandidateError):
                candidate.gallop_tokens(grid, pick)
        for chord, pattern, count in (("G", "G-C-G-C", "1-2-3-4"),
                                      ("C", "C-G-G-C", "1-2-3-4"),
                                      ("F", "F-C-F-C", "1-&-3-4")):
            with self.subTest(chord=chord, pattern=pattern), self.assertRaises(candidate.CandidateError):
                candidate.check_bass(chord, pattern, count)

    def test_mutated_source_bytes_are_refused(self) -> None:
        for level in (88, 89):
            for kind in ("txt", "pdf"):
                path, size, digest = candidate.SOURCES[level][kind]
                raw = (candidate.ROOT / path).read_bytes()
                candidate.verify_bytes(raw, size, digest, f"Level {level} {kind}")
                changed = raw[:-1] + bytes([raw[-1] ^ 1])
                with self.assertRaises(candidate.CandidateError):
                    candidate.verify_bytes(changed, size, digest, f"Level {level} {kind}")

    def test_selected_pdf_mutation_is_refused(self) -> None:
        modified = dict(self.sources[88])
        modified["pdf"] = dict(modified["pdf"])
        modified["pdf"]["content"] = list(modified["pdf"]["content"])
        modified["pdf"]["content"][3] = modified["pdf"]["content"][3].replace("D - D U", "- - D U")
        with self.assertRaises(candidate.CandidateError):
            candidate.level88(modified)

    def test_candidate_stays_pending_and_unadmitted(self) -> None:
        self.assertEqual(self.payload["selected_cell_count"], 12)
        self.assertEqual(self.payload["status"], "Pending")
        self.assertEqual(self.payload["review"], "Pending")
        self.assertFalse(self.payload["canonical_ids_allocated"])
        self.assertFalse(self.payload["runtime_eligible"])
        self.assertFalse(self.payload["whole_workbook_complete"])


if __name__ == "__main__":
    unittest.main()
