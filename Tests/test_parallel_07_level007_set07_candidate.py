#!/usr/bin/env python3
"""Focused source/structure tests for the detached Level 7 Set 7 candidate."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))
import parallel_07_level007_set07_candidate as level7


class Level7Set7CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = level7.build_candidate()
        cls.build = level7.ROOT / level7.BUILD_REL
        cls.build.mkdir(parents=True, exist_ok=True)

    def test_exact_source_and_scope(self) -> None:
        candidate = self.candidate
        self.assertEqual(candidate["wbs_id"], "2.3.1.1.1")
        self.assertEqual(candidate["level"], 7)
        self.assertEqual(candidate["set"], 7)
        self.assertEqual(candidate["schema"], "fathom-level007-set07-detached-candidate-v1")
        self.assertEqual(candidate["source"]["txt_sha256"], level7.TXT_SHA256)
        self.assertEqual(candidate["source"]["pdf_sha256"], level7.PDF_SHA256)
        self.assertEqual(candidate["source"]["pdf_pages"], 10)
        self.assertEqual(candidate["source"]["selected_pdf_page"], 8)
        self.assertEqual(len(candidate["records"]), 12)
        self.assertEqual(tuple(row["code"] for row in candidate["records"]), level7.CODES)
        self.assertEqual(tuple(row["exercise_number"] for row in candidate["records"]), tuple(f"{n:03d}" for n in range(73, 85)))
        self.assertEqual(candidate["exceptions"], [])
        self.assertIn("Level 7 candidate family review", candidate["pending"])

    def test_exact_txt_pdf_cards_and_lineage(self) -> None:
        txt_bytes = (level7.ROOT / level7.TXT_REL).read_bytes()
        pdf_bytes = (level7.ROOT / level7.PDF_REL).read_bytes()
        txt_cards, _ = level7._txt_cards(txt_bytes.decode("utf-8"))
        pdf_cards = level7._pdf_cards(pdf_bytes)
        expected_lines = (1206, 1222, 1238, 1254, 1270, 1286, 1302, 1318, 1334, 1350, 1366, 1382)
        self.assertEqual(len(txt_cards), 12)
        self.assertEqual(len(pdf_cards), 12)
        for index, (txt_card, pdf_card, record, line_start) in enumerate(
            zip(txt_cards, pdf_cards, self.candidate["records"], expected_lines, strict=True)
        ):
            self.assertEqual(txt_card["number"], f"{73 + index:03d}")
            self.assertEqual(pdf_card["number"], txt_card["number"])
            self.assertEqual(pdf_card["code"], txt_card["code"])
            self.assertEqual(pdf_card["directions"], txt_card["directions"])
            self.assertEqual(txt_card["heading_line"], line_start)
            self.assertEqual(txt_card["last_line"], line_start + 14)
            self.assertEqual(
                record["source_refs"],
                {"txt": f"L7-TXT1-{line_start}-{line_start + 14}", "pdf": "L7-PDF1-p8"},
            )
            self.assertEqual(
                tuple(direction["tab_rows"] for direction in record["directions"]),
                tuple(txt_card["directions"][name] for name in ("ascending", "descending")),
            )

    def test_all_four_routes_frets_fingers_pitches_and_silent_gaps(self) -> None:
        note_count = 0
        route_count = 0
        open_midi = {"E": 40, "A": 45, "D": 50, "G": 55, "B": 59, "e": 64}
        for record in self.candidate["records"]:
            self.assertTrue(record["source_local_key"].startswith("L7-set07-ex"))
            self.assertEqual(record["source_refs"]["pdf"], "L7-PDF1-p8")
            self.assertEqual(tuple(d["direction"] for d in record["directions"]), ("ascending", "descending"))
            for direction in record["directions"]:
                name = direction["direction"]
                self.assertEqual(len(direction["tab_rows"]), 6)
                self.assertEqual(len(direction["routes"]), 2)
                self.assertEqual(tuple(tuple(route["strings"]) for route in direction["routes"]), level7.ROUTES[name])
                for route in direction["routes"]:
                    route_count += 1
                    notes = route["notes"]
                    note_count += len(notes)
                    self.assertEqual(len(notes), 4)
                    self.assertEqual(route["silent_intervening_strings"], 2)
                    self.assertEqual(
                        tuple(note["string"] for note in notes),
                        (route["strings"][0], route["strings"][1], route["strings"][1], route["strings"][2]),
                    )
                    self.assertEqual(tuple(note["fret"] for note in notes), tuple(int(d) + 4 for d in record["code"]))
                    self.assertEqual(tuple(note["finger_digit"] for note in notes), tuple(record["code"]))
                    self.assertEqual(tuple(note["ascii_column"] for note in notes), (0, 2, 4, 6))
                    self.assertEqual(
                        tuple(note["finger_name"] for note in notes),
                        tuple(level7.FINGER_NAMES[digit] for digit in record["code"]),
                    )
                    self.assertTrue(all(note["onset_q"] is None and note["duration_q"] is None for note in notes))
                    pitches = tuple(open_midi[note["string"]] + note["fret"] for note in notes)
                    self.assertTrue(all(45 <= pitch <= 72 for pitch in pitches))
        self.assertEqual(route_count, 48)
        self.assertEqual(note_count, 192)
        first_route = self.candidate["records"][0]["directions"][0]["routes"][0]["notes"]
        self.assertEqual(tuple(open_midi[note["string"]] + note["fret"] for note in first_route), (47, 58, 55, 65))
        last_route = self.candidate["records"][-1]["directions"][1]["routes"][1]["notes"]
        self.assertEqual(tuple(open_midi[note["string"]] + note["fret"] for note in last_route), (67, 55, 56, 48))

    def test_printed_guidance_is_instruction_only(self) -> None:
        instructions = self.candidate["instructions"]
        self.assertEqual(instructions["finger_map"]["1"], {"name": "index", "fret": 5})
        self.assertEqual(instructions["finger_map"]["4"], {"name": "pinky", "fret": 8})
        text = instructions["practice_rule_text"]
        for phrase in (
            "10-15 BPM below", "opposite starting pick stroke", "landing notes 2 and 4",
            "Use straight 16ths first", "triplet and quintuplet", "add 2 BPM next session",
            "reduce 4-6 BPM", "two separate days",
        ):
            self.assertIn(phrase, text)
        self.assertTrue(instructions["pdf_ref"].endswith("p1"))
        self.assertIsNone(self.candidate["records"][0]["fixed_bpm"])
        self.assertIsNone(self.candidate["records"][0]["note_per_click"])

    def test_no_canonical_identity_or_admission(self) -> None:
        for row in [self.candidate, *self.candidate["records"]]:
            self.assertFalse(row["runtime_eligible"])
            self.assertFalse(row["runtime_admitted"])
            self.assertFalse(row["imported"])
            self.assertFalse(row["admitted"])
        self.assertFalse(self.candidate["whole_workbook_complete"])
        for row in self.candidate["records"]:
            self.assertIsNone(row["canonical_item_id"])
            self.assertIsNone(row["canonical_variant_id"])
            self.assertIsNone(row["onset_q"])
            self.assertIsNone(row["duration_q"])

    def test_source_drift_refuses_before_parse(self) -> None:
        source = (level7.ROOT / level7.TXT_REL).read_bytes()
        mutated = self.build / f"mutated-level007-set07-source-{uuid.uuid4().hex}.txt"
        mutated.write_bytes(source[:-1] + bytes([source[-1] ^ 1]))
        try:
            with self.assertRaisesRegex(level7.CandidateError, "PINNED_INPUT_DRIFT L7-TXT"):
                level7.build_candidate(txt_data=mutated.read_bytes())
        finally:
            mutated.unlink()
        pdf = (level7.ROOT / level7.PDF_REL).read_bytes()
        with self.assertRaisesRegex(level7.CandidateError, "PINNED_INPUT_DRIFT L7-PDF"):
            level7.build_candidate(pdf_data=pdf[:-1])

    def test_bad_tab_route_and_set_boundary_refuse(self) -> None:
        rows = list(self.candidate["records"][0]["directions"][0]["tab_rows"])
        rows[3] = rows[3].replace("5", "6", 1)
        with self.assertRaisesRegex(level7.CandidateError, "TAB_CODE_ROUTE_MISMATCH"):
            level7._route(rows, level7.ROUTES["ascending"][0], 0, "3412")
        with self.assertRaisesRegex(level7.CandidateError, "SET7_CARD_COUNT"):
            level7._blocks(["Exercise 073: 3412", "Exercise 074: 3413"], level7.TXT_HEADING)

    def test_output_is_confined_and_no_replace(self) -> None:
        name = f"test-output-{uuid.uuid4().hex}.json"
        output = self.build / name
        info = level7.write_candidate(output)
        try:
            self.assertEqual(info["records"], 12)
            self.assertEqual(json.loads(output.read_text())["records"], self.candidate["records"])
            with self.assertRaisesRegex(level7.CandidateError, "OUTPUT_EXISTS"):
                level7.write_candidate(output)
            with self.assertRaisesRegex(level7.CandidateError, "OUTPUT_OUTSIDE_LANE_BUILD"):
                level7.write_candidate(level7.ROOT / "Content" / name)
            linked = self.build / f"linked-{name}"
            linked.symlink_to(output)
            try:
                with self.assertRaisesRegex(level7.CandidateError, "OUTPUT_INVALID"):
                    level7.write_candidate(linked)
            finally:
                linked.unlink()
        finally:
            output.unlink()

    def test_candidate_json_is_deterministic(self) -> None:
        encoded = json.dumps(self.candidate, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        repeated = level7.build_candidate()
        self.assertEqual(encoded, json.dumps(repeated, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
