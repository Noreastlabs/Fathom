"""Focused Level85 whole-source semantic conversion and drift refusals."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel13_level085_whole_semantic_candidate as candidate  # noqa: E402


class Level85SemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        candidate.check_pins()
        candidate.foundation_status()
        cls.structure = json.loads((ROOT / candidate.STRUCTURE).read_text())
        cls.replayed = candidate.index.build_candidate(ROOT)
        cls.raw_pdf = candidate.index.read_pinned(ROOT, candidate.index.PDF)
        cls.pages = [p.extract_text() or "" for p in PdfReader(BytesIO(cls.raw_pdf)).pages]
        cls.output = candidate.build()

    def test_original_source_and_structural_index_replay(self) -> None:
        self.assertEqual(self.structure, self.replayed)
        self.assertEqual(self.output["source_index"]["sha256"], candidate.PINS[candidate.STRUCTURE])
        self.assertEqual(len(self.output["txt_lines"]), 40)
        self.assertEqual(len(self.output["pdf_pages"]), 15)
        self.assertEqual([p["extracted_text_sha256"] for p in self.output["pdf_pages"]],
                         [p["literal_extracted_text_sha256"] for p in self.structure["pdf"]["pages"]])
        self.assertEqual(self.output["txt_lines"][3]["literal"],
                         "LEVEL 85 OF 105 - HARD STOP AFTER LEVEL 105")

    def test_all_modules_rows_and_unallocated_workloads(self) -> None:
        self.assertEqual(self.output["module_task_row_count"], 82)
        self.assertEqual(self.output["reference_row_count"], 6)
        self.assertEqual({m["module"]: len(m["tasks"]) for m in self.output["modules"]},
                         candidate.COUNTS)
        self.assertEqual({m["module"]: m["declared_events"] for m in self.output["modules"]},
                         {k: v for k, _, v in candidate.index.EXPECTED_MODULES})
        self.assertEqual(self.output["declared_total_events"], 1440)
        self.assertEqual(self.output["playable_event_count"], 0)
        self.assertFalse(self.output["canonical_ids_allocated"])
        self.assertFalse(self.output["schema1_imported"])
        self.assertFalse(self.output["whole_workbook_accepted"])
        self.assertFalse(self.output["runtime_eligible"])
        for row in self.output["reference_rows"] + [t for m in self.output["modules"] for t in m["tasks"]]:
            self.assertIsNone(row["declared_event_count_for_row"])
            self.assertIsNone(row["canonical_id"])
            self.assertIsNone(row["onset_q"])
            self.assertIsNone(row["duration_q"])
            self.assertIsNone(row["performed_result"])
            page = row["source"]["pdf_page"]
            self.assertEqual(row["source"]["pdf_extracted_text_sha256"],
                             self.output["pdf_pages"][page - 1]["extracted_text_sha256"])

    def test_reference_legend_and_ghosts_are_not_pitched_events(self) -> None:
        self.assertEqual(self.output["symbol_legend"],
                         {"P": "pitched contact", "x": "muted contact",
                          "-": "air stroke", "~": "sustain"})
        self.assertEqual(self.output["continuous_hand_motion"], "D U D U sixteenths")
        self.assertEqual({r["relation"] for r in self.output["reference_rows"]},
                         {"adjacent_unassigned_groove_reference"})
        self.assertEqual({r["source"]["pdf_page"] for r in self.output["reference_rows"]}, {2})
        self.assertTrue(all(r["semantic"]["pitched_attack_events"] is None
                            for r in self.output["reference_rows"]))
        c = self.output["modules"][2]["tasks"]
        self.assertEqual(len(c), 6)
        self.assertTrue(all(r["semantic"]["ghost_pitch_allowed"] is False and
                            r["semantic"]["pitched_attack_events"] is None for r in c))

    def test_a_b_d_e_f_g_semantics(self) -> None:
        modules = {m["module"]: m for m in self.output["modules"]}
        self.assertTrue(all(t["semantic"]["fixed_harmony"] == "Am7"
                            for t in modules["A"]["tasks"]))
        self.assertTrue(all(t["semantic"]["quarter_attacks_per_measure"] == 4 and
                            t["semantic"]["tempo_change"] is False
                            for t in modules["B"]["tasks"]))
        self.assertTrue(all(t["semantic"]["imagined_drum_part"] is True
                            for t in modules["D"]["tasks"]))
        self.assertTrue(all(t["semantic"]["recorded_bass_supplied"] is False
                            for t in modules["E"]["tasks"]))
        self.assertEqual([t["semantic"]["placement"] for t in modules["F"]["tasks"]],
                         ["On", "Slightly ahead", "Slightly behind", "Return on"])
        self.assertTrue(all(t["semantic"]["exact_millisecond_target"] is None and
                            t["semantic"]["performed_offset"] is None
                            for t in modules["F"]["tasks"]))
        self.assertEqual(len(modules["G"]["tasks"]), 8)
        self.assertTrue(all(t["semantic"]["complete_genre_definition"] is False
                            for t in modules["G"]["tasks"]))

    def test_four_h_studies_and_eight_capstone_ranges(self) -> None:
        modules = {m["module"]: m for m in self.output["modules"]}
        h = modules["H"]["tasks"]
        self.assertEqual(len(h), 24)
        for study in range(1, 5):
            group = [t for t in h if t["semantic"]["study"] == study]
            self.assertEqual([t["semantic"]["pass"] for t in group], list(range(1, 7)))
            self.assertEqual(len(group[0]["semantic"]["harmony_bars_literal"]), 8)
            self.assertEqual(len({tuple(t["semantic"]["harmony_bars_literal"]) for t in group}), 1)
            self.assertEqual(len({t["semantic"]["focus"] for t in group}), 1)
        i = modules["I"]["tasks"]
        self.assertEqual([(t["semantic"]["bar_start"], t["semantic"]["bar_end"])
                          for t in i], [(n, n + 3) for n in range(1, 33, 4)])
        self.assertEqual([t["fields"] for t in i],
                         [r["literal_fields"] for r in self.structure["pdf"]["i_capstone_table"]["rows"]])
        self.assertTrue(all(t["semantic"]["declared_events_for_range"] is None for t in i))
        self.assertEqual(self.output["capstone"]["printed_module_events"], 256)
        self.assertIsNone(self.output["capstone"]["per_four_bar_row_event_counts"])
        self.assertTrue(self.output["capstone"]["one_underlying_tempo"])
        self.assertTrue(self.output["capstone"]["beat_four_announcement_required"])

    def test_recovery_mastery_and_hard_stop(self) -> None:
        j = self.output["modules"][9]["tasks"]
        self.assertEqual(len(j), 8)
        self.assertTrue(all(set(t["fields"]) == {"Failure", "Repair"}
                            and t["semantic"]["observed_failure"] is None
                            for t in j))
        mastery = self.output["mastery"]
        self.assertEqual(mastery["minimum"], "14/16 or better on two separate days")
        self.assertEqual(mastery["protected_zero_domains"],
                         ["pulse", "note length", "muting", "recovery"])
        self.assertIsNone(mastery["observed_score"])
        self.assertIn("HARD STOP after 105.", self.output["pdf_pages"][-1]["extracted_text"])

    def test_refuse_changed_table_and_capstone(self) -> None:
        for page, old, new, code in (
            (3, "Use one chord - Am7 -", "Use one chord - Dm7 -", "A_FIXED_HARMONY_TEMPO"),
            (8, "not by an exact millisecond target", "by a 20 ms target", "F_NO_MS_TARGET"),
            (14, "29-32", "29-33", "I_INDEX_PARITY"),
            (15, "14/16 or better", "12/16 or better", "J_MASTERY_HARD_STOP"),
        ):
            pages = list(self.pages)
            pages[page - 1] = pages[page - 1].replace(old, new)
            structure = copy.deepcopy(self.structure)
            structure["pdf"]["pages"][page - 1]["literal_extracted_text_sha256"] = candidate.sha(
                pages[page - 1].encode())
            with self.assertRaisesRegex(candidate.SourceError, code):
                candidate.parse_pages(pages, structure)

    def test_refuse_missing_rows_or_bad_structure_hash(self) -> None:
        pages = list(self.pages)
        pages[4] = pages[4].replace("P-xx P-xx P-xx P-xx\n", "")
        structure = copy.deepcopy(self.structure)
        structure["pdf"]["pages"][4]["literal_extracted_text_sha256"] = candidate.sha(pages[4].encode())
        with self.assertRaises(candidate.SourceError):
            candidate.parse_pages(pages, structure)
        with self.assertRaisesRegex(candidate.SourceError, "PDF_INDEX_PAGE_HASH_DRIFT"):
            candidate.parse_pages(pages, self.structure)


if __name__ == "__main__":
    unittest.main()
