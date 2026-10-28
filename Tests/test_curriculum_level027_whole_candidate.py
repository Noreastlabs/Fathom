#!/usr/bin/env python3
"""Focused source-projection tests for the detached Level27 candidate."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))

import curriculum_level027_whole_candidate as whole


class Level27WholeCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = ROOT
        cls.candidate = whole.build_candidate()
        cls.records = cls.candidate["records"]
        cls.by_rung = {record["rung"]: record for record in cls.records}

    def test_pinned_sources_and_exact_pending_source_map_row(self) -> None:
        txt = (self.root / whole.TXT_REL).read_bytes()
        pdf = (self.root / whole.PDF_REL).read_bytes()
        source_map = (self.root / whole.SOURCE_MAP_REL).read_bytes()
        self.assertEqual((len(txt), hashlib.sha256(txt).hexdigest()), (whole.TXT_BYTES, whole.TXT_SHA256))
        self.assertEqual((len(pdf), hashlib.sha256(pdf).hexdigest()), (whole.PDF_BYTES, whole.PDF_SHA256))
        self.assertEqual((len(source_map), hashlib.sha256(source_map).hexdigest()), (whole.SOURCE_MAP_BYTES, whole.SOURCE_MAP_SHA256))
        rows = list(csv.DictReader(source_map.decode("utf-8").splitlines(), delimiter="\t"))
        row = next(item for item in rows if item["level"] == "27")
        self.assertEqual(row["wbs_owner"], "2.3.1.1.1")
        self.assertEqual((row["review"], row["conversion_status"], row["representative_item_id"]), ("Pending", "not_converted", ""))
        for field in ("stable_ids_assigned", "runtime_eligible", "imported", "admitted"):
            self.assertEqual(row[field], "False")
        self.assertEqual(self.candidate["source_map_state"]["conversion_status"], "not_converted")

    def test_thirteen_ordered_rungs_preserve_keys_roots_frames_and_source_refs(self) -> None:
        route = self.candidate["route_reference"]
        self.assertEqual(len(self.records), 13)
        self.assertEqual([record["rung"] for record in self.records], list(range(1, 14)))
        self.assertEqual([record["root_fret"] for record in self.records], list(range(5, 18)))
        self.assertEqual(
            [record["key_name"] for record in self.records],
            [
                "A natural minor", "Bb natural minor", "B natural minor", "C natural minor",
                "C# natural minor", "D natural minor", "Eb natural minor", "E natural minor",
                "F natural minor", "F# natural minor", "G natural minor", "G# natural minor",
                "A natural minor - octave",
            ],
        )
        self.assertEqual([entry["source_line"] for entry in route], list(range(87, 100)))
        for rung, record in enumerate(self.records, start=1):
            self.assertEqual(record["frame"], {"low_fret": rung + 3, "high_fret": rung + 7})
            self.assertEqual(record["source_refs"]["txt_start_line"], 106 + 26 * (rung - 1))
            self.assertEqual(record["source_refs"]["txt_end_line"], 129 + 26 * (rung - 1))
            self.assertEqual(record["source_refs"]["route_table_line"], 86 + rung)
            self.assertEqual(record["source_refs"]["pdf_card_page"], 3 + (rung - 1) // 2 if rung < 13 else 9)
            self.assertEqual(record["source_refs"]["pdf_route_summary_page"], 2)
            self.assertEqual(record["source_refs"]["pdf_worked_example_page"], 1 if rung == 1 else None)
            self.assertEqual(len(record["scale_tones_two_octaves"]), 15)
            self.assertEqual(record["source_cell_note_count"], 52)

    def test_all_338_pairs_676_contacts_and_independent_pitch_interval_route_facts(self) -> None:
        pair_total = contact_total = 0
        quality_counts = {"m3": 0, "M3": 0}
        low_to_high = ("E", "A", "D", "G", "B", "e")
        for record in self.records:
            root_midi = whole.OPEN_MIDI["E"] + record["root_fret"]
            for direction in record["directions"]:
                self.assertEqual(len(direction["pairs"]), 13)
                expected_pairs = (
                    self.candidate["sequence_facts"]["ascending_degree_pairs"]
                    if direction["direction"] == "ascending"
                    else self.candidate["sequence_facts"]["descending_degree_pairs"]
                )
                expected_quality = self.candidate["sequence_facts"][
                    "ascending_quality" if direction["direction"] == "ascending" else "descending_quality"
                ]
                expected_paths = self.candidate["sequence_facts"][
                    "ascending_string_paths" if direction["direction"] == "ascending" else "descending_string_paths"
                ]
                self.assertEqual([pair["degree_pair"] for pair in direction["pairs"]], expected_pairs)
                self.assertEqual([pair["interval_quality"] for pair in direction["pairs"]], expected_quality)
                self.assertEqual([pair["string_path"] for pair in direction["pairs"]], expected_paths)
                for index, pair in enumerate(direction["pairs"]):
                    pair_total += 1
                    quality_counts[pair["interval_quality"]] += 1
                    self.assertEqual(pair["pair_number"], index + 1)
                    self.assertEqual(len(pair["contacts"]), 2)
                    pitches = []
                    for note in pair["contacts"]:
                        contact_total += 1
                        self.assertEqual(
                            note["midi_pitch"],
                            whole.OPEN_MIDI[note["string"]] + note["fret"],
                        )
                        self.assertEqual(
                            note["midi_pitch"],
                            root_midi + whole.DEGREE_SEMITONES[note["degree_label"]],
                        )
                        self.assertIn(note["string"], low_to_high)
                        self.assertTrue(record["frame"]["low_fret"] <= note["fret"] <= record["frame"]["high_fret"])
                        self.assertIn(note["finger_digit"], (1, 2, 3, 4))
                        self.assertIsNone(note["onset_q"])
                        self.assertIsNone(note["duration_q"])
                        pitches.append(note["midi_pitch"])
                    self.assertEqual(abs(pitches[1] - pitches[0]), 3 if pair["interval_quality"] == "m3" else 4)
                    string_indexes = [low_to_high.index(note["string"]) for note in pair["contacts"]]
                    self.assertLessEqual(abs(string_indexes[1] - string_indexes[0]), 1)
        self.assertEqual((pair_total, contact_total), (338, 676))
        self.assertEqual(quality_counts, {"m3": 208, "M3": 130})
        self.assertEqual(self.candidate["coverage"]["pair_count"], pair_total)
        self.assertEqual(self.candidate["coverage"]["note_contact_count"], contact_total)

    def test_two_high_root_notes_are_present_at_each_chart_turn(self) -> None:
        for record in self.records:
            ascending = record["directions"][0]["pairs"][-1]["contacts"][1]
            descending = record["directions"][1]["pairs"][0]["contacts"][0]
            for note in (ascending, descending):
                self.assertEqual(note["degree_label"], "15")
                self.assertEqual(note["string"], "e")
                self.assertEqual(note["fret"], record["root_fret"])
            self.assertEqual(ascending["midi_pitch"], descending["midi_pitch"])
        facts = self.candidate["sequence_facts"]
        self.assertEqual(facts["cell_design"]["high_root_occurrences_at_turn"], 2)
        self.assertEqual(facts["full_round_trip_instruction"]["cells_per_round"], 25)
        self.assertEqual(facts["full_round_trip_instruction"]["instructed_note_count"], 1300)
        self.assertIs(facts["full_round_trip_instruction"]["performed"], False)

    def test_pdf_route_table_and_all_rung_grids_match_the_txt(self) -> None:
        facts = self.candidate["pdf_projection_checks"]
        self.assertEqual(facts["route_rows_compared"], 13)
        self.assertEqual(facts["direction_grids_compared"], 28)
        self.assertTrue(facts["worked_example_matches_rung_01"])
        self.assertFalse(facts["down_paths_summary_present"])
        self.assertEqual(facts["page_one_session_protocol_step_count"], 6)
        self.assertEqual(facts["page_ten_practice_heading"], "Five-phase practice sequence")
        self.assertEqual(
            facts["rung_13_route_labels_preserved_separately"],
            {
                "txt": "A natural minor - octave",
                "pdf": "A natural minor (octave)",
                "shared_route_facts_match": True,
            },
        )
        self.assertEqual(self.candidate["source"]["pdf_rendered_pages_visually_reviewed"], list(range(1, 11)))
        for record in self.records:
            self.assertEqual(len(record["directions"]), 2)
            self.assertEqual(len(record["directions"][0]["tab_rows"]), 6)
            self.assertEqual(len(record["directions"][1]["tab_rows"]), 6)

    def test_rung_and_tab_parser_refuse_malformed_source_rows(self) -> None:
        with self.assertRaisesRegex(whole.CandidateError, "GRID_CELL_SHAPE_INVALID"):
            whole._split_pipe_cells("Int|short|", "Int")
        with self.assertRaisesRegex(whole.CandidateError, "TAB_ROW_COLUMN_COUNT_INVALID"):
            whole._tab_row("e  |bad")
        lines = (self.root / whole.TXT_REL).read_text(encoding="utf-8").splitlines()
        asc_degrees = whole._pair_labels(lines, "MAIN SEQUENCE", "Ascending")
        desc_degrees = whole._pair_labels(lines, "MAIN SEQUENCE", "Descending")
        asc_quality = whole._pair_labels(lines, "INTERVAL-QUALITY PATTERN", "Ascending")
        desc_quality = whole._pair_labels(lines, "INTERVAL-QUALITY PATTERN", "Descending")
        with self.assertRaisesRegex(whole.CandidateError, "RUNG_HEADING_COUNT 12"):
            whole._parse_text_rungs(
                lines[:417],
                whole._parse_route_table(lines),
                asc_degrees,
                desc_degrees,
                asc_quality,
                desc_quality,
                whole._route_pairs(lines, "Ascending"),
                whole._route_pairs(lines, "Descending"),
            )

    def test_source_discrepancies_retain_both_sides_without_resolution(self) -> None:
        differences = {item["id"]: item for item in self.candidate["source_discrepancies"]}
        self.assertEqual(
            set(differences),
            {
                "tempo_downshift_trigger_specificity",
                "pause_duration_specificity",
                "descending_string_path_summary",
                "practice_phase_grouping",
                "rung_13_route_label_presentation",
            },
        )
        tempo = differences["tempo_downshift_trigger_specificity"]
        self.assertIn("or signs of tension", tempo["txt_ref"]["text"])
        self.assertIn("after 2 errors.", tempo["pdf_ref"]["text"])
        pause = differences["pause_duration_specificity"]
        self.assertIn("one-beat pause", pause["txt_ref"]["text"])
        self.assertIn("pause only after each cell", pause["pdf_ref"]["text"])
        for item in differences.values():
            self.assertIn("pending_review", item["status"])

    def test_candidate_keeps_timing_ids_runtime_import_and_admission_unset(self) -> None:
        self.assertEqual(self.candidate["candidate_status"], "detached_pending_review")
        self.assertIs(self.candidate["scope"]["level_source_coverage_verified"], True)
        self.assertIs(self.candidate["scope"]["whole_workbook_complete"], False)
        self.assertIs(self.candidate["scope"]["parent_acceptance"], False)
        self.assertIs(self.candidate["scope"]["performed_or_recorded_practice"], False)
        for field in ("canonical_ids_assigned", "runtime_eligible", "runtime_admitted", "imported", "admitted"):
            self.assertIs(self.candidate["scope"][field], False)
        for record in self.records:
            for field in ("canonical_item_id", "canonical_variant_id", "onset_q", "duration_q", "note_per_click", "fixed_bpm"):
                self.assertIsNone(record[field])
            for field in ("runtime_eligible", "runtime_admitted", "imported", "admitted"):
                self.assertIs(record[field], False)
            for direction in record["directions"]:
                for pair in direction["pairs"]:
                    for note in pair["contacts"]:
                        self.assertIsNone(note["onset_q"])
                        self.assertIsNone(note["duration_q"])

    def test_input_mutations_fail_closed_and_serialization_is_deterministic(self) -> None:
        txt = (self.root / whole.TXT_REL).read_bytes()
        pdf = (self.root / whole.PDF_REL).read_bytes()
        source_map = (self.root / whole.SOURCE_MAP_REL).read_bytes()
        altered = lambda raw: raw[:-1] + bytes([raw[-1] ^ 1])
        with self.assertRaisesRegex(whole.CandidateError, "PINNED_INPUT_DRIFT L27-TXT"):
            whole.build_candidate(txt_data=altered(txt))
        with self.assertRaisesRegex(whole.CandidateError, "PINNED_INPUT_DRIFT L27-PDF"):
            whole.build_candidate(pdf_data=altered(pdf))
        with self.assertRaisesRegex(whole.CandidateError, "PINNED_INPUT_DRIFT L27-SOURCE-MAP"):
            whole.build_candidate(source_map_data=altered(source_map))
        first = whole.serialize_candidate(self.candidate)
        second = whole.serialize_candidate(whole.build_candidate())
        self.assertEqual(first, second)
        self.assertEqual(hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest())
        self.assertTrue(first.endswith(b"\n"))
        self.assertEqual(json.loads(first), self.candidate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
