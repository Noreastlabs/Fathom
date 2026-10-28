"""Focused Level 25 natural-minor source, crossing, route, and refusal checks."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from Tools import curriculum_level025_whole_candidate as level25


ROOT = Path(__file__).resolve().parents[1]


class Level25WholeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = level25.read_pinned(ROOT, level25.TXT)
        cls.pdf = level25.read_pinned(ROOT, level25.PDF)
        cls.cards, cls.guidance = level25.parse_sources(cls.txt, cls.pdf)
        cls.candidate = level25.assemble(cls.cards, cls.guidance)

    def changed_card(self, rung: int) -> list[dict]:
        cards = list(self.cards)
        cards[rung - 1] = copy.deepcopy(cards[rung - 1])
        return cards

    def test_full_txt_pdf_coverage_and_card_lineage(self) -> None:
        result = self.candidate
        self.assertEqual(result["counts"], {
            "rungs": 13, "groups_per_rung": 10, "notes_per_rung": 40,
            "groups_in_source_cards": 130, "notes_in_source_cards": 520,
            "round_trip_cells": 25, "round_trip_note_occurrences": 1000})
        self.assertEqual([record["rung"] for record in result["records"]], list(range(1, 14)))
        self.assertEqual(len({record["source_local_key"] for record in result["records"]}), 13)
        self.assertEqual(result["records"][0]["source_refs"], {
            "txt": "L25-TXT1-67-78", "pdf_card": "L25-PDF1-p3-l4-17",
            "pdf_route_map": "L25-PDF1-p2-l9-13"})
        self.assertEqual(result["records"][-1]["source_refs"], {
            "txt": "L25-TXT1-235-246", "pdf_card": "L25-PDF1-p7-l3-16",
            "pdf_route_map": "L25-PDF1-p2-l69-73"})
        for record, card in zip(result["records"], self.cards, strict=True):
            self.assertEqual(record["raw_txt_card"], card["txt_body"])
            self.assertEqual(record["raw_pdf_card"], card["pdf_block"])
            self.assertEqual(record["raw_pdf_route_map_row"], card["pdf_route_map_row"])
            self.assertEqual(len(record["groups"]), 10)
            self.assertEqual(sum(len(group["notes"]) for group in record["groups"]), 40)

    def test_transposition_minor_degrees_and_every_tab_note(self) -> None:
        for index, record in enumerate(self.candidate["records"]):
            root = index + 5
            self.assertEqual((record["key"], record["root_fret"], record["frame_frets"]),
                             (level25.KEYS[index], root, [root, root + 3]))
            self.assertEqual(record["scale_degrees_1_to_8"], list(level25.DEGREES))
            self.assertEqual(record["scale_tones_degrees_1_to_8"], level25.TONES[index].split())
            for group_index, group in enumerate(record["groups"]):
                self.assertEqual(group["degree_indices"], list(level25.GROUPS[group_index]))
                self.assertEqual(group["degree_labels"], [level25.DEGREES[d - 1] for d in level25.GROUPS[group_index]])
                for column, note in enumerate(group["notes"]):
                    degree = group["degree_indices"][column]
                    self.assertEqual(note["ordinal_in_cell"], 4 * group_index + column + 1)
                    self.assertEqual(note["degree_label"], level25.DEGREES[degree - 1])
                    self.assertEqual(note["finger_digit"], level25.FINGERS[degree - 1])
                    self.assertEqual(note["string"], level25.SCALE_STRING[degree - 1])
                    self.assertEqual(note["printed_column"], 3 * column)
                    self.assertEqual(note["tone"], record["scale_tones_degrees_1_to_8"][degree - 1])
                    self.assertEqual((level25.OPEN_MIDI[note["string"]] + note["fret"]) % 12,
                                     level25.note_pc(note["tone"]))
                    self.assertIsNone(note["onset_q"])
                    self.assertIsNone(note["duration_q"])
        # High-rung edge includes fret 20; Eb natural minor retains the Cb spelling.
        high = self.candidate["records"][-1]
        self.assertIn(20, [n["fret"] for g in high["groups"] for n in g["notes"]])
        self.assertEqual(self.candidate["records"][6]["scale_tones_degrees_1_to_8"][5], "Cb")
        self.assertEqual(high["root_fret"] - self.candidate["records"][0]["root_fret"], 12)
        self.assertEqual(high["scale_tones_degrees_1_to_8"], self.candidate["records"][0]["scale_tones_degrees_1_to_8"])

    def test_crossing_map_overlap_turn_routes_and_pick_cycle(self) -> None:
        result = self.candidate
        self.assertEqual(result["ascending_route"], list(range(1, 14)))
        self.assertEqual(result["descending_route_after_high_a"], list(range(12, 0, -1)))
        self.assertEqual(result["round_trip_rung_order"], list(range(1, 14)) + list(range(12, 0, -1)))
        self.assertEqual(result["round_trip_rung_order"].count(13), 1)
        self.assertEqual(sum(result["records"][n - 1]["note_count"] for n in result["round_trip_rung_order"]), 1000)
        for record in result["records"]:
            groups = record["groups"]
            self.assertEqual([group["string_crossing_pattern"] for group in groups], list(level25.CROSSINGS))
            for first, last in ((0, 5), (5, 10)):
                for index in range(first + 1, last):
                    self.assertEqual(groups[index - 1]["degree_indices"][1:], groups[index]["degree_indices"][:3])
            a = groups[4]["notes"][-1]
            b = groups[5]["notes"][0]
            self.assertEqual((a["degree_label"], a["tone"], a["string"], a["fret"]),
                             (b["degree_label"], b["tone"], b["string"], b["fret"]))
            self.assertEqual(a["degree_label"], "8")
            self.assertEqual((groups[0]["notes"][0]["degree_label"], groups[-1]["notes"][-1]["degree_label"]), ("1", "1"))
            self.assertTrue(record["shift_after_complete_cell_only"])
            self.assertFalse(record["within_cell_shift"])
            self.assertEqual([n["pick_for_down_start"] for g in groups for n in g["notes"]], ["D", "U"] * 20)
            self.assertEqual([n["pick_for_up_start"] for g in groups for n in g["notes"]], ["U", "D"] * 20)

    def test_authored_guidance_has_no_machine_timing_or_admission(self) -> None:
        result = self.candidate
        intro = "\n".join(result["source_guidance"]["txt_intro_lines_1_65"])
        tail = "\n".join(result["source_guidance"]["txt_after_cards_lines_248_280"])
        self.assertIn("Degrees:   1 2 b3 4 5 b6 b7 8", intro)
        self.assertIn("UP:   EEEA | EEAA | EAAA | AAAD | AADD", intro)
        self.assertIn("Use sixteenth notes: one four-note group per beat.", intro)
        self.assertIn("if Level 24 is clean at 80 BPM, begin near 60 BPM", intro)
        self.assertIn("Reverse after the fret-17 A-natural-minor cell", tail)
        self.assertIn("Advance after two separate clean days with both pick starts", tail)
        self.assertEqual(result["pick_start_options"], ["D", "U"])
        self.assertTrue(result["tempo_and_grouping_are_source_guidance_only"])
        self.assertFalse(result["canonical_schema_validated"] or result["runtime_eligible"]
                         or result["imported"] or result["admitted"] or result["whole_workbook_complete"])
        for record in result["records"]:
            for field in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q",
                          "note_per_click", "fixed_bpm"):
                self.assertIsNone(record[field])
            self.assertFalse(record["runtime_eligible"] or record["imported"] or record["admitted"])

    def test_pinned_source_and_crossing_guidance_drift_refuse(self) -> None:
        with self.assertRaisesRegex(level25.SourceError, "pinned input drift"):
            level25.read_pinned(ROOT, (level25.TXT[0], "0" * 64, level25.TXT[2]))
        with self.assertRaisesRegex(level25.SourceError, "pinned input drift"):
            level25.read_pinned(ROOT, (level25.PDF[0], "0" * 64, level25.PDF[2]))
        bad_txt = self.txt.replace(b"UP:   EEEA | EEAA", b"UP:   EEAA | EEAA")
        with self.assertRaisesRegex(level25.SourceError, "string-crossing guidance drift"):
            level25.parse_sources(bad_txt, self.pdf)
        bad_txt = self.txt.replace(b"RUNG 08 OF 13", b"RUNG 09 OF 13")
        with self.assertRaisesRegex(level25.SourceError, "rung/key/root/frame conflict"):
            cards, guidance = level25.parse_sources(bad_txt, self.pdf)
            level25.assemble(cards, guidance)

    def test_loss_duplicate_pdf_map_and_octave_turn_refuse(self) -> None:
        with self.assertRaisesRegex(level25.SourceError, "missing/duplicate/out-of-order rung"):
            level25.assemble(self.cards[:-1], self.guidance)
        bad = list(self.cards)
        bad[1] = bad[0]
        with self.assertRaisesRegex(level25.SourceError, "missing/duplicate/out-of-order rung"):
            level25.assemble(bad, self.guidance)
        bad = self.changed_card(10)
        bad[9]["pdf_route_map_row"][1] = "F natural minor"
        with self.assertRaisesRegex(level25.SourceError, "PDF route-map/rung conflict"):
            level25.assemble(bad, self.guidance)
        bad = self.changed_card(13)
        bad[12]["txt_body"][11] = level25.TXT_FINISH
        with self.assertRaisesRegex(level25.SourceError, "TXT tone/cell/turn guidance conflict"):
            level25.assemble(bad, self.guidance)
        bad = self.changed_card(13)
        bad[12]["pdf_block"][12] = level25.PDF_FINISH
        with self.assertRaisesRegex(level25.SourceError, "PDF/TXT rung card conflict"):
            level25.assemble(bad, self.guidance)

    def test_degree_finger_fret_column_and_crossing_conflicts_refuse(self) -> None:
        for altered in ("b3-", "b6-", "b7-"):
            bad = self.changed_card(1)
            card = bad[0]
            card["txt_body"][3] = card["txt_body"][3].replace(altered, altered[1:] + "-", 1)
            card["pdf_block"][4] = card["txt_body"][3]
            with self.subTest(degree=altered), self.assertRaisesRegex(level25.SourceError, "degree order/alignment"):
                level25.assemble(bad, self.guidance)
        cases = ((3, "3--", "degree order/alignment"),
                 (4, "2--", "finger order/alignment"),
                 (10, "6--", "TAB string/fret conflict"))
        for row_index, token, expected in cases:
            bad = self.changed_card(1)
            card = bad[0]
            original = card["txt_body"][row_index]
            if row_index == 10:
                card["txt_body"][row_index] = original.replace("E  |5--", "E  |6--", 1)
            else:
                card["txt_body"][row_index] = original[:4] + token + original[7:]
            card["pdf_block"][row_index + 1] = card["txt_body"][row_index]
            with self.subTest(row=row_index), self.assertRaisesRegex(level25.SourceError, expected):
                level25.assemble(bad, self.guidance)
        bad = self.changed_card(1)
        card = bad[0]
        card["txt_body"][9] = card["txt_body"][9].replace("A  |---", "A  |5--", 1)
        card["pdf_block"][10] = card["txt_body"][9]
        with self.assertRaisesRegex(level25.SourceError, "TAB column note count"):
            level25.assemble(bad, self.guidance)
        with patch.object(level25, "CROSSINGS", ("AAAA",) + level25.CROSSINGS[1:]):
            with self.assertRaisesRegex(level25.SourceError, "authored string-crossing map conflict"):
                level25.assemble(self.cards, self.guidance)

    def test_determinism_and_output_refusal(self) -> None:
        first = json.dumps(level25.build(ROOT), ensure_ascii=False, sort_keys=True, indent=2)
        second = json.dumps(level25.build(ROOT), ensure_ascii=False, sort_keys=True, indent=2)
        self.assertEqual(first, second)
        command = [sys.executable, "-m", "Tools.curriculum_level025_whole_candidate", "--output"]
        bad = subprocess.run(command + [str(ROOT / "Results" / "forbidden.json")], cwd=ROOT,
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertIn("new JSON file", bad.stderr)
        existing = ROOT / level25.BUILD_REL / "candidate-initial.json"
        before = existing.read_bytes()
        bad = subprocess.run(command + [str(existing)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(existing.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
