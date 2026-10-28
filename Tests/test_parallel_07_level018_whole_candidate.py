"""Focused source and mutation checks for the detached Level 18 thirds ladder."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))
import parallel_07_level018_whole_candidate as lane  # noqa: E402


class Level18CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = (ROOT / lane.TXT_REL).read_bytes()
        cls.pdf = (ROOT / lane.PDF_REL).read_bytes()
        cls.candidate = lane.build_candidate(txt_data=cls.txt, pdf_data=cls.pdf)

    def test_all_authored_pairs_and_routes(self) -> None:
        data = self.candidate
        records = data["records"]
        self.assertEqual(len(records), 13)
        self.assertEqual([card["key"] for card in records], list(lane.KEYS))
        self.assertEqual([card["root_fret"] for card in records], list(range(5, 18)))
        self.assertEqual(sum(len(direction["pairs"]) for card in records for direction in card["directions"]), 338)
        self.assertEqual(sum(len(direction["notes"]) for card in records for direction in card["directions"]), 676)
        for index, card in enumerate(records):
            self.assertEqual(card["source_refs"]["txt"], f"L18-TXT1-{72 + 27 * index}-{95 + 27 * index}")
            self.assertEqual(card["source_refs"]["pdf_card"], f"L18-PDF1-p{3 + index // 2}")
            self.assertEqual(card["frame_low"], card["root_fret"] - 1)
            self.assertEqual(card["frame_high"], card["root_fret"] + 2)
            up, down = card["directions"]
            self.assertEqual(up["direction"], "ascending")
            self.assertEqual(down["direction"], "descending")
            self.assertEqual([pair["degrees"] for pair in up["pairs"]], [list(pair) for pair in lane.ASC_DEGREES])
            self.assertEqual([pair["degrees"] for pair in down["pairs"]], [list(pair) for pair in lane.DESC_DEGREES])
            self.assertEqual([pair["quality"] for pair in up["pairs"]], list(lane.ASC_QUALITY))
            self.assertEqual([pair["quality"] for pair in down["pairs"]], list(lane.DESC_QUALITY))
            for direction in (up, down):
                self.assertEqual(len(direction["raw_rows"]), 9)
                self.assertEqual(len(direction["notes"]), 26)
                for pair in direction["pairs"]:
                    first, second = (direction["notes"][i - 1] for i in pair["note_ordinals"])
                    self.assertEqual([first["degree"], second["degree"]], pair["degrees"])
                    self.assertEqual(first["pair_ordinal"], pair["ordinal"])
                    self.assertEqual(second["pair_ordinal"], pair["ordinal"])
                    self.assertLess(first["ascii_column_in_pair"], second["ascii_column_in_pair"])
                    self.assertEqual(pair["semitones"], 4 if pair["quality"] == "M3" else 3)
                    for note in (first, second):
                        self.assertIn(note["string"], lane.OPEN_MIDI)
                        self.assertIn(note["finger_digit"], range(1, 5))
                        self.assertEqual((lane.OPEN_MIDI[note["string"]] + note["fret"]) % 12,
                                         lane._pitch_class(note["tone"]))
                        self.assertIsNone(note["onset_q"])
                        self.assertIsNone(note["duration_q"])
            self.assertEqual((up["notes"][0]["string"], up["notes"][0]["fret"]), ("E", card["root_fret"]))
            self.assertEqual((down["notes"][-1]["string"], down["notes"][-1]["fret"]), ("E", card["root_fret"]))
            self.assertEqual((up["notes"][-1]["string"], up["notes"][-1]["fret"]),
                             (down["notes"][0]["string"], down["notes"][0]["fret"]))
            self.assertFalse(card["pdf_card_has_int_row"])
            self.assertIsNone(card["canonical_item_id"])
            self.assertIsNone(card["canonical_variant_id"])
            self.assertFalse(card["runtime_eligible"])
            self.assertFalse(card["runtime_admitted"])
        gb = records[9]
        self.assertEqual(gb["scale_tones"][:7], ["Gb", "Ab", "Bb", "Cb", "Db", "Eb", "F"])
        self.assertEqual(records[12]["key"], "A")
        self.assertTrue(records[12]["octave_rung"])
        route = data["routes"]
        up_keys = route["up"]["rungs"]
        down_keys = route["down_return"]["rungs"]
        self.assertEqual(up_keys, [card["source_local_key"] for card in records])
        self.assertEqual(down_keys, list(reversed(up_keys[:-1])))
        self.assertEqual(route["continuous_round_trip"]["rungs"], up_keys + down_keys)
        self.assertEqual(route["continuous_round_trip"]["cell_count"], 25)
        self.assertEqual(route["continuous_round_trip"]["picked_note_count"], 1300)
        self.assertEqual(route["continuous_round_trip"]["rungs"].count("L18-rung13"), 1)
        self.assertEqual(len(data["exceptions"]), 1)
        self.assertEqual(data["exceptions"][0]["kind"], "pdf_layout")
        self.assertFalse(data["admitted"])
        self.assertFalse(data["whole_workbook_complete"])

    def test_cross_source_rows_and_transposition(self) -> None:
        txt_cards, _, _, txt_table = lane._txt_cards(self.txt.decode("utf-8"))
        pdf_cards, pdf_table, pdf_quality = lane._pdf_cards(self.pdf)
        self.assertEqual(pdf_quality, list(lane.ASC_QUALITY))
        self.assertEqual(len(pdf_cards), 13)
        for index, (txt_card, pdf_card) in enumerate(zip(txt_cards, pdf_cards, strict=True)):
            self.assertEqual(pdf_card["ascending_rows"], txt_card["directions"][0]["raw_rows"][1:])
            self.assertEqual(pdf_card["descending_rows"], txt_card["directions"][1]["raw_rows"][1:])
            self.assertEqual(pdf_card["scale_tones"], txt_card["scale_tones"])
            self.assertEqual(pdf_card["root_fret"], txt_card["root_fret"])
            self.assertEqual(pdf_table[index], txt_table[index])
            if index:
                for direction, base in zip(txt_card["directions"], txt_cards[0]["directions"], strict=True):
                    self.assertEqual([(note["string"], note["fret"]) for note in direction["notes"]],
                                     [(note["string"], note["fret"] + index) for note in base["notes"]])

    def test_pins_reject_drift_and_parser_rejects_authored_mutations(self) -> None:
        mutated = bytearray(self.txt)
        mutated[0] = ord("X")
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L18-TXT"):
            lane.build_candidate(txt_data=bytes(mutated), pdf_data=self.pdf)
        mutated_pdf = bytearray(self.pdf)
        mutated_pdf[-1] ^= 1
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L18-PDF"):
            lane.build_candidate(txt_data=self.txt, pdf_data=bytes(mutated_pdf))
        source = self.txt.decode("utf-8")
        alterations = [
            ("Int|M3----|m3----", "Int|m3----|m3----", "PAIR_QUALITY_PATTERN_MISMATCH"),
            ("E  |5-----|7-----", "E  |6-----|7-----", "PAIR_TONE_PITCH_MISMATCH"),
        ]
        for before, after, expected in alterations:
            self.assertIn(before, source)
            changed = source.replace(before, after, 1).encode("utf-8")
            with self.subTest(expected=expected), patch.object(lane, "TXT_BYTES", len(changed)), patch.object(
                lane, "TXT_SHA256", hashlib.sha256(changed).hexdigest()
            ):
                with self.assertRaisesRegex(lane.CandidateError, expected):
                    lane.build_candidate(txt_data=changed, pdf_data=self.pdf)

    def test_output_is_deterministic_and_confined(self) -> None:
        expected = (json.dumps(self.candidate, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        output = ROOT / lane.BUILD_REL / "candidate.json"
        self.assertEqual(output.read_bytes(), expected)
        self.assertEqual(hashlib.sha256(expected).hexdigest(), "9950bd9fad4f909d9ffcac3266612a88f093ab25b2897d8c259b28b6eb36ebf2")
        with self.assertRaisesRegex(lane.CandidateError, "OUTPUT_EXISTS"):
            lane.write_candidate(output)
        with tempfile.TemporaryDirectory() as tempdir:
            outside = Path(tempdir) / "candidate.json"
            with self.assertRaisesRegex(lane.CandidateError, "OUTPUT_OUTSIDE_LANE_BUILD"):
                lane.write_candidate(outside)
            link = ROOT / lane.BUILD_REL / "test-symlink.json"
            try:
                link.symlink_to(outside)
                with self.assertRaisesRegex(lane.CandidateError, "OUTPUT_INVALID"):
                    lane.write_candidate(link)
            finally:
                link.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
