"""Focused Level 16 source, rolling-cell, route, and refusal checks."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from Tools import curriculum_level016_whole_candidate as level16


ROOT = Path(__file__).resolve().parents[1]


class Level16WholeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = level16.read_pinned(ROOT, level16.TXT)
        cls.pdf = level16.read_pinned(ROOT, level16.PDF)
        cls.cards, cls.guidance = level16.parse_sources(cls.txt, cls.pdf)
        cls.candidate = level16.assemble(cls.cards, cls.guidance)

    def changed_card(self, rung: int) -> list[dict]:
        cards = list(self.cards)
        cards[rung - 1] = copy.deepcopy(cards[rung - 1])
        return cards

    def test_complete_txt_pdf_coverage_and_card_lineage(self) -> None:
        result = self.candidate
        self.assertEqual(result["counts"], {
            "rungs": 13, "groups_per_rung": 10, "notes_per_rung": 40,
            "groups_in_source_cards": 130, "notes_in_source_cards": 520,
            "round_trip_cells": 25, "round_trip_note_occurrences": 1000})
        self.assertEqual([r["rung"] for r in result["records"]], list(range(1, 14)))
        self.assertEqual(len({r["source_local_key"] for r in result["records"]}), 13)
        self.assertEqual(result["records"][0]["source_refs"], {
            "txt": "L16-TXT1-62-73", "pdf_card": "L16-PDF1-p3-l4-17",
            "pdf_route_map": "L16-PDF1-p2-l9-13"})
        self.assertEqual(result["records"][-1]["source_refs"], {
            "txt": "L16-TXT1-230-241", "pdf_card": "L16-PDF1-p7-l3-16",
            "pdf_route_map": "L16-PDF1-p2-l69-73"})
        for record, card in zip(result["records"], self.cards, strict=True):
            self.assertEqual(record["raw_txt_card"], card["txt_body"])
            self.assertEqual(record["raw_pdf_card"], card["pdf_block"])
            self.assertEqual(record["raw_pdf_route_map_row"], card["pdf_route_map_row"])
            self.assertEqual(len(record["groups"]), 10)
            self.assertEqual(sum(len(g["notes"]) for g in record["groups"]), 40)

    def test_all_keys_transpose_and_every_printed_note_is_preserved(self) -> None:
        for index, record in enumerate(self.candidate["records"]):
            root = index + 5
            self.assertEqual((record["key"], record["root_fret"], record["frame_frets"]),
                             (level16.KEYS[index], root, [root - 1, root + 2]))
            self.assertEqual(record["scale_tones_degrees_1_to_8"], level16.TONES[index].split())
            for group_index, group in enumerate(record["groups"]):
                self.assertEqual(group["group_number"], group_index + 1)
                self.assertEqual(group["direction"], "up" if group_index < 5 else "down")
                self.assertEqual(group["degrees"], list(level16.GROUPS[group_index]))
                self.assertEqual(len(group["notes"]), 4)
                for column, note in enumerate(group["notes"]):
                    degree = group["degrees"][column]
                    self.assertEqual(note["ordinal_in_cell"], 4 * group_index + column + 1)
                    self.assertEqual(note["finger_digit"], level16.FINGERS[degree - 1])
                    self.assertEqual(note["string"], level16.SCALE_STRING[degree - 1])
                    self.assertEqual(note["printed_column"], 3 * column)
                    self.assertEqual(note["tone"], record["scale_tones_degrees_1_to_8"][degree - 1])
                    self.assertEqual((level16.OPEN_MIDI[note["string"]] + note["fret"]) % 12,
                                     level16.note_pc(note["tone"]))
                    self.assertIsNone(note["onset_q"])
                    self.assertIsNone(note["duration_q"])
        # The high A is the same pitch class as the low A, twelve frets higher.
        self.assertEqual(self.candidate["records"][12]["root_fret"] - self.candidate["records"][0]["root_fret"], 12)
        self.assertEqual(self.candidate["records"][0]["scale_tones_degrees_1_to_8"],
                         self.candidate["records"][12]["scale_tones_degrees_1_to_8"])

    def test_overlap_turn_routes_and_pick_cycle(self) -> None:
        result = self.candidate
        self.assertEqual(result["ascending_route"], list(range(1, 14)))
        self.assertEqual(result["descending_route_after_high_a"], list(range(12, 0, -1)))
        self.assertEqual(result["round_trip_rung_order"], list(range(1, 14)) + list(range(12, 0, -1)))
        self.assertEqual(result["round_trip_rung_order"].count(13), 1)
        self.assertEqual(sum(result["records"][n - 1]["note_count"] for n in result["round_trip_rung_order"]), 1000)
        for record in result["records"]:
            groups = record["groups"]
            for first, last in ((0, 5), (5, 10)):
                for index in range(first + 1, last):
                    self.assertEqual(groups[index - 1]["degrees"][1:], groups[index]["degrees"][:3])
            self.assertEqual((groups[4]["notes"][-1]["degree"], groups[5]["notes"][0]["degree"]), (8, 8))
            self.assertEqual(groups[4]["notes"][-1]["tone"], groups[5]["notes"][0]["tone"])
            self.assertEqual(groups[0]["notes"][0]["degree"], 1)
            self.assertEqual(groups[-1]["notes"][-1]["degree"], 1)
            self.assertTrue(record["shift_after_complete_cell_only"])
            self.assertFalse(record["within_cell_shift"])
            strokes = [n["pick_for_down_start"] for g in groups for n in g["notes"]]
            self.assertEqual(strokes, ["D", "U"] * 20)
            strokes = [n["pick_for_up_start"] for g in groups for n in g["notes"]]
            self.assertEqual(strokes, ["U", "D"] * 20)

    def test_authored_guidance_is_not_machine_timing_or_admission(self) -> None:
        result = self.candidate
        self.assertTrue(result["tempo_and_grouping_are_source_guidance_only"])
        intro = "\n".join(result["source_guidance"]["txt_intro_lines_1_60"])
        tail = "\n".join(result["source_guidance"]["txt_after_cards_lines_243_265"])
        self.assertIn("Use sixteenth notes: one four-note group per beat.", intro)
        self.assertIn("Level 15 is clean at 80 BPM, begin near 60 BPM.", intro)
        self.assertIn("Add 2 BPM after three clean round trips.", intro)
        self.assertIn("Do not replay rung 13 at the turn.", tail)
        self.assertEqual(result["pick_start_options"], ["D", "U"])
        self.assertFalse(result["canonical_schema_validated"] or result["runtime_eligible"]
                         or result["imported"] or result["admitted"] or result["whole_workbook_complete"])
        for record in result["records"]:
            for field in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q",
                          "note_per_click", "fixed_bpm"):
                self.assertIsNone(record[field])
            self.assertFalse(record["runtime_eligible"] or record["imported"] or record["admitted"])

    def test_source_pin_and_guidance_drift_refuse(self) -> None:
        with self.assertRaisesRegex(level16.SourceError, "pinned input drift"):
            level16.read_pinned(ROOT, (level16.TXT[0], "0" * 64, level16.TXT[2]))
        with self.assertRaisesRegex(level16.SourceError, "pinned input drift"):
            level16.read_pinned(ROOT, (level16.PDF[0], "0" * 64, level16.PDF[2]))
        bad_txt = self.txt.replace(b"Do not replay rung 13 at the turn.", b"Do not replay rung 12 at the turn.")
        with self.assertRaisesRegex(level16.SourceError, "round-trip guidance drift"):
            level16.parse_sources(bad_txt, self.pdf)
        bad_txt = self.txt.replace(b"RUNG 08 OF 13", b"RUNG 09 OF 13")
        with self.assertRaisesRegex(level16.SourceError, "rung/key/root/frame conflict"):
            cards, guidance = level16.parse_sources(bad_txt, self.pdf)
            level16.assemble(cards, guidance)

    def test_missing_duplicate_and_pdf_route_conflicts_refuse(self) -> None:
        with self.assertRaisesRegex(level16.SourceError, "missing/duplicate/out-of-order rung"):
            level16.assemble(self.cards[:-1], self.guidance)
        bad = list(self.cards)
        bad[1] = bad[0]
        with self.assertRaisesRegex(level16.SourceError, "missing/duplicate/out-of-order rung"):
            level16.assemble(bad, self.guidance)
        bad = self.changed_card(10)
        bad[9]["pdf_route_map_row"][1] = "F major"
        with self.assertRaisesRegex(level16.SourceError, "PDF route-map/rung conflict"):
            level16.assemble(bad, self.guidance)
        bad = self.changed_card(13)
        bad[12]["pdf_block"][6] = "Deg|wrong|"
        with self.assertRaisesRegex(level16.SourceError, "PDF/TXT rung card conflict"):
            level16.assemble(bad, self.guidance)

    def test_degree_finger_tab_and_cell_conflicts_refuse(self) -> None:
        cases = ((3, "2--", "degree order/alignment"),
                 (4, "1--", "finger order/alignment"),
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
            with self.subTest(row=row_index), self.assertRaisesRegex(level16.SourceError, expected):
                level16.assemble(bad, self.guidance)
        bad = self.changed_card(1)
        card = bad[0]
        card["txt_body"][9] = card["txt_body"][9].replace("A  |---", "A  |4--", 1)
        card["pdf_block"][10] = card["txt_body"][9]
        with self.assertRaisesRegex(level16.SourceError, "TAB column note count"):
            level16.assemble(bad, self.guidance)

    def test_determinism_and_output_refusal(self) -> None:
        first = json.dumps(level16.build(ROOT), ensure_ascii=False, sort_keys=True, indent=2)
        second = json.dumps(level16.build(ROOT), ensure_ascii=False, sort_keys=True, indent=2)
        self.assertEqual(first, second)
        command = [sys.executable, "-m", "Tools.curriculum_level016_whole_candidate", "--output"]
        bad = subprocess.run(command + [str(ROOT / "Results" / "forbidden.json")], cwd=ROOT,
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertIn("new JSON file", bad.stderr)
        existing = ROOT / level16.BUILD_REL / "candidate-initial.json"
        before = existing.read_bytes()
        bad = subprocess.run(command + [str(existing)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(existing.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
