"""Focused source and mutation checks for the detached Level 26 ladder."""

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
import parallel_07_level026_whole_candidate as lane  # noqa: E402


class Level26CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = (ROOT / lane.TXT_REL).read_bytes()
        cls.pdf = (ROOT / lane.PDF_REL).read_bytes()
        cls.candidate = lane.build_candidate(txt_data=cls.txt, pdf_data=cls.pdf)

    def test_all_authored_groups_geometry_and_route(self) -> None:
        data = self.candidate
        records = data["records"]
        self.assertEqual(len(records), 13)
        self.assertEqual([card["key"] for card in records], list(lane.KEYS))
        self.assertEqual([card["root_fret"] for card in records], list(range(5, 18)))
        self.assertEqual(sum(len(direction["groups"]) for card in records for direction in card["directions"]), 312)
        self.assertEqual(sum(len(direction["notes"]) for card in records for direction in card["directions"]), 1248)
        for index, card in enumerate(records):
            self.assertEqual(card["source_refs"]["txt"], f"L26-TXT1-{79 + 24 * index}-{100 + 24 * index}")
            self.assertEqual(card["source_refs"]["pdf_card"], f"L26-PDF1-p{3 + index // 2}")
            self.assertEqual((card["frame_low"], card["frame_high"]),
                             (card["root_fret"] - 1, card["root_fret"] + 3))
            self.assertEqual(card["degree_map"], list(lane.DEGREES))
            up, down = card["directions"]
            self.assertEqual((up["direction"], down["direction"]), ("ascending", "descending"))
            for direction, expected_positions, expected_paths in (
                (up, lane.ASC_POSITIONS, lane.UP_PATHS),
                (down, lane.DESC_POSITIONS, lane.DOWN_PATHS),
            ):
                self.assertEqual(len(direction["raw_rows"]), 8)
                self.assertEqual(len(direction["groups"]), 12)
                self.assertEqual(len(direction["notes"]), 48)
                self.assertEqual([group["positions"] for group in direction["groups"]],
                                 [list(group) for group in expected_positions])
                self.assertEqual([group["string_path"] for group in direction["groups"]], list(expected_paths))
                for group in direction["groups"]:
                    notes = [direction["notes"][ordinal - 1] for ordinal in group["note_ordinals"]]
                    self.assertEqual([note["position"] for note in notes], group["positions"])
                    self.assertEqual([note["degree"] for note in notes], group["degrees"])
                    self.assertEqual("".join(note["string"] for note in notes), group["string_path"])
                    self.assertEqual([note["ascii_column_in_group"] for note in notes], [0, 3, 6, 9])
                    for note in notes:
                        string, offset, finger = lane.POSITION_MAP[note["position"] - 1]
                        self.assertEqual((note["string"], note["fret"], note["finger_digit"]),
                                         (string, card["root_fret"] + offset, finger))
                        self.assertEqual((lane.OPEN_MIDI[string] + note["fret"]) % 12,
                                         lane._pitch_class(note["tone"]))
                        self.assertEqual(note["degree"], lane.DEGREES[note["position"] - 1])
                        self.assertIsNone(note["onset_q"])
                        self.assertIsNone(note["duration_q"])
            self.assertEqual((up["notes"][0]["string"], up["notes"][0]["fret"]), ("E", card["root_fret"]))
            self.assertEqual((down["notes"][-1]["string"], down["notes"][-1]["fret"]), ("E", card["root_fret"]))
            self.assertEqual((up["notes"][-1]["position"], up["notes"][-1]["string"], up["notes"][-1]["fret"]),
                             (15, "e", card["root_fret"]))
            self.assertEqual((down["notes"][0]["position"], down["notes"][0]["string"], down["notes"][0]["fret"]),
                             (15, "e", card["root_fret"]))
            self.assertIsNone(card["canonical_item_id"])
            self.assertIsNone(card["canonical_variant_id"])
            self.assertFalse(card["runtime_eligible"])
            self.assertFalse(card["admitted"])
        self.assertEqual(records[6]["scale_tones"][:7], ["Eb", "F", "Gb", "Ab", "Bb", "Cb", "Db"])
        self.assertEqual(records[12]["key"], "A")
        self.assertTrue(records[12]["octave_rung"])
        self.assertEqual(data["shape"]["position_map"][8]["fret_offset_from_root"], -1)
        self.assertEqual([data["shape"]["position_map"][i]["string"] for i in (11, 12, 13)], ["B"] * 3)
        route = data["routes"]
        up_ids = [card["source_local_key"] for card in records]
        self.assertEqual(route["up"]["rungs"], up_ids)
        self.assertEqual(route["down_standalone"]["rungs"], list(reversed(up_ids)))
        self.assertEqual(route["down_return"]["rungs"], list(reversed(up_ids[:-1])))
        self.assertEqual(route["continuous_round_trip"]["rungs"], up_ids + list(reversed(up_ids[:-1])))
        self.assertEqual(route["continuous_round_trip"]["cell_count"], 25)
        self.assertEqual(route["continuous_round_trip"]["picked_note_count"], 2400)
        self.assertEqual(route["continuous_round_trip"]["rungs"].count("L26-rung13"), 1)
        self.assertFalse(data["runtime_eligible"])
        self.assertFalse(data["admitted"])
        self.assertFalse(data["whole_workbook_complete"])

    def test_all_pdf_rows_and_one_fret_transposition(self) -> None:
        txt_cards, _, _ = lane._txt_cards(self.txt.decode("utf-8"))
        pdf_cards, pdf_table = lane._pdf_cards(self.pdf)
        self.assertEqual(len(pdf_cards), 13)
        for index, (txt_card, pdf_card, row) in enumerate(zip(txt_cards, pdf_cards, pdf_table, strict=True)):
            self.assertEqual(pdf_card["ascending_rows"], txt_card["directions"][0]["raw_rows"])
            self.assertEqual(pdf_card["descending_rows"], txt_card["directions"][1]["raw_rows"])
            self.assertEqual(pdf_card["scale_tones"], txt_card["scale_tones"])
            self.assertEqual(row["tones_1_to_7"], txt_card["scale_tones"][:7])
            if index:
                for direction, base in zip(txt_card["directions"], txt_cards[0]["directions"], strict=True):
                    self.assertEqual([(note["string"], note["fret"], note["finger_digit"], note["position"])
                                      for note in direction["notes"]],
                                     [(note["string"], note["fret"] + index, note["finger_digit"], note["position"])
                                      for note in base["notes"]])

    def test_pins_and_authored_mutations(self) -> None:
        changed = bytearray(self.txt)
        changed[0] = ord("X")
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L26-TXT"):
            lane.build_candidate(txt_data=bytes(changed), pdf_data=self.pdf)
        changed_pdf = bytearray(self.pdf)
        changed_pdf[-1] ^= 1
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L26-PDF"):
            lane.build_candidate(txt_data=self.txt, pdf_data=bytes(changed_pdf))
        source = self.txt.decode("utf-8")
        mutations = [
            ("Pos|1--2--3--4--", "Pos|1--2--3--5--", "GROUP_POSITION_OR_FINGER_INVALID"),
            ("Fng|1--3--4--1--", "Fng|1--3--4--2--", "GROUP_GEOMETRY_OR_FINGER_MISMATCH"),
            ("E  |5--7--8-----", "E  |6--7--8-----", "GROUP_GEOMETRY_OR_FINGER_MISMATCH"),
            ("DOWN: A(17) > G#(16)", "DOWN: A(17) > G(16)", "TXT_CHROMATIC_ROUTE_MISMATCH"),
        ]
        for before, after, expected in mutations:
            self.assertIn(before, source)
            modified = source.replace(before, after, 1).encode("utf-8")
            with self.subTest(expected=expected), patch.object(lane, "TXT_BYTES", len(modified)), patch.object(
                lane, "TXT_SHA256", hashlib.sha256(modified).hexdigest()
            ):
                with self.assertRaisesRegex(lane.CandidateError, expected):
                    lane.build_candidate(txt_data=modified, pdf_data=self.pdf)

    def test_output_is_deterministic_and_confined(self) -> None:
        expected = (json.dumps(self.candidate, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        output = ROOT / lane.BUILD_REL / "candidate.json"
        self.assertEqual(output.read_bytes(), expected)
        self.assertEqual(hashlib.sha256(expected).hexdigest(), "04960145804f4e6d86c12a6b953a4666b541f47af68d16b5f2679a23c754880b")
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
