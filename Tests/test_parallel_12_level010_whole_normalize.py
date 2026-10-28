"""Whole Level 10 source-local normalization and refusal checks."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path
from unittest.mock import patch

import parallel_12_level010_whole_normalize as module
from parallel_12_level010_whole_normalize import (
    INPUTS, MODE_ORDER, ROOT, CandidateError, build_candidate, canonical_bytes,
    digest, load_inputs, normalize_sources, serialize, source_cards, write_output,
)


class WholeLevelTenNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.txt, cls.pdf, cls.documents = load_inputs()
        cls.candidate = normalize_sources(cls.txt, cls.pdf, cls.documents)

    def test_exact_complete_source_local_inventory_and_provenance(self) -> None:
        candidate = self.candidate
        self.assertEqual(candidate["schema"], "fathom-level010-whole-detached-normalized-v1")
        self.assertEqual(candidate["sets"], list(range(1, 10)))
        self.assertEqual(candidate["counts"], {"records": 108, "modes": 216, "directions": 432,
                                               "string_routes": 2592, "untimed_note_positions": 10368})
        self.assertEqual([record["exercise_number"] for record in candidate["records"]],
                         [f"{n:03d}" for n in range(1, 109)])
        self.assertEqual(len(set(record["code"] for record in candidate["records"])), 108)
        self.assertEqual(len(set(record["source_local_key"] for record in candidate["records"])), 108)
        expected_inputs = [item for doc in self.documents for item in doc["records"]]
        for normalized, original in zip(candidate["records"], expected_inputs, strict=True):
            self.assertEqual(normalized["source_record"], original)
            self.assertEqual(normalized["source_record_sha256"], digest(canonical_bytes(original)))
            self.assertEqual(normalized["set"], (int(normalized["exercise_number"]) - 1) // 12 + 1)
            source = next(source for source in candidate["source_candidate_inputs"]
                          if normalized["set"] in source["sets"])
            self.assertEqual(normalized["source_candidate_path"], source["path"])
            self.assertEqual(normalized["source_candidate_sha256"], source["sha256"])

    def test_all_modes_directions_routes_notes_and_printed_refs(self) -> None:
        cards = source_cards(self.txt, self.pdf)
        self.assertEqual(len(cards), 216)
        for record in self.candidate["records"]:
            number = int(record["exercise_number"])
            self.assertEqual([mode["mode"] for mode in record["modes"]], list(MODE_ORDER))
            for mode in record["modes"]:
                mode_key = mode["mode"]
                shift = 3 if mode_key == "mode_a" else 1
                landing = shift + 1
                card = cards[(number, mode_key)]
                self.assertEqual(record["code"], card["code"])
                self.assertEqual(mode["shift_after_note"], shift)
                self.assertEqual(mode["landing_note_ordinal"], landing)
                self.assertEqual(mode["source_refs"],
                                 {"txt": f"L10-TXT1-{card['txt_start_line']}-{card['txt_end_line']}",
                                  "pdf": f"L10-PDF1-p{card['pdf_page']}"})
                self.assertEqual([direction["direction"] for direction in mode["directions"]],
                                 ["shift_up", "shift_down"])
                for direction in mode["directions"]:
                    key = direction["direction"]
                    self.assertEqual(len(direction["routes"]), 6)
                    self.assertEqual([route["string"] for route in direction["routes"]],
                                     direction["route_order"])
                    positions = direction["position_order"]
                    expected_positions = [positions[0]] * shift + [positions[1]] * (4 - shift)
                    for ordinal, route in enumerate(direction["routes"], 1):
                        self.assertEqual(route["route_ordinal"], ordinal)
                        self.assertEqual(route["shift_after_note"], shift)
                        self.assertEqual(route["landing_note_ordinal"], landing)
                        self.assertEqual(route["source_finger_row"], card["directions"][key]["finger_row"])
                        self.assertEqual(route["pdf_finger_template"], card["directions"][key]["pdf_finger_template"])
                        self.assertEqual(route["pdf_tab_template"], card["directions"][key]["pdf_tab_template"])
                        notes = route["notes"]
                        self.assertEqual(len(notes), 4)
                        self.assertEqual([note["ordinal"] for note in notes], [1, 2, 3, 4])
                        self.assertEqual([note["finger_digit"] for note in notes], list(record["code"]))
                        self.assertEqual([note["position"] for note in notes], expected_positions)
                        self.assertEqual([note["landing"] for note in notes],
                                         [index == landing for index in range(1, 5)])
                        self.assertEqual([note["fret"] for note in notes],
                                         [int(digit) + (4 if position == "P5" else 6)
                                          for digit, position in zip(record["code"], expected_positions, strict=True)])
                        self.assertTrue(all(note["string"] == route["string"] and
                                            note["onset_q"] is None and note["duration_q"] is None
                                            for note in notes))

    def test_pins_and_deterministic_serialization(self) -> None:
        self.assertEqual(serialize(self.candidate), serialize(build_candidate()))
        for _, _, path, pin, _ in INPUTS:
            data = module.local_bytes(ROOT, path)
            self.assertEqual((len(data), digest(data)), pin)
        original = module.local_bytes
        def changed(root: Path, path: Path) -> bytes:
            data = original(root, path)
            return data + b"x" if path == INPUTS[1][2] else data
        with patch.object(module, "local_bytes", side_effect=changed):
            with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT RELEASED_SETS_2_2"):
                load_inputs()
        def changed_txt(root: Path, path: Path) -> bytes:
            data = original(root, path)
            return data + b"x" if path == module.TXT else data
        with patch.object(module, "local_bytes", side_effect=changed_txt):
            with self.assertRaisesRegex(CandidateError, "PINNED_INPUT_DRIFT LEVEL10_TXT"):
                load_inputs()

    def test_duplicate_missing_code_and_mode_refuse(self) -> None:
        def bad(change, error: str) -> None:
            docs = copy.deepcopy(self.documents)
            change(docs)
            with self.assertRaisesRegex(CandidateError, error):
                normalize_sources(self.txt, self.pdf, docs)
        bad(lambda docs: docs[0]["records"].pop(), "INPUT_ROOT_SHAPE")
        bad(lambda docs: docs[0]["records"][1].update(exercise_number="001"), "CANDIDATE_RECORD_IDENTITY")
        bad(lambda docs: docs[1]["records"][0].update(finger_code="1322"), "CANDIDATE_RECORD_IDENTITY")
        bad(lambda docs: docs[2]["records"][0]["modes"][1].update(mode="mode_a"), "CANDIDATE_MODE_DUPLICATE")
        bad(lambda docs: docs[3]["records"][0]["modes"].pop(), "CANDIDATE_MODE_COUNT")

    def test_route_and_landing_mutations_refuse_in_each_layout(self) -> None:
        def bad(change, error: str) -> None:
            docs = copy.deepcopy(self.documents)
            change(docs)
            with self.assertRaisesRegex(CandidateError, error):
                normalize_sources(self.txt, self.pdf, docs)
        bad(lambda docs: docs[0]["records"][0]["modes"][0]["directions"][0]["string_routes"].reverse(),
            "CANDIDATE_ROUTE_ORDER")
        bad(lambda docs: docs[0]["records"][0]["modes"][0]["directions"][0]["string_routes"][0]["cells"][1]["notes"][0].update(is_landing_note=False),
            "CANDIDATE_NOTE_MISMATCH")
        bad(lambda docs: docs[1]["records"][0]["modes"][0]["routes"][0]["notes"][0].update(fret=9),
            "CANDIDATE_NOTE_MISMATCH")
        bad(lambda docs: docs[1]["records"][0]["modes"][0]["routes"].reverse(),
            "CANDIDATE_ROUTE_COUNT")
        bad(lambda docs: docs[2]["records"][0]["modes"][0]["directions"][0]["routes"].pop(),
            "CANDIDATE_ROUTE_COUNT")
        bad(lambda docs: docs[3]["records"][0]["modes"][1].update(landing_note_ordinal=4),
            "CANDIDATE_LANDING")
        bad(lambda docs: docs[3]["records"][0]["modes"][0]["directions"][0]["routes"][0]["notes"][3].update(landing=False),
            "CANDIDATE_NOTE_MISMATCH")

    def test_source_admission_and_output_boundary_refuse(self) -> None:
        docs = copy.deepcopy(self.documents)
        docs[3]["runtime_eligible"] = True
        with self.assertRaisesRegex(CandidateError, "INPUT_ROOT_ADMISSION"):
            normalize_sources(self.txt, self.pdf, docs)
        docs = copy.deepcopy(self.documents)
        docs[1]["records"][0]["onset"] = 1
        with self.assertRaisesRegex(CandidateError, "CANDIDATE_RECORD_ADMISSION"):
            normalize_sources(self.txt, self.pdf, docs)
        for record in self.candidate["records"]:
            self.assertTrue(all(record[key] is None for key in
                                ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q",
                                 "fixed_bpm", "note_per_click")))
            self.assertTrue(all(record[key] is False for key in
                                ("runtime_eligible", "runtime_admitted", "imported", "admitted")))
        self.assertFalse(self.candidate["whole_workbook_complete"])
        with self.assertRaisesRegex(CandidateError, "OUTPUT_BOUNDARY"):
            write_output(Path("relative.json"), b"{}")
        with self.assertRaisesRegex(CandidateError, "OUTPUT_BOUNDARY"):
            write_output(ROOT / "Build/parallel-12/other/candidate.json", b"{}")


if __name__ == "__main__":
    unittest.main()
