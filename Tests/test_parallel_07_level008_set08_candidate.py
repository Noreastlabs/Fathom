#!/usr/bin/env python3
"""Focused proof for the detached Level 8 Set 8 position ladder candidate."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))
import parallel_07_level008_set08_candidate as level8


class Level8Set8CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = level8.build_candidate()
        cls.build = level8.ROOT / level8.BUILD_REL
        cls.build.mkdir(parents=True, exist_ok=True)

    def test_exact_source_scope_and_set(self) -> None:
        candidate = self.candidate
        self.assertEqual((candidate["wbs_id"], candidate["level"], candidate["set"]), ("2.3.1.1.1", 8, 8))
        self.assertEqual(candidate["schema"], "fathom-level008-set08-detached-candidate-v1")
        self.assertEqual(candidate["source"]["txt_sha256"], level8.TXT_SHA256)
        self.assertEqual(candidate["source"]["pdf_sha256"], level8.PDF_SHA256)
        self.assertEqual((candidate["source"]["pdf_pages"], candidate["source"]["selected_pdf_page"]), (10, 9))
        self.assertEqual(tuple(row["exercise_number"] for row in candidate["records"]), tuple(f"{n:03d}" for n in range(85, 97)))
        self.assertEqual(tuple(row["code"] for row in candidate["records"]), level8.CODES)
        self.assertEqual(candidate["exceptions"], [])

    def test_txt_pdf_all_cards_and_lineage(self) -> None:
        txt = (level8.ROOT / level8.TXT_REL).read_bytes().decode("utf-8")
        pdf = (level8.ROOT / level8.PDF_REL).read_bytes()
        txt_cards, _ = level8._txt_cards(txt)
        pdf_cards = level8._pdf_cards(pdf)
        expected_lines = tuple(range(1403, 1580, 16))
        self.assertEqual(len(txt_cards), len(pdf_cards))
        self.assertEqual(len(txt_cards), 12)
        for txt_card, pdf_card, record, start in zip(txt_cards, pdf_cards, self.candidate["records"], expected_lines, strict=True):
            self.assertEqual((txt_card["number"], txt_card["code"]), (pdf_card["number"], pdf_card["code"]))
            self.assertEqual((txt_card["heading_line"], txt_card["last_line"]), (start, start + 14))
            self.assertEqual(record["source_refs"], {"txt": f"L8-TXT1-{start}-{start + 14}", "pdf": "L8-PDF1-p9"})
            for direction in record["directions"]:
                name = direction["direction"]
                rows = txt_card["directions"][name]
                template = pdf_card["templates"][name]
                self.assertEqual(direction["txt_tab_rows_high_to_low"], rows)
                self.assertEqual(direction["pdf_template"], template)
                self.assertTrue(all("S" + row[1:] == template for row in rows))

    def test_complete_shift_routes_and_note_facts(self) -> None:
        routes = cells = notes = 0
        for record in self.candidate["records"]:
            self.assertEqual(record["source_local_key"], f'L8-set08-ex{record["exercise_number"]}')
            self.assertEqual(tuple(d["direction"] for d in record["directions"]), ("shift_up", "shift_down"))
            for direction in record["directions"]:
                name = direction["direction"]
                order = level8.ROUTE_ORDERS[name]
                positions = ("P5", "P7") if name == "shift_up" else ("P7", "P5")
                self.assertEqual(tuple(direction["route_order"]), order)
                self.assertEqual(tuple(route["string"] for route in direction["routes"]), order)
                self.assertEqual(len(direction["routes"]), 6)
                for route in direction["routes"]:
                    routes += 1
                    self.assertEqual(route["shift_after_cell"], 1)
                    self.assertTrue(route["shift_at_center_barline"])
                    self.assertEqual(route["hand_frame_shift_frets"], 2 if name == "shift_up" else -2)
                    self.assertEqual(tuple(cell["position"] for cell in route["cells"]), positions)
                    self.assertEqual(len(route["cells"]), 2)
                    self.assertEqual(route["source_tab_row"], next(row for row in direction["txt_tab_rows_high_to_low"] if row[0] == route["string"]))
                    source_cells = route["source_tab_row"].split("|")[1:3]
                    for cell, source_cell in zip(route["cells"], source_cells, strict=True):
                        cells += 1
                        self.assertEqual(len(cell["notes"]), 4)
                        notes += len(cell["notes"])
                        self.assertEqual(tuple(note["ordinal"] for note in cell["notes"]), (1, 2, 3, 4))
                        self.assertEqual(tuple(note["fret"] for note in cell["notes"]),
                                         tuple(int(digit) + level8.POSITIONS[cell["position"]] for digit in record["code"]))
                        self.assertEqual(tuple(note["finger_digit"] for note in cell["notes"]), tuple(record["code"]))
                        self.assertEqual(tuple(note["finger_name"] for note in cell["notes"]),
                                         tuple(level8.FINGER_NAMES[digit] for digit in record["code"]))
                        self.assertEqual(tuple(note["ascii_column"] for note in cell["notes"]),
                                         tuple(match.start() for match in re.finditer(r"\d+", source_cell)))
                        self.assertTrue(all(note["onset_q"] is None and note["duration_q"] is None for note in cell["notes"]))
        self.assertEqual((routes, cells, notes), (144, 288, 1152))
        first = self.candidate["records"][0]["directions"][0]["routes"][0]
        self.assertEqual(first["string"], "E")
        self.assertEqual(tuple(note["fret"] for cell in first["cells"] for note in cell["notes"]),
                         (8, 5, 7, 5, 10, 7, 9, 7))
        last = self.candidate["records"][-1]["directions"][1]["routes"][0]
        self.assertEqual(last["string"], "e")
        self.assertEqual(tuple(note["fret"] for cell in last["cells"] for note in cell["notes"]),
                         (10, 8, 9, 10, 8, 6, 7, 8))

    def test_guidance_is_instruction_only(self) -> None:
        instructions = self.candidate["instructions"]
        self.assertEqual(instructions["position_maps"]["P5"]["4"], {"name": "pinky", "fret": 8})
        self.assertEqual(instructions["position_maps"]["P7"]["4"], {"name": "pinky", "fret": 10})
        self.assertIn("not simultaneous chord tones", instructions["movement_rule_text"])
        for phrase in ("pause one subdivision", "straight 16ths", "downstroke start", "upstroke start", "two separate days"):
            self.assertIn(phrase, instructions["practice_rule_text"])
        self.assertEqual(instructions["pdf_ref"], "L8-PDF1-p1")

    def test_no_identity_timing_or_admission(self) -> None:
        candidate = self.candidate
        self.assertFalse(candidate["whole_workbook_complete"])
        for row in [candidate, *candidate["records"]]:
            for flag in ("runtime_eligible", "runtime_admitted", "imported", "admitted"):
                self.assertFalse(row[flag])
        for record in candidate["records"]:
            for field in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "fixed_bpm", "note_per_click"):
                self.assertIsNone(record[field])

    def test_source_drift_and_bad_route_refuse(self) -> None:
        txt = (level8.ROOT / level8.TXT_REL).read_bytes()
        pdf = (level8.ROOT / level8.PDF_REL).read_bytes()
        with self.assertRaisesRegex(level8.CandidateError, "PINNED_INPUT_DRIFT L8-TXT"):
            level8.build_candidate(txt_data=txt[:-1])
        with self.assertRaisesRegex(level8.CandidateError, "PINNED_INPUT_DRIFT L8-PDF"):
            level8.build_candidate(pdf_data=pdf[:-1])
        with self.assertRaisesRegex(level8.CandidateError, "TAB_CODE_POSITION_MISMATCH"):
            level8._cell("8-5-7-6----", "4131", "P5")
        with self.assertRaisesRegex(level8.CandidateError, "SET8_CARD_COUNT"):
            level8._blocks(["Exercise 085: 4131"], level8.TXT_HEADING)

    def test_output_confined_no_overwrite_or_symlink(self) -> None:
        output = self.build / f"test-output-{uuid.uuid4().hex}.json"
        info = level8.write_candidate(output)
        try:
            self.assertEqual(info["records"], 12)
            self.assertEqual(json.loads(output.read_text()), self.candidate)
            with self.assertRaisesRegex(level8.CandidateError, "OUTPUT_EXISTS"):
                level8.write_candidate(output)
            with self.assertRaisesRegex(level8.CandidateError, "OUTPUT_OUTSIDE_LANE_BUILD"):
                level8.write_candidate(level8.ROOT / "Content" / output.name)
            linked = self.build / f"linked-{output.name}"
            linked.symlink_to(output)
            try:
                with self.assertRaisesRegex(level8.CandidateError, "OUTPUT_INVALID"):
                    level8.write_candidate(linked)
            finally:
                linked.unlink()
        finally:
            output.unlink()

    def test_candidate_json_is_deterministic(self) -> None:
        encoded = (json.dumps(self.candidate, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        repeated = (json.dumps(level8.build_candidate(), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        self.assertEqual(encoded, repeated)
        self.assertEqual(encoded, (self.build / "candidate.json").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
