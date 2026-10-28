"""Focused source and mutation checks for detached Level 32 sequence modules."""

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
import parallel_07_level032_whole_candidate as lane  # noqa: E402


class Level32CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt = (ROOT / lane.TXT_REL).read_bytes()
        cls.pdf = (ROOT / lane.PDF_REL).read_bytes()
        cls.candidate = lane.build_candidate(txt_data=cls.txt, pdf_data=cls.pdf)

    def test_all_groups_contacts_module_boundary_and_routes(self) -> None:
        data = self.candidate
        records = data["records"]
        self.assertEqual(len(records), 13)
        self.assertEqual([card["key"] for card in records], list(lane.KEYS))
        self.assertEqual([card["root_fret"] for card in records], list(range(5, 18)))
        self.assertEqual(sum(len(direction["groups"]) for card in records for module in card["modules"]
                             for direction in module["directions"]), 416)
        self.assertEqual(sum(len(direction["notes"]) for card in records for module in card["modules"]
                             for direction in module["directions"]), 1612)
        for index, card in enumerate(records):
            root_fret = card["root_fret"]
            self.assertEqual(card["source_refs"]["txt"], f"L32-TXT1-{63 + 50 * index}-{110 + 50 * index}")
            self.assertEqual(card["source_refs"]["pdf_card"], f"L32-PDF1-p{index + 3}")
            self.assertEqual((card["frame_low"], card["frame_high"]), (root_fret - 1, root_fret + 2))
            self.assertEqual(card["degree_map"], list(lane.DEGREES))
            self.assertEqual(card["linked_order"], ["A ascending", "A descending", "B ascending", "B descending"])
            self.assertEqual(card["linked_note_count"], 124)
            self.assertEqual(len(card["modules"]), 2)
            for module in card["modules"]:
                letter = module["module"]
                spec = lane.MODULES[letter]
                self.assertEqual(module["note_count"], spec["note_count"])
                self.assertEqual(module["group_size"], spec["size"])
                up, down = module["directions"]
                self.assertEqual((up["direction"], down["direction"]), ("ascending", "descending"))
                for direction in (up, down):
                    count = spec["groups_each_direction"]
                    size = spec["size"]
                    self.assertEqual(len(direction["raw_rows"]), 8)
                    self.assertEqual(len(direction["groups"]), count)
                    self.assertEqual(len(direction["notes"]), count * size)
                    self.assertEqual(direction["path_line"], "PATH " + " | ".join(lane.PATHS[letter][direction["direction"]]))
                    self.assertEqual([group["degrees"] for group in direction["groups"]],
                                     [list(window) for window in lane._expected_degrees(letter, direction["direction"])])
                    expected_pick_starts = ["D" if (group_index + (count if direction["direction"] == "descending" else 0)) % 2 == 0 else "U"
                                            for group_index in range(count)]
                    self.assertEqual([group["D_start_group_start_stroke"] for group in direction["groups"]],
                                     expected_pick_starts)
                    for group in direction["groups"]:
                        notes = [direction["notes"][ordinal - 1] for ordinal in group["note_ordinals"]]
                        self.assertEqual([note["degree"] for note in notes], group["degrees"])
                        self.assertEqual("".join(note["string"] for note in notes), group["string_path"])
                        self.assertEqual([note["ascii_column_in_group"] for note in notes], list(range(0, 3 * size, 3)))
                        for note in notes:
                            position = lane.DEGREES.index(note["degree"])
                            string, offset, finger = lane.POSITION_MAP[position]
                            self.assertEqual((note["string"], note["fret"], note["finger_digit"]),
                                             (string, root_fret + offset, finger))
                            self.assertEqual(note["scale_position"], position + 1)
                            self.assertEqual((lane.OPEN_MIDI[string] + note["fret"]) % 12,
                                             lane._pitch_class(note["tone"]))
                            self.assertIsNone(note["onset_q"])
                            self.assertIsNone(note["duration_q"])
                self.assertEqual((up["notes"][0]["degree"], up["notes"][0]["string"], up["notes"][0]["fret"]),
                                 (1, "E", root_fret))
                self.assertEqual((up["notes"][-1]["degree"], up["notes"][-1]["string"], up["notes"][-1]["fret"]),
                                 (15, "e", root_fret))
                self.assertEqual((down["notes"][0]["degree"], down["notes"][0]["string"], down["notes"][0]["fret"]),
                                 (15, "e", root_fret))
                self.assertEqual((down["notes"][-1]["degree"], down["notes"][-1]["string"], down["notes"][-1]["fret"]),
                                 (1, "E", root_fret))
                self.assertEqual(down["groups"][0]["D_start_group_start_stroke"], "U")
            boundary = card["linked_boundary"]
            self.assertEqual((boundary["degree"], boundary["string"], boundary["fret"]), (1, "E", root_fret))
            self.assertTrue(boundary["separate_rearticulated_contacts"])
            self.assertTrue(boundary["pick_cycle_continues"])
            self.assertEqual(card["modules"][0]["directions"][1]["notes"][-1]["fret"], boundary["fret"])
            self.assertEqual(card["modules"][1]["directions"][0]["notes"][0]["fret"], boundary["fret"])
            self.assertIsNone(card["canonical_item_id"])
            self.assertIsNone(card["canonical_variant_id"])
            self.assertFalse(card["runtime_eligible"])
            self.assertFalse(card["admitted"])
        self.assertEqual(records[9]["scale_tones"][:5], ["Gb", "Ab", "Bb", "Db", "Eb"])
        self.assertTrue(records[12]["octave_rung"])
        up_ids = [card["source_local_key"] for card in records]
        route = data["routes"]
        self.assertEqual(route["up"]["rungs"], up_ids)
        self.assertEqual(route["down_standalone"]["rungs"], list(reversed(up_ids)))
        self.assertEqual(route["down_return"]["rungs"], list(reversed(up_ids[:-1])))
        self.assertEqual(route["continuous_round_trip"]["rungs"], up_ids + list(reversed(up_ids[:-1])))
        self.assertEqual(route["continuous_round_trip"]["rungs"].count("L32-rung13"), 1)
        self.assertEqual(route["continuous_round_trip"]["cell_count"], 25)
        self.assertEqual((route["continuous_round_trip"]["module_A_notes"],
                          route["continuous_round_trip"]["module_B_notes"],
                          route["continuous_round_trip"]["linked_notes"]), (1350, 1750, 3100))
        self.assertEqual(route["continuous_round_trip"]["authored_grouped_beats_instruction_only"], 800)
        self.assertFalse(data["runtime_eligible"])
        self.assertFalse(data["admitted"])
        self.assertFalse(data["whole_workbook_complete"])

    def test_all_pdf_blocks_and_one_fret_transposition(self) -> None:
        txt_cards, _, _ = lane._txt_cards(self.txt.decode("utf-8"))
        pdf_cards, pdf_table = lane._pdf_cards(self.pdf)
        self.assertEqual(len(pdf_cards), 13)
        for index, (txt_card, pdf_card, row) in enumerate(zip(txt_cards, pdf_cards, pdf_table, strict=True)):
            self.assertEqual(pdf_card["scale_tones"], txt_card["scale_tones"])
            self.assertEqual(row["tones_1_to_5"], txt_card["scale_tones"][:5])
            txt_blocks = [(module["module"], direction["direction"], direction["path_line"], direction["raw_rows"])
                          for module in txt_card["modules"] for direction in module["directions"]]
            pdf_blocks = [(block["module"], block["direction"], block["path_line"], block["raw_rows"])
                          for block in pdf_card["blocks"]]
            self.assertEqual(pdf_blocks, txt_blocks)
            if index:
                for module, base_module in zip(txt_card["modules"], txt_cards[0]["modules"], strict=True):
                    for direction, base in zip(module["directions"], base_module["directions"], strict=True):
                        self.assertEqual([(note["string"], note["fret"], note["finger_digit"], note["degree"])
                                          for note in direction["notes"]],
                                         [(note["string"], note["fret"] + index, note["finger_digit"], note["degree"])
                                          for note in base["notes"]])

    def test_pins_and_authored_mutations(self) -> None:
        changed = bytearray(self.txt)
        changed[0] = ord("X")
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L32-TXT"):
            lane.build_candidate(txt_data=bytes(changed), pdf_data=self.pdf)
        changed_pdf = bytearray(self.pdf)
        changed_pdf[-1] ^= 1
        with self.assertRaisesRegex(lane.CandidateError, "PINNED_INPUT_DRIFT L32-PDF"):
            lane.build_candidate(txt_data=self.txt, pdf_data=bytes(changed_pdf))
        source = self.txt.decode("utf-8")
        mutations = [
            ("Deg|1--2--3--", "Deg|1--2--5--", "GROUP_DEGREE_OR_FINGER_INVALID"),
            ("Fng|2--4--1--", "Fng|2--4--2--", "GROUP_CONTACT_OR_FINGER_MISMATCH"),
            ("E  |5--7-----", "E  |6--7-----", "GROUP_CONTACT_OR_FINGER_MISMATCH"),
            ("String paths up:   EEA |", "String paths up:   EEB |", "TXT_OVERVIEW_PATH_MISMATCH"),
            ("DOWN: A(17) > Ab(16)", "DOWN: A(17) > G(16)", "TXT_CHROMATIC_ROUTE_MISMATCH"),
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
        self.assertEqual(hashlib.sha256(expected).hexdigest(), "f66189ab30d4961d971b58818e9d83fe4846fe986d34fdecb65caff976f653e5")
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
