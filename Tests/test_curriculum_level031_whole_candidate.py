"""Focused Level 31 pentatonic source, route, discrepancy, and refusal checks."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from Tools import curriculum_level031_whole_candidate as level31


ROOT = Path(__file__).resolve().parents[1]


class Level31WholeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = level31.read_pinned(ROOT, level31.TXT)
        cls.pdf = level31.read_pinned(ROOT, level31.PDF)
        cls.cards, cls.guidance, cls.discrepancies = level31.parse_sources(cls.txt, cls.pdf)
        cls.candidate = level31.assemble(cls.cards, cls.guidance, cls.discrepancies)

    def changed_card(self, rung: int) -> list[dict]:
        cards = list(self.cards)
        cards[rung - 1] = copy.deepcopy(cards[rung - 1])
        return cards

    def test_complete_txt_pdf_coverage_and_card_lineage(self) -> None:
        result = self.candidate
        self.assertEqual(result["counts"], {"rungs": 13, "notes_per_rung": 22,
                                            "notes_in_source_cards": 286,
                                            "round_trip_cells": 25, "round_trip_note_occurrences": 550})
        self.assertEqual([r["rung"] for r in result["records"]], list(range(1, 14)))
        self.assertEqual(len({r["source_local_key"] for r in result["records"]}), 13)
        self.assertEqual(result["records"][0]["source_refs"], {
            "txt": "L31-TXT1-54-65", "pdf_card": "L31-PDF1-p3-l4-17",
            "pdf_route_map": "L31-PDF1-p2-l9-13"})
        self.assertEqual(result["records"][-1]["source_refs"], {
            "txt": "L31-TXT1-222-233", "pdf_card": "L31-PDF1-p7-l4-17",
            "pdf_route_map": "L31-PDF1-p2-l69-73"})
        for record, card in zip(result["records"], self.cards, strict=True):
            self.assertEqual(record["raw_txt_card"], card["txt_body"])
            self.assertEqual(record["raw_pdf_card"], card["pdf_block"])
            self.assertEqual(record["raw_pdf_route_map_row"], card["pdf_route_map_row"])
            self.assertEqual(record["printed_tab_rows_high_to_low"], card["txt_body"][5:11])
            self.assertEqual(len(record["notes"]), 22)

    def test_all_keys_pentatonic_notes_six_strings_and_g_to_b(self) -> None:
        for index, record in enumerate(self.candidate["records"]):
            root = index + 5
            self.assertEqual((record["key"], record["root_fret"], record["frame_frets"]),
                             (level31.KEYS[index], root, [root - 1, root + 2]))
            self.assertEqual(record["degrees_per_octave"], [1, 2, 3, 5, 6])
            self.assertEqual(record["scale_tones_two_octaves"], level31.TONES[index].replace(" | ", " ").split())
            self.assertEqual([n["degree"] for n in record["notes"]], list(level31.DEGREES))
            self.assertEqual([n["finger_digit"] for n in record["notes"]], list(level31.FINGERS))
            self.assertEqual([n["string"] for n in record["notes"]], list(level31.STRINGS))
            self.assertEqual([n["fret"] for n in record["notes"]], [root + x for x in level31.FRET_OFFSETS])
            self.assertEqual([n["printed_column"] for n in record["notes"]], [3 * x for x in range(22)])
            self.assertEqual({n["string"] for n in record["notes"]}, set(level31.PRINTED_STRINGS))
            self.assertFalse({4, 7} & {n["degree"] for n in record["notes"]})
            self.assertEqual((record["notes"][6]["string"], record["notes"][8]["string"]), ("G", "B"))
            self.assertEqual((record["notes"][6]["fret"], record["notes"][8]["fret"]), (root - 1, root))
            for note in record["notes"]:
                self.assertEqual((level31.OPEN_MIDI[note["string"]] + note["fret"]) % 12,
                                 level31.tone_pc(note["tone"]))
                self.assertIsNone(note["onset_q"])
                self.assertIsNone(note["duration_q"])
        self.assertEqual(self.candidate["records"][12]["root_fret"] - self.candidate["records"][0]["root_fret"], 12)
        self.assertEqual(self.candidate["records"][0]["scale_tones_two_octaves"],
                         self.candidate["records"][12]["scale_tones_two_octaves"])

    def test_three_roots_high_turn_routes_and_pick_cycle(self) -> None:
        result = self.candidate
        self.assertEqual(result["ascending_route"], list(range(1, 14)))
        self.assertEqual(result["descending_route_after_high_a"], list(range(12, 0, -1)))
        self.assertEqual(result["round_trip_rung_order"], list(range(1, 14)) + list(range(12, 0, -1)))
        self.assertEqual(result["round_trip_rung_order"].count(13), 1)
        self.assertEqual(sum(result["records"][n - 1]["note_count"] for n in result["round_trip_rung_order"]), 550)
        for record in result["records"]:
            notes = record["notes"]
            self.assertEqual([n["degree"] for n in notes[:11]], list(level31.DEGREES_UP))
            self.assertEqual([n["degree"] for n in notes[11:]], list(reversed(level31.DEGREES_UP)))
            self.assertEqual([notes[i]["degree"] for i in (0, 5, 10, 11, 16, 21)], [1] * 6)
            self.assertEqual((notes[10]["string"], notes[10]["fret"], notes[10]["tone"]),
                             (notes[11]["string"], notes[11]["fret"], notes[11]["tone"]))
            self.assertEqual([n["pick_for_down_start"] for n in notes], ["D", "U"] * 11)
            self.assertEqual([n["pick_for_up_start"] for n in notes], ["U", "D"] * 11)
            self.assertTrue(record["shift_after_complete_cell_only"])
            self.assertFalse(record["within_cell_shift"])

    def test_pdf_worked_separator_discrepancy_is_retained_unresolved(self) -> None:
        discrepancy = self.candidate["source_discrepancies"][0]
        self.assertEqual(discrepancy["kind"], "octave_separator_position")
        self.assertEqual(discrepancy["txt_card"]["tokens_before_separator"], 6)
        self.assertEqual(discrepancy["pdf_card"]["tokens_before_separator"], 6)
        self.assertEqual(discrepancy["pdf_worked_example"]["tokens_before_separator"], 5)
        self.assertEqual(discrepancy["txt_card"]["ref"], "L31-TXT1-55")
        self.assertEqual(discrepancy["pdf_worked_example"]["ref"], "L31-PDF1-p1-l18")
        self.assertIn("F# A | B", discrepancy["txt_card"]["text"])
        self.assertIn("F# | A B", discrepancy["pdf_worked_example"]["text"])
        self.assertTrue(discrepancy["sounding_tone_order_same"])
        self.assertIsNone(discrepancy["resolution"])
        bad = copy.deepcopy(self.discrepancies)
        bad[0]["resolution"] = "invented"
        with self.assertRaisesRegex(level31.SourceError, "source discrepancy lost or falsely resolved"):
            level31.assemble(self.cards, self.guidance, bad)

    def test_authored_guidance_is_not_machine_timing_or_admission(self) -> None:
        result = self.candidate
        intro = "\n".join(result["source_guidance"]["txt_intro_lines_1_52"])
        tail = "\n".join(result["source_guidance"]["txt_after_cards_lines_235_259"])
        self.assertIn("Begin 10-15 BPM below your clean Level 30 tempo.", intro)
        self.assertIn("play even eighth notes", intro)
        self.assertIn("Do not restart the pick cycle", intro)
        self.assertIn("25 cells x 22 notes = 550 picked notes.", tail)
        self.assertEqual(result["pick_start_options"], ["D", "U"])
        self.assertTrue(result["tempo_and_picking_are_source_guidance_only"])
        self.assertFalse(result["canonical_schema_validated"] or result["runtime_eligible"]
                         or result["imported"] or result["admitted"] or result["whole_workbook_complete"])
        for record in result["records"]:
            for field in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "note_per_click", "fixed_bpm"):
                self.assertIsNone(record[field])
            self.assertFalse(record["runtime_eligible"] or record["imported"] or record["admitted"])

    def test_source_pins_and_route_drift_refuse(self) -> None:
        with self.assertRaisesRegex(level31.SourceError, "pinned input drift"):
            level31.read_pinned(ROOT, (level31.TXT[0], "0" * 64, level31.TXT[2]))
        with self.assertRaisesRegex(level31.SourceError, "pinned input drift"):
            level31.read_pinned(ROOT, (level31.PDF[0], "0" * 64, level31.PDF[2]))
        bad_txt = self.txt.replace(b"DOWN: A(17) > Ab(16)", b"DOWN: A(17) > A(16)")
        with self.assertRaisesRegex(level31.SourceError, "TXT key-route guidance drift"):
            level31.parse_sources(bad_txt, self.pdf)
        bad_txt = self.txt.replace(b"RUNG 08 OF 13", b"RUNG 09 OF 13")
        with self.assertRaisesRegex(level31.SourceError, "rung/key/root/frame conflict"):
            cards, guidance, discrepancies = level31.parse_sources(bad_txt, self.pdf)
            level31.assemble(cards, guidance, discrepancies)

    def test_card_loss_duplicates_pdf_map_and_note_conflicts_refuse(self) -> None:
        with self.assertRaisesRegex(level31.SourceError, "missing/duplicate/out-of-order rung"):
            level31.assemble(self.cards[:-1], self.guidance, self.discrepancies)
        bad = list(self.cards)
        bad[1] = bad[0]
        with self.assertRaisesRegex(level31.SourceError, "missing/duplicate/out-of-order rung"):
            level31.assemble(bad, self.guidance, self.discrepancies)
        bad = self.changed_card(10)
        bad[9]["pdf_route_map_row"][1] = "F major pentatonic"
        with self.assertRaisesRegex(level31.SourceError, "PDF route-map/rung conflict"):
            level31.assemble(bad, self.guidance, self.discrepancies)
        for row, old, new, expected in ((3, "1--", "4--", "degree/finger order conflict"),
                                        (4, "2--", "3--", "degree/finger order conflict"),
                                        (10, "5--", "6--", "TAB string/fret conflict")):
            bad = self.changed_card(1)
            card = bad[0]
            if row == 10:
                card["txt_body"][row] = card["txt_body"][row].replace("E  |5--", "E  |6--", 1)
            else:
                card["txt_body"][row] = card["txt_body"][row].replace(old, new, 1)
            card["pdf_block"][row + 1] = card["txt_body"][row]
            with self.subTest(row=row), self.assertRaisesRegex(level31.SourceError, expected):
                level31.assemble(bad, self.guidance, self.discrepancies)
        bad = self.changed_card(1)
        card = bad[0]
        card["txt_body"][9] = card["txt_body"][9].replace("A  |---", "A  |4--", 1)
        card["pdf_block"][10] = card["txt_body"][9]
        with self.assertRaisesRegex(level31.SourceError, "TAB column note count"):
            level31.assemble(bad, self.guidance, self.discrepancies)

    def test_determinism_and_output_refusal(self) -> None:
        first = json.dumps(level31.build(ROOT), ensure_ascii=False, sort_keys=True, indent=2)
        second = json.dumps(level31.build(ROOT), ensure_ascii=False, sort_keys=True, indent=2)
        self.assertEqual(first, second)
        command = [sys.executable, "-m", "Tools.curriculum_level031_whole_candidate", "--output"]
        bad = subprocess.run(command + [str(ROOT / "Results" / "forbidden.json")], cwd=ROOT,
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertIn("new JSON file", bad.stderr)
        existing = ROOT / level31.BUILD_REL / "candidate-initial.json"
        before = existing.read_bytes()
        bad = subprocess.run(command + [str(existing)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(existing.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
