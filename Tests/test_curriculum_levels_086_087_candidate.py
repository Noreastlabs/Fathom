"""Source fidelity checks for detached Level 86–87 musical groove cells."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "Tools/curriculum_levels_086_087_candidate.py"
spec = importlib.util.spec_from_file_location("curriculum_levels_086_087_candidate", TOOL)
assert spec and spec.loader
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = candidate.read_sources()
        cls.payload = candidate.build()

    def test_exact_source_pairs_and_pdf_pages(self) -> None:
        self.assertEqual(set(self.payload["levels"]), {"86", "87"})
        for level, page in ((86, 5), (87, 3)):
            self.assertEqual(set(self.payload["source_identities"][str(level)]), {"txt", "pdf"})
            self.assertEqual(self.payload["levels"][str(level)]["selected_pdf_page"]["page"], page)
            self.assertEqual(len(self.payload["levels"][str(level)]["cells"]), 6)

    def test_single_chord_contact_rows_are_ordered_and_bounded(self) -> None:
        rows = self.payload["levels"]["86"]["cells"]
        self.assertEqual([r["printed_harmony"] for r in rows],
                         ["Am7", "D9", "G13", "Cmaj9", "F#m7", "E9"])
        self.assertEqual(rows[0]["ordered_contact_labels"], ["1", "a2", "&3", "a4"])
        self.assertEqual(rows[-1]["ordered_contact_labels"], ["2", "a2", "&3", "4"])
        self.assertEqual([r["txt_module_anchor_line"] for r in rows], [15] * 6)
        self.assertEqual([r["txt_skill_anchor_line"] for r in rows], [28] * 6)
        self.assertIn("rows 7–8 not converted", self.payload["levels"]["86"]["scope_note"])
        for row in rows:
            self.assertEqual(row["txt_cell_detail"], "omitted")
            self.assertIsNone(row["performed_onsets_and_durations"])
            self.assertIsNone(row["voicing_strings_and_frets"])

    def test_reggae_patterns_preserve_both_printed_grid_forms(self) -> None:
        rows = self.payload["levels"]["87"]["cells"]
        self.assertEqual([len(r["ordered_contact_symbols"]) for r in rows], [8, 8, 8, 16, 16, 16])
        self.assertEqual(rows[0]["ordered_contact_symbols"], ["-", "P", "-", "P", "-", "P", "-", "P"])
        self.assertEqual(rows[5]["ordered_contact_symbols"], list("---- --P- ---- --P-".replace(" ", "")))
        self.assertEqual([r["txt_module_anchor_line"] for r in rows], [12] * 6)
        self.assertEqual([r["txt_skill_anchor_line"] for r in rows], [24] * 6)
        for row in rows:
            self.assertEqual(row["txt_cell_detail"], "omitted")
            self.assertIsNone(row["chord_to_grid_assignment"])
            self.assertIsNone(row["audio"])

    def test_mutated_source_bytes_are_refused(self) -> None:
        for level in (86, 87):
            for kind in ("txt", "pdf"):
                path, size, digest = candidate.SOURCES[level][kind]
                raw = (candidate.ROOT / path).read_bytes()
                candidate.verify_bytes(raw, size, digest, f"Level {level} {kind}")
                changed = raw[:-1] + bytes([raw[-1] ^ 1])
                with self.assertRaises(candidate.CandidateError):
                    candidate.verify_bytes(changed, size, digest, f"Level {level} {kind}")

    def test_malformed_contact_rows_fail_closed(self) -> None:
        for value in ("1, a2, Q3", "1, 1, &3", "1, a2"):
            with self.subTest(value=value), self.assertRaises(candidate.CandidateError):
                candidate.parse_points(value)
        for count, pattern in (("1 & 2 & 3 & 4 &", "P P - P - P - P"),
                               ("1 e & a ...", "--P- --P- --P-"),
                               ("unknown", "- P - P - P - P")):
            with self.subTest(count=count, pattern=pattern), self.assertRaises(candidate.CandidateError):
                candidate.parse_pattern(count, pattern)

    def test_selected_pdf_row_mutation_is_refused(self) -> None:
        changed = dict(self.sources[87])
        changed["pdf"] = dict(changed["pdf"])
        changed["pdf"]["content"] = list(changed["pdf"]["content"])
        changed["pdf"]["content"][2] = changed["pdf"]["content"][2].replace("- P - P - P - P", "P P - P - P - P")
        with self.assertRaises(candidate.CandidateError):
            candidate.level87(changed)

    def test_candidate_remains_pending_and_unadmitted(self) -> None:
        self.assertEqual(self.payload["selected_cell_count"], 12)
        self.assertEqual(self.payload["status"], "Pending")
        self.assertEqual(self.payload["review"], "Pending")
        self.assertFalse(self.payload["canonical_ids_allocated"])
        self.assertFalse(self.payload["runtime_eligible"])
        self.assertFalse(self.payload["whole_workbook_complete"])


if __name__ == "__main__":
    unittest.main()
