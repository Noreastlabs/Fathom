#!/usr/bin/env python3
"""Focused source and safety proof for detached Level 12 whole-ladder conversion."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Tools"))
import parallel_07_level012_whole_candidate as level12


class Level12WholeCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = level12.build_candidate()
        cls.build = level12.ROOT / level12.BUILD_REL
        cls.build.mkdir(parents=True, exist_ok=True)

    def test_exact_source_scope_and_all_thirteen_rungs(self) -> None:
        candidate = self.candidate
        self.assertEqual((candidate["wbs_id"], candidate["level"]), ("2.3.1.1.1", 12))
        self.assertEqual(candidate["schema"], "fathom-level012-whole-detached-candidate-v1")
        self.assertEqual(candidate["source"]["txt_sha256"], level12.TXT_SHA256)
        self.assertEqual(candidate["source"]["pdf_sha256"], level12.PDF_SHA256)
        self.assertEqual(candidate["source"]["selected_pdf_card_pages"], [3, 4, 5, 6])
        records = candidate["records"]
        self.assertEqual(len(records), 13)
        self.assertEqual(tuple(row["rung_number"] for row in records), tuple(f"{n:02d}" for n in range(1, 14)))
        self.assertEqual(tuple(row["key"] for row in records), level12.KEYS)
        self.assertEqual(tuple(row["root_fret"] for row in records), tuple(range(5, 18)))
        self.assertEqual(candidate["exceptions"], [])

    def test_txt_pdf_cards_table_and_lineage(self) -> None:
        txt = (level12.ROOT / level12.TXT_REL).read_bytes().decode("utf-8")
        pdf = (level12.ROOT / level12.PDF_REL).read_bytes()
        txt_cards, _, _ = level12._txt_cards(txt)
        pdf_cards, table = level12._pdf_cards(pdf)
        self.assertEqual((len(txt_cards), len(pdf_cards), len(table)), (13, 13, 13))
        for index, (txt_card, pdf_card, row, record) in enumerate(
            zip(txt_cards, pdf_cards, table, self.candidate["records"], strict=True)
        ):
            start = 42 + 14 * index
            self.assertEqual((txt_card["heading_line"], txt_card["last_line"]), (start, start + 11))
            self.assertEqual(record["source_refs"], {
                "txt": f"L12-TXT1-{start}-{start + 11}",
                "pdf_card": f"L12-PDF1-p{3 + index // 4}", "pdf_route_table": "L12-PDF1-p2",
            })
            self.assertEqual(pdf_card["scale_tones"], txt_card["scale_tones"])
            self.assertEqual(pdf_card["raw_rows"], txt_card["raw_rows"])
            self.assertEqual(record["raw_rows"], txt_card["raw_rows"])
            self.assertEqual(record["notes"], txt_card["notes"])
            self.assertEqual(row["tones_1_to_7"], record["scale_tones"][:7])
            self.assertEqual(row["root_fret"], record["root_fret"])

    def test_all_208_notes_degrees_fingers_strings_and_pitch_spellings(self) -> None:
        note_count = 0
        for record in self.candidate["records"]:
            r = record["root_fret"]
            notes = record["notes"]
            self.assertEqual(len(notes), 16)
            note_count += len(notes)
            expected_frets = (r, r + 2, r - 1, r, r + 2, r - 1, r + 1, r + 2,
                              r + 2, r + 1, r - 1, r + 2, r, r - 1, r + 2, r)
            self.assertEqual(tuple(note["fret"] for note in notes), expected_frets)
            self.assertEqual(tuple(note["string"] for note in notes), level12.NOTE_STRINGS)
            self.assertEqual(tuple(note["degree"] for note in notes), level12.DEGREES)
            self.assertEqual(tuple(note["finger_digit"] for note in notes), level12.FINGERS)
            self.assertEqual(tuple(note["ordinal"] for note in notes), tuple(range(1, 17)))
            self.assertEqual(tuple(note["tone"] for note in notes),
                             tuple(record["scale_tones"][degree - 1] for degree in level12.DEGREES))
            self.assertEqual((notes[7]["string"], notes[7]["fret"]), (notes[8]["string"], notes[8]["fret"]))
            self.assertEqual(level12.OPEN_MIDI[notes[7]["string"]] + notes[7]["fret"],
                             level12.OPEN_MIDI[notes[0]["string"]] + notes[0]["fret"] + 12)
            columns = [match.start() for row in record["raw_rows"][2:]
                       for match in re.finditer(r"\d+", row.split("|")[1])]
            self.assertEqual(tuple(note["ascii_column"] for note in notes), tuple(sorted(columns)))
            self.assertTrue(all(note["onset_q"] is None and note["duration_q"] is None for note in notes))
        self.assertEqual(note_count, 208)
        self.assertEqual(self.candidate["records"][3]["scale_tones"], ["C", "D", "E", "F", "G", "A", "B", "C"])
        self.assertEqual(self.candidate["records"][9]["scale_tones"], ["Gb", "Ab", "Bb", "Cb", "Db", "Eb", "F", "Gb"])
        self.assertEqual(self.candidate["records"][0]["scale_tones"], self.candidate["records"][-1]["scale_tones"])

    def test_up_down_and_continuous_round_trip_orders(self) -> None:
        routes = self.candidate["routes"]
        up = [f"L12-rung{n:02d}" for n in range(1, 14)]
        down = list(reversed(up))
        self.assertEqual(routes["up"]["rungs"], up)
        self.assertEqual(routes["up"]["root_frets"], list(range(5, 18)))
        self.assertEqual(routes["up"]["shift_frets_between_cells"], 1)
        self.assertEqual(routes["down"]["rungs"], down)
        self.assertEqual(routes["down"]["root_frets"], list(range(17, 4, -1)))
        self.assertEqual(routes["down"]["shift_frets_between_cells"], -1)
        trip = routes["continuous_round_trip"]
        self.assertEqual(trip["rungs"], up + down[1:])
        self.assertEqual(trip["return_rungs"], down[1:])
        self.assertEqual(len(trip["rungs"]), 25)
        self.assertEqual(trip["rungs"].count("L12-rung13"), 1)
        self.assertIn("A(5) > Bb(6)", routes["up"]["source_text"])
        self.assertIn("A(17) > Ab(16)", routes["down"]["source_text"])

    def test_source_guidance_is_instruction_only_and_no_admission(self) -> None:
        instructions = self.candidate["instructions"]
        self.assertIn("A major is the starting rung, not the key of every rung", instructions["overview_text"])
        self.assertIn("octave root is repeated", instructions["overview_text"])
        self.assertIn("return through rungs 12-01", instructions["round_trip_text"])
        self.assertIn("These are variants of Level 12", instructions["after_mastery_text"])
        self.assertEqual(instructions["after_mastery_ref"], "L12-TXT1-229-231")
        self.assertFalse(self.candidate["whole_workbook_complete"])
        for row in [self.candidate, *self.candidate["records"]]:
            for flag in ("runtime_eligible", "runtime_admitted", "imported", "admitted"):
                self.assertFalse(row[flag])
        for record in self.candidate["records"]:
            for field in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "fixed_bpm", "note_per_click"):
                self.assertIsNone(record[field])

    def test_source_drift_and_bad_cell_refuse(self) -> None:
        txt = (level12.ROOT / level12.TXT_REL).read_bytes()
        pdf = (level12.ROOT / level12.PDF_REL).read_bytes()
        with self.assertRaisesRegex(level12.CandidateError, "PINNED_INPUT_DRIFT L12-TXT"):
            level12.build_candidate(txt_data=txt[:-1])
        with self.assertRaisesRegex(level12.CandidateError, "PINNED_INPUT_DRIFT L12-PDF"):
            level12.build_candidate(pdf_data=pdf[:-1])
        first = self.candidate["records"][0]
        rows = list(first["raw_rows"])
        rows[1] = rows[1].replace("2--4", "3--4", 1)
        with self.assertRaisesRegex(level12.CandidateError, "DEGREE_OR_FINGER_SEQUENCE_INVALID"):
            level12._tab_notes(rows, first["root_fret"], first["scale_tones"])
        rows = list(first["raw_rows"])
        rows[-1] = rows[-1].replace("5--7", "5--8", 1)
        with self.assertRaisesRegex(level12.CandidateError, "TAB_TRANSPOSED_SHAPE_MISMATCH"):
            level12._tab_notes(rows, first["root_fret"], first["scale_tones"])

    def test_output_confined_no_overwrite_or_symlink(self) -> None:
        output = self.build / f"test-output-{uuid.uuid4().hex}.json"
        info = level12.write_candidate(output)
        try:
            self.assertEqual(info["records"], 13)
            self.assertEqual(json.loads(output.read_text()), self.candidate)
            with self.assertRaisesRegex(level12.CandidateError, "OUTPUT_EXISTS"):
                level12.write_candidate(output)
            with self.assertRaisesRegex(level12.CandidateError, "OUTPUT_OUTSIDE_LANE_BUILD"):
                level12.write_candidate(level12.ROOT / "Content" / output.name)
            linked = self.build / f"linked-{output.name}"
            linked.symlink_to(output)
            try:
                with self.assertRaisesRegex(level12.CandidateError, "OUTPUT_INVALID"):
                    level12.write_candidate(linked)
            finally:
                linked.unlink()
        finally:
            output.unlink()

    def test_candidate_json_is_deterministic(self) -> None:
        encoded = (json.dumps(self.candidate, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        repeated = (json.dumps(level12.build_candidate(), indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        self.assertEqual(encoded, repeated)
        self.assertEqual(encoded, (self.build / "candidate.json").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
