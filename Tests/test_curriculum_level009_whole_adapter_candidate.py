"""Whole-Level9 source-bound normalization, coverage and refusal checks."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from Tools import curriculum_level009_whole_adapter_candidate as whole


ROOT = Path(__file__).resolve().parents[1]


class WholeLevel9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cards, cls.candidates = whole.load_inputs(ROOT)
        cls.aggregate = whole.normalize(cls.cards, cls.candidates)

    def changed_candidate(self, number: int) -> dict[int, dict]:
        result = dict(self.candidates)
        result[number] = copy.deepcopy(result[number])
        return result

    def test_complete_source_and_original_record_lineage(self) -> None:
        result = self.aggregate
        self.assertEqual(result["counts"], whole.COUNTS)
        self.assertEqual(len(result["records"]), 108)
        self.assertEqual([r["exercise_number"] for r in result["records"]], list(range(1, 109)))
        self.assertEqual(len({r["source_local_key"] for r in result["records"]}), 108)
        self.assertEqual(sum(len(r["directions"]) for r in result["records"]), 216)
        self.assertEqual(sum(len(d["sequential_one_string_routes"]) for r in result["records"]
                             for d in r["directions"]), 1296)
        self.assertEqual(sum(len(route["notes"]) for r in result["records"]
                             for d in r["directions"] for route in d["sequential_one_string_routes"]), 5184)
        self.assertEqual(result["records"][0]["source_refs"], {"txt": "L9-TXT1-31-45", "pdf": "L9-PDF1-p2"})
        self.assertEqual(result["records"][-1]["source_refs"], {"txt": "L9-TXT1-1775-1789", "pdf": "L9-PDF1-p10"})
        for record in result["records"]:
            number = (record["exercise_number"] - 1) // 12 + 1
            offset = (record["exercise_number"] - 1) % 12
            source = self.candidates[number]["records"][offset]
            self.assertEqual(record["original_record"], source)
            self.assertEqual(record["original_record_sha256"], whole.sha(whole.canonical(source)))
            self.assertEqual(record["source_refs"], source["source_refs"])
            self.assertEqual(record["code"], self.cards[record["exercise_number"]]["code"])

    def test_all_three_lane_layouts_preserve_route_order_and_2_plus_2(self) -> None:
        for exercise in (1, 13, 25, 37, 49, 61, 73, 85, 97):
            record = self.aggregate["records"][exercise - 1]
            for direction, expected_order, positions, shift in whole.DIRECTIONS:
                row = next(d for d in record["directions"] if d["direction"] == direction)
                self.assertEqual(row["route_order"], list(expected_order))
                self.assertEqual(row["position_order"], list(positions))
                self.assertEqual(row["pdf_template"], self.cards[exercise]["templates"][direction])
                for route in row["sequential_one_string_routes"]:
                    self.assertEqual(route["shift_after_note"], 2)
                    self.assertEqual(route["whole_hand_frame_shift_frets"], shift)
                    self.assertFalse(route["melodic_interval_inferred"])
                    self.assertEqual([note["ordinal"] for note in route["notes"]], [1, 2, 3, 4])
                    self.assertEqual([note["finger_digit"] for note in route["notes"]], list(record["code"]))
                    self.assertEqual([note["position"] for note in route["notes"]], list(positions[:1]) * 2 + list(positions[1:]) * 2)
                    self.assertEqual({note["string"] for note in route["notes"]}, {route["string"]})
                    self.assertTrue(all(note["onset_q"] is None and note["duration_q"] is None for note in route["notes"]))
        # A whole-frame upward shift in exercise 088 includes a falling note.
        up = self.aggregate["records"][87]["directions"][0]["sequential_one_string_routes"][0]
        self.assertEqual([note["fret"] for note in up["notes"]], [8, 5, 10, 7])

    def test_determinism_and_non_admission(self) -> None:
        first = whole.canonical(whole.build(ROOT))
        second = whole.canonical(whole.build(ROOT))
        self.assertEqual(first, second)
        self.assertEqual(first, whole.canonical(json.loads(first)))
        result = self.aggregate
        self.assertFalse(result["admitted"] or result["imported"] or result["runtime_eligible"]
                         or result["canonical_schema_validated"] or result["whole_workbook_complete"])
        for record in result["records"]:
            for key in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "note_per_click", "fixed_bpm"):
                self.assertIsNone(record[key])
            self.assertFalse(record["admitted"] or record["runtime_eligible"])

    def test_candidate_loss_duplicate_source_and_false_claims_refuse(self) -> None:
        bad = self.changed_candidate(5)
        bad[5]["records"].pop()
        with self.assertRaisesRegex(whole.CoverageError, "record count"):
            whole.normalize(self.cards, bad)
        bad = self.changed_candidate(5)
        bad[5]["records"][1]["source_local_key"] = bad[5]["records"][0]["source_local_key"]
        with self.assertRaisesRegex(whole.CoverageError, "source-local key"):
            whole.normalize(self.cards, bad)
        bad = self.changed_candidate(5)
        bad[5]["runtime_eligible"] = True
        with self.assertRaisesRegex(whole.CoverageError, "false candidate admission"):
            whole.normalize(self.cards, bad)
        bad = self.changed_candidate(5)
        bad[5]["records"][0]["note_per_click"] = 1
        with self.assertRaisesRegex(whole.CoverageError, "invented identity/timing"):
            whole.normalize(self.cards, bad)

    def test_family_route_shift_note_and_hidden_field_conflicts_refuse(self) -> None:
        for number, route_field, shift_field in ((1, "routes", "hand_frame_shift_frets"),
                                                 (2, "string_routes", "shift_frets"),
                                                 (4, "sequential_one_string_routes", "whole_hand_frame_shift_frets")):
            bad = self.changed_candidate(number)
            route = bad[number]["records"][0]["directions"][0][route_field][0]
            route[shift_field] = 0
            with self.subTest(set=number), self.assertRaisesRegex(whole.CoverageError, "route/shift conflict"):
                whole.normalize(self.cards, bad)
        bad = self.changed_candidate(4)
        bad[4]["records"][0]["directions"][0]["sequential_one_string_routes"][0]["cells"][0]["notes"][0]["onset_q"] = [0, 1]
        with self.assertRaisesRegex(whole.CoverageError, "invented note timing"):
            whole.normalize(self.cards, bad)
        bad = self.changed_candidate(2)
        bad[2]["records"][0]["directions"][0]["string_routes"][0]["cells"][0]["notes"][0]["canonical_id"] = "invented"
        with self.assertRaisesRegex(whole.CoverageError, "finger/fret/order conflict"):
            whole.normalize(self.cards, bad)

    def test_source_and_candidate_pin_refusal(self) -> None:
        with self.assertRaisesRegex(whole.CoverageError, "pinned input drift"):
            whole.read_pinned(ROOT, whole.TXT[0], "0" * 64, whole.TXT[2])
        with self.assertRaisesRegex(whole.CoverageError, "pinned input drift"):
            whole.read_pinned(ROOT, whole.SPECS[4][1], "0" * 64, whole.SPECS[4][3])
        altered = copy.deepcopy(self.cards)
        altered[37]["templates"]["shift_up"] = "S|wrong|"
        with self.assertRaisesRegex(whole.CoverageError, "route/template/source conflict"):
            whole.normalize(altered, self.candidates)

    def test_cli_refuses_output_outside_build_and_overwrite(self) -> None:
        command = [sys.executable, "-m", "Tools.curriculum_level009_whole_adapter_candidate", "--output"]
        bad = subprocess.run(command + [str(ROOT / "Results" / "forbidden.json")], cwd=ROOT,
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertIn("new JSON file", bad.stderr)
        existing = ROOT / whole.BUILD_REL / "aggregate-initial.json"
        self.assertTrue(existing.is_file())
        before = existing.read_bytes()
        bad = subprocess.run(command + [str(existing)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(existing.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
